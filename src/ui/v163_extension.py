"""v163 : timeline / historique universel."""
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import universal_history as uh


ICONS = {
    "Téléchargement": "⬇",
    "Benchmark": "📊",
    "Entraînement": "🧠",
    "Outil local": "🛠",
    "Système": "⚙️",
    "Erreur": "⚠️",
    "Création": "✨",
    "Autre": "•",
}
STATUS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "running": "⏳",
    "info": "ℹ️",
}


class HistoryTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.rows = []
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🕘 Historique universel")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Timeline centrale de l'activité IA Manager. Elle regroupe les événements nouveaux "
            "et réimporte les historiques déjà présents quand ils sont disponibles."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Rechercher modèle, outil, résultat…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filters)
        filters.addWidget(self.search, 2)

        self.kind = QComboBox()
        self.kind.addItem("Tous les types", "")
        for name in ("Téléchargement", "Benchmark", "Entraînement", "Outil local", "Création", "Système", "Erreur"):
            self.kind.addItem(name, name)
        self.kind.currentIndexChanged.connect(self.apply_filters)
        filters.addWidget(self.kind)

        refresh = QPushButton("🔄 Actualiser / importer")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(refresh)

        clear = QPushButton("🧹 Effacer la timeline")
        clear.clicked.connect(self.clear_history)
        filters.addWidget(clear)
        root.addLayout(filters)

        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Type", "État", "Événement", "Détail", "Source", "Actions"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh(self):
        count = uh.import_existing()
        self.rows = uh.list_events()
        self.apply_filters()
        self.status.setText(
            f"Historique actualisé · {len(self.rows)} événement(s) · import synchronisé."
        )

    def filtered(self):
        needle = self.search.text().strip().casefold()
        kind = self.kind.currentData()
        out = []
        for row in self.rows:
            if kind and row.get("kind") != kind:
                continue
            hay = " ".join([
                str(row.get("title") or ""),
                str(row.get("detail") or ""),
                str(row.get("source") or ""),
                str(row.get("kind") or ""),
            ]).casefold()
            if needle and needle not in hay:
                continue
            out.append(row)
        return out

    def apply_filters(self):
        rows = self.filtered()
        self.table.setRowCount(len(rows))

        counts = {}
        for item in rows:
            counts[item.get("kind", "Autre")] = counts.get(item.get("kind", "Autre"), 0) + 1

        for r, item in enumerate(rows):
            kind = item.get("kind") or "Autre"
            state = item.get("status") or "info"
            values = [
                str(item.get("created") or "").replace("T", " "),
                f"{ICONS.get(kind, '•')} {kind}",
                f"{STATUS.get(state, 'ℹ️')} {state}",
                str(item.get("title") or ""),
                str(item.get("detail") or ""),
                str(item.get("source") or ""),
            ]
            for c, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, str(item.get("id") or ""))
                self.table.setItem(r, c, cell)

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 1, 2, 1)
            path = str(item.get("path") or "")
            if path:
                op = QPushButton("Ouvrir")
                op.clicked.connect(lambda _=False, p=path: self.open_path(p))
                al.addWidget(op)

            remove = QPushButton("Retirer")
            remove.clicked.connect(
                lambda _=False, eid=str(item.get("id") or ""): self.remove_event(eid)
            )
            al.addWidget(remove)
            self.table.setCellWidget(r, 6, actions)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

        by_kind = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        self.summary.setText(
            f"{len(rows)} événement(s) affiché(s)" + (f" · {by_kind}" if by_kind else "")
        )

    def open_path(self, value):
        p = Path(value)
        target = p if p.is_dir() else p.parent
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        else:
            self.status.setText("Le fichier ou dossier n'existe plus : " + value)

    def remove_event(self, eid):
        uh.remove(eid)
        self.rows = uh.list_events()
        self.apply_filters()

    def clear_history(self):
        answer = QMessageBox.question(
            self,
            "Effacer la timeline",
            "Effacer l'historique universel ? Les historiques sources (benchmarks, entraînements, téléchargements) "
            "ne seront pas supprimés et pourront être réimportés lors d'une future actualisation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        uh.clear()
        self.rows = []
        self.apply_filters()
        self.status.setText("Timeline effacée. Les fichiers de résultats originaux sont conservés.")


def _patch_downloads(window):
    tracker = getattr(window, "download_tracker", None)
    if tracker is None or getattr(tracker, "_v163_history", False):
        return

    def sync():
        for job in tracker.jobs.values():
            state = str(job.get("state") or "")
            if state not in ("done", "failed", "cancelled", "interrupted"):
                continue
            status = {
                "done": "success",
                "failed": "error",
                "cancelled": "warning",
                "interrupted": "warning",
            }.get(state, "info")
            uh.record(
                "Téléchargement",
                str(job.get("name") or "Téléchargement"),
                str(job.get("status") or state),
                status,
                str(job.get("target") or ""),
                str(job.get("source") or ""),
                "v157:" + str(job.get("id") or ""),
            )

    tracker.changed.connect(sync)
    sync()
    tracker._v163_history = True


def _patch_benchmark(window):
    tab = getattr(window, "benchmark_tab", None)
    if tab is None or getattr(tab, "_v163_history", False):
        return

    old_done = tab.benchmark_done
    old_failed = tab.benchmark_failed

    def benchmark_done(self, campaign):
        old_done(campaign)
        models = ", ".join(campaign.get("models") or [])
        uh.record(
            "Benchmark",
            "Benchmark IA terminé",
            f"{models} · {len(campaign.get('rows') or [])} test(s)",
            "success",
            str(campaign.get("path") or ""),
            "Benchmark",
        )

    def benchmark_failed(self, error):
        old_failed(error)
        uh.record(
            "Benchmark",
            "Benchmark interrompu",
            str(error),
            "error",
            "",
            "Benchmark",
        )

    tab.benchmark_done = MethodType(benchmark_done, tab)
    tab.benchmark_failed = MethodType(benchmark_failed, tab)
    try:
        if tab.worker is not None:
            pass
    except Exception:
        pass
    tab._v163_history = True


def _patch_training(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(tab, "_v163_history", False):
        return

    old_finished = tab.finished

    def finished(self, code, status):
        job = self.job
        importing = bool(self.importing)
        cancelled = bool(self.cancelled)
        old_finished(code, status)
        ok = code == 0 and not cancelled
        title = "Import Ollama" if importing else "Tâche entraînement / fusion"
        uh.record(
            "Entraînement",
            title + (" terminé" if ok else " interrompu"),
            f"Code {code}",
            "success" if ok else ("warning" if cancelled else "error"),
            str(job or ""),
            "Atelier entraînement",
            "train-live:" + (Path(job).name if job else str(code)),
        )

    tab.finished = MethodType(finished, tab)
    tab._v163_history = True


def _patch_creative(window):
    tab = getattr(window, "creative_tools_tab", None)
    if tab is None or getattr(tab, "_v163_history", False):
        return

    old_finish = tab.finish

    def finish(self, success, message=""):
        mode = str(self.mode or "")
        active = self.active
        result = old_finish(success, message)
        key = ""
        root = ""
        if active:
            try:
                root, key, _hardware = active
            except Exception:
                pass
        label = {
            "install": "Installation outil local",
            "diagnostic": "Diagnostic outil local",
            "run": "Session outil local",
        }.get(mode, "Outil local")
        uh.record(
            "Outil local",
            f"{label} · {key or 'moteur'}",
            message or ("Succès" if success else "Échec"),
            "success" if success else "error",
            str(root or ""),
            key or "Outils locaux",
        )
        return result

    tab.finish = MethodType(finish, tab)
    tab._v163_history = True


def _patch_storage(window):
    tab = getattr(window, "storage_tab", None)
    if tab is None or getattr(tab, "_v163_history", False):
        return

    old_copy = tab.on_copy_done

    def on_copy_done(self, ok, message):
        old_copy(ok, message)
        uh.record(
            "Système",
            "Migration de stockage" if ok else "Échec migration de stockage",
            str(message),
            "success" if ok else "error",
            "",
            "Stockage",
        )

    tab.on_copy_done = MethodType(on_copy_done, tab)
    tab._v163_history = True


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ACCUEIL":
                if not any(e[0] == "history_tab" for e in entries):
                    entries.append(
                        ("history_tab", "Historique universel", "Timeline des téléchargements, benchmarks, tâches et événements.")
                    )
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v163(window):
    if getattr(window, "_v163_universal_history", False):
        return

    uh.import_existing()

    tab = HistoryTab(window)
    window.history_tab = tab

    downloads = getattr(window, "download_center_tab", None)
    idx = window.tabs.indexOf(downloads)
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "🕘 Historique")

    _patch_downloads(window)
    _patch_benchmark(window)
    _patch_training(window)
    _patch_creative(window)
    _patch_storage(window)
    _add_nav(window)

    timer = QTimer(tab)
    timer.setInterval(15000)
    timer.timeout.connect(tab.refresh)
    timer.start()
    tab.v163_timer = timer

    window._v163_universal_history = True
