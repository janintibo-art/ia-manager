"""v161 : Gestionnaire de stockage."""
import os
import shutil
from collections import defaultdict
from pathlib import Path

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import creative_tools, download_history, settings, storage


def _human(value):
    value = float(value or 0)
    units = ("o", "Ko", "Mo", "Go", "To")
    i = 0
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.1f} {units[i]}"


def _folder_size(path, max_files=200000):
    path = Path(path)
    total = 0
    count = 0
    largest = []
    if not path.exists():
        return 0, 0, [], []
    temps = []
    for parent, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(parent) / d).is_symlink()]
        for name in files:
            count += 1
            if count > max_files:
                return total, count, largest, temps
            p = Path(parent) / name
            try:
                if p.is_symlink():
                    continue
                size = p.stat().st_size
                total += size
                largest.append((size, str(p)))
                low = name.lower()
                if low.endswith((".part", ".tmp", ".temp", ".download")) or ".ia-manager-part" in low:
                    temps.append((size, str(p)))
            except OSError:
                pass
    largest.sort(reverse=True)
    return total, count, largest[:30], temps


def _category_paths(window):
    rows = [
        ("Modèles / téléchargements IA Manager", storage.app_models()),
        ("Modèles Ollama", storage.ollama_models()),
        ("Conversions", storage.conversions()),
        ("Sauvegardes / archives chat", storage.backups()),
        ("Configuration IA Manager", Path.home() / ".ia_manager"),
    ]
    creative = getattr(window, "creative_tools_tab", None)
    if creative is not None:
        try:
            base = Path(creative.directory.text()).expanduser()
            for key, meta in creative_tools.TOOLS.items():
                rows.append((meta["name"], base / key))
        except Exception:
            pass
    return rows


class ScanWorker(QThread):
    done = pyqtSignal(list, list, list)
    failed = pyqtSignal(str)

    def __init__(self, paths):
        super().__init__()
        self.paths = list(paths)

    def run(self):
        try:
            categories = []
            largest_all = []
            temps_all = []
            seen_roots = set()
            for label, path in self.paths:
                p = Path(path).expanduser()
                try:
                    rp = p.resolve()
                except Exception:
                    rp = p
                # Évite de compter deux fois exactement le même dossier.
                if str(rp).casefold() in seen_roots:
                    continue
                seen_roots.add(str(rp).casefold())
                size, count, largest, temps = _folder_size(p)
                categories.append((label, str(p), size, count, p.exists()))
                largest_all.extend((s, f, label) for s, f in largest)
                temps_all.extend((s, f, label) for s, f in temps)

            largest_all.sort(reverse=True)
            temps_all.sort(reverse=True)

            # Candidats doublons prudents : même nom + même taille, sans hachage lourd.
            groups = defaultdict(list)
            for size, file, label in largest_all:
                p = Path(file)
                if size >= 10 * 1024 * 1024:
                    groups[(p.name.casefold(), size)].append((file, label))
            dupes = []
            for (name, size), items in groups.items():
                if len(items) > 1:
                    dupes.append((name, size, items))
            dupes.sort(key=lambda x: x[1], reverse=True)

            self.done.emit(categories, largest_all[:50], temps_all[:200] + [("DUPES", dupes, "")])
        except Exception as exc:
            self.failed.emit(str(exc))


class CopyWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, mode, source, target):
        super().__init__()
        self.mode = mode
        self.source = Path(source)
        self.target = Path(target)

    def run(self):
        try:
            if self.mode == "app":
                new_root = storage.validate_root(self.target)
                mapping = [
                    (storage.app_models(), new_root / "Modeles" / "Telechargements"),
                    (storage.conversions(), new_root / "Modeles" / "Conversions"),
                    (storage.backups(), new_root / "Sauvegardes"),
                ]
                copied = 0
                for src, dst in mapping:
                    if Path(src).exists():
                        copied += storage.copy_folder(src, dst)
                settings.set("storage_root", str(new_root))
                self.done.emit(
                    True,
                    f"Copie vérifiée terminée · {copied} fichier(s). "
                    "IA Manager utilise maintenant ce nouvel emplacement. "
                    "Les anciens fichiers n'ont pas été supprimés."
                )
            elif self.mode == "ollama":
                source = self.source
                target = storage.validate_root(self.target)
                copied = storage.copy_folder(source, target) if source.exists() else 0
                storage.set_ollama_location(target)
                self.done.emit(
                    True,
                    f"Copie Ollama terminée · {copied} fichier(s). "
                    "Le nouvel emplacement est configuré. Redémarrez Ollama avant de supprimer l'ancien dossier."
                )
            else:
                raise ValueError("Mode de copie inconnu.")
        except Exception as exc:
            self.done.emit(False, str(exc))


class StorageTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.scan_worker = None
        self.copy_worker = None
        self.temp_files = []
        self.dupes = []
        self.build_ui()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("💽 Gestionnaire de stockage")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Analyse les modèles, caches, conversions, archives et outils locaux. "
            "Les déplacements utilisent une copie vérifiée et ne suppriment jamais l'ancien dossier automatiquement."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        buttons = QHBoxLayout()
        self.scan_btn = QPushButton("🔎 Analyser l'espace disque")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self.scan)
        buttons.addWidget(self.scan_btn)

        self.move_app = QPushButton("📦 Déplacer les données IA Manager…")
        self.move_app.clicked.connect(self.move_app_data)
        buttons.addWidget(self.move_app)

        self.move_ollama = QPushButton("🦙 Déplacer les modèles Ollama…")
        self.move_ollama.clicked.connect(self.move_ollama_data)
        buttons.addWidget(self.move_ollama)

        self.clean_btn = QPushButton("🧹 Nettoyer les temporaires sûrs")
        self.clean_btn.clicked.connect(self.clean_safe)
        buttons.addWidget(self.clean_btn)
        buttons.addStretch()
        root.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        root.addWidget(QLabel("Répartition par emplacement"))
        self.categories = QTableWidget(0, 5)
        self.categories.setHorizontalHeaderLabels(["Catégorie", "Taille", "Fichiers", "Emplacement", "Ouvrir"])
        self.categories.verticalHeader().hide()
        self.categories.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.categories.horizontalHeader().setStretchLastSection(True)
        self.categories.setMinimumHeight(300)
        root.addWidget(self.categories)

        root.addWidget(QLabel("Plus gros fichiers détectés"))
        self.largest = QTableWidget(0, 3)
        self.largest.setHorizontalHeaderLabels(["Taille", "Catégorie", "Fichier"])
        self.largest.verticalHeader().hide()
        self.largest.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.largest.horizontalHeader().setStretchLastSection(True)
        self.largest.setMinimumHeight(300)
        root.addWidget(self.largest)

        root.addWidget(QLabel("Doublons potentiels"))
        dupe_note = QLabel(
            "Détection prudente : même nom + même taille. IA Manager ne supprime rien automatiquement ; "
            "ce sont seulement des candidats à vérifier."
        )
        dupe_note.setWordWrap(True)
        root.addWidget(dupe_note)
        self.duplicates = QTableWidget(0, 3)
        self.duplicates.setHorizontalHeaderLabels(["Taille", "Nom", "Emplacements détectés"])
        self.duplicates.verticalHeader().hide()
        self.duplicates.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.duplicates.horizontalHeader().setStretchLastSection(True)
        self.duplicates.setMinimumHeight(220)
        root.addWidget(self.duplicates)

    def set_busy(self, busy, text=""):
        self.progress.setVisible(busy)
        for b in (self.scan_btn, self.move_app, self.move_ollama, self.clean_btn):
            b.setEnabled(not busy)
        if text:
            self.status.setText(text)

    def scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        self.set_busy(True, "Analyse des dossiers en cours…")
        self.scan_worker = ScanWorker(_category_paths(self.window))
        self.scan_worker.done.connect(self.on_scan)
        self.scan_worker.failed.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_error(self, error):
        self.set_busy(False)
        self.status.setText("❌ Analyse impossible : " + error)

    def on_scan(self, categories, largest, mixed):
        self.set_busy(False)
        self.temp_files = []
        self.dupes = []
        for item in mixed:
            if item and item[0] == "DUPES":
                self.dupes = item[1]
            else:
                self.temp_files.append(item)

        self.categories.setRowCount(len(categories))
        total = 0
        for r, (label, path, size, count, exists) in enumerate(categories):
            total += size
            self.categories.setItem(r, 0, QTableWidgetItem(label))
            self.categories.setItem(r, 1, QTableWidgetItem(_human(size)))
            self.categories.setItem(r, 2, QTableWidgetItem(str(count)))
            self.categories.setItem(r, 3, QTableWidgetItem(path))
            btn = QPushButton("Ouvrir")
            btn.setEnabled(bool(exists))
            btn.clicked.connect(lambda _=False, p=path: self.open_folder(p))
            self.categories.setCellWidget(r, 4, btn)

        self.largest.setRowCount(len(largest))
        for r, (size, file, label) in enumerate(largest):
            self.largest.setItem(r, 0, QTableWidgetItem(_human(size)))
            self.largest.setItem(r, 1, QTableWidgetItem(label))
            self.largest.setItem(r, 2, QTableWidgetItem(file))

        self.duplicates.setRowCount(len(self.dupes))
        for r, (name, size, items) in enumerate(self.dupes):
            self.duplicates.setItem(r, 0, QTableWidgetItem(_human(size)))
            self.duplicates.setItem(r, 1, QTableWidgetItem(name))
            self.duplicates.setItem(r, 2, QTableWidgetItem("\n".join(x[0] for x in items)))

        for table in (self.categories, self.largest, self.duplicates):
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)

        temp_size = sum(int(x[0]) for x in self.temp_files)
        self.status.setText(
            f"✅ Analyse terminée · {_human(total)} parcourus · "
            f"{len(self.temp_files)} temporaire(s) ({_human(temp_size)}) · "
            f"{len(self.dupes)} groupe(s) de doublons potentiels."
        )

    def open_folder(self, path):
        p = Path(path)
        if p.is_file():
            p = p.parent
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def clean_safe(self):
        removed = download_history.cleanup_cache()
        extra_removed = 0
        # Ne supprime ici que les fichiers temporaires typiques appartenant aux
        # répertoires gérés par IA Manager, jamais les modèles complets.
        managed_roots = [
            storage.app_models(),
            Path.home() / ".ia_manager",
        ]
        for _size, name, _label in list(self.temp_files):
            p = Path(name)
            if not p.exists():
                continue
            try:
                rp = p.resolve()
                allowed = any(Path(root).resolve() == rp or Path(root).resolve() in rp.parents for root in managed_roots if Path(root).exists())
                if allowed and (p.name.lower().endswith((".part", ".tmp", ".temp", ".download")) or ".ia-manager-part" in p.name.lower()):
                    p.unlink()
                    extra_removed += 1
            except Exception:
                pass

        self.status.setText(
            f"✅ Nettoyage terminé : {removed + extra_removed} fichier(s) temporaire(s) supprimé(s). "
            "Aucun modèle complet ni ancien dossier de migration n'a été supprimé."
        )
        self.scan()

    def choose_target(self, title):
        return QFileDialog.getExistingDirectory(self, title, str(Path.home()))

    def move_app_data(self):
        target = self.choose_target("Choisir le nouveau dossier racine IA Manager")
        if not target:
            return
        answer = QMessageBox.question(
            self, "Copier les données IA Manager",
            "Les données seront copiées et vérifiées vers ce nouvel emplacement. "
            "L'ancien dossier ne sera PAS supprimé.\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_copy("app", storage.root() or Path.home() / ".ia_manager", target)

    def move_ollama_data(self):
        source = storage.ollama_models()
        target = self.choose_target("Choisir le nouveau dossier des modèles Ollama")
        if not target:
            return
        answer = QMessageBox.question(
            self, "Copier les modèles Ollama",
            "Les modèles Ollama seront copiés sans écraser les fichiers différents. "
            "L'ancien dossier restera intact. Ollama devra être redémarré ensuite.\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_copy("ollama", source, target)

    def start_copy(self, mode, source, target):
        if self.copy_worker is not None and self.copy_worker.isRunning():
            return
        self.set_busy(True, "Copie vérifiée en cours… Cela peut être long pour les gros modèles.")
        self.copy_worker = CopyWorker(mode, source, target)
        self.copy_worker.done.connect(self.on_copy_done)
        self.copy_worker.start()

    def on_copy_done(self, ok, message):
        self.set_busy(False)
        self.status.setText(("✅ " if ok else "❌ ") + message)
        if ok:
            self.scan()


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "SYSTÈME":
                if not any(e[0] == "storage_tab" for e in entries):
                    entries.insert(0, (
                        "storage_tab",
                        "Stockage",
                        "Analysez l'espace disque, les caches et les emplacements des modèles."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v161(window):
    if getattr(window, "_v161_storage_manager", False):
        return

    tab = StorageTab(window)
    window.storage_tab = tab

    connections = getattr(window, "connections_tab", None)
    idx = window.tabs.indexOf(connections)
    window.tabs.insertTab(idx if idx >= 0 else window.tabs.count(), tab, "💽 Stockage")

    _add_nav(window)
    window._v161_storage_manager = True
