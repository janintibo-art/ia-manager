"""Page Recherche universelle v110 : recherche + actions adaptées."""
import html
import shutil

from PyQt6.QtCore import QProcess, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QListWidget, QListWidgetItem, QTextBrowser, QSplitter, QMessageBox,
    QFileDialog
)

from src.backend import settings, universal_actions, universal_search
from src.ui.workers import FunctionWorker


class UniversalSearchPage(QWidget):
    open_search_result = pyqtSignal(int, str)
    open_pinokio = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.all_results = []
        self.workers = []
        self.errors = {}
        self.pending = set()
        self.favorite_ids = set(settings.get("studio_v109_source_favorites") or [])
        self.current = None
        self.action_process = None

        root = QVBoxLayout(self)
        intro = QLabel(
            "Une seule recherche interroge plusieurs catalogues en parallèle. "
            "La v110 propose ensuite l'action adaptée à chaque source."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        top = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Exemples : générateur musique local, image vers 3D, voix, coder, upscaler…")
        self.query.returnPressed.connect(self.search_all)
        self.search_btn = QPushButton("Rechercher partout")
        self.search_btn.clicked.connect(self.search_all)
        top.addWidget(self.query, 1); top.addWidget(self.search_btn)
        root.addLayout(top)

        filters = QHBoxLayout()
        self.source_filter = QComboBox()
        self.source_filter.addItem("Toutes les sources", "Toutes")
        for sid, label in universal_search.SOURCES:
            self.source_filter.addItem(label, sid)
        self.type_filter = QComboBox()
        self.type_filter.addItems(universal_search.TYPE_FILTERS)
        self.local_only = QCheckBox("Local uniquement")
        self.favorites_only = QCheckBox("★ Favoris")
        for w in (self.source_filter, self.type_filter):
            w.currentIndexChanged.connect(self.refresh_list)
        self.local_only.toggled.connect(self.refresh_list)
        self.favorites_only.toggled.connect(self.refresh_list)
        filters.addWidget(QLabel("Source :")); filters.addWidget(self.source_filter)
        filters.addWidget(QLabel("Type :")); filters.addWidget(self.type_filter)
        filters.addWidget(self.local_only); filters.addWidget(self.favorites_only); filters.addStretch(1)
        root.addLayout(filters)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        split = QSplitter()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.select)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        split.addWidget(self.list); split.addWidget(self.details); split.setSizes([430, 680])
        root.addWidget(split, 1)

        actions = QHBoxLayout()
        self.action_btn = QPushButton("Action adaptée")
        self.action_btn.clicked.connect(self.run_adapted_action)
        self.favorite_btn = QPushButton("☆ Ajouter aux favoris")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.open_btn = QPushButton("Ouvrir la source")
        self.open_btn.clicked.connect(self.open_current)
        actions.addWidget(self.action_btn); actions.addWidget(self.favorite_btn)
        actions.addWidget(self.open_btn); actions.addStretch(1)
        root.addLayout(actions)
        self.update_buttons()

    def search_all(self):
        query = self.query.text().strip()
        if not query:
            self.status.setText("Saisissez un mot-clé.")
            return
        self.all_results = []
        self.errors = {}
        self.pending = {sid for sid, _label in universal_search.SOURCES}
        self.workers = []
        self.current = None
        self.list.clear(); self.details.clear()
        self.search_btn.setEnabled(False)
        self.status.setText("⏳ Recherche simultanée sur " + str(len(self.pending)) + " sources…")

        for source in list(self.pending):
            worker = FunctionWorker(universal_search.search_one, source, query, 20)
            worker.done.connect(
                lambda ok, result, s=source, w=worker: self.source_done(s, w, ok, result)
            )
            self.workers.append(worker)
            worker.start()

    def source_done(self, source, worker, ok, result):
        self.pending.discard(source)
        try:
            self.workers.remove(worker)
        except ValueError:
            pass
        if ok:
            self.all_results = universal_search.merge_results(self.all_results, list(result))
        else:
            self.errors[source] = str(result)
        self.refresh_list()
        if self.pending:
            self.status.setText(
                f"⏳ {len(self.all_results)} résultat(s) · encore {len(self.pending)} source(s) en cours…"
            )
        else:
            self.search_btn.setEnabled(True)
            if self.errors:
                labels = [universal_search.source_label(s) for s in self.errors]
                self.status.setText(
                    f"✅ {len(self.all_results)} résultat(s). Sources indisponibles : {', '.join(labels)}."
                )
            else:
                self.status.setText(f"✅ {len(self.all_results)} résultat(s) sur toutes les sources.")

    def visible_results(self):
        favorites = self.favorite_ids if self.favorites_only.isChecked() else None
        return universal_search.filter_results(
            self.all_results, self.source_filter.currentData(), self.type_filter.currentText(),
            self.local_only.isChecked(), favorites,
        )

    def refresh_list(self):
        values = self.visible_results()
        old_key = self.current["key"] if self.current else None
        self.list.blockSignals(True)
        self.list.clear()
        selected = -1
        for i, item in enumerate(values):
            star = "★ " if item["key"] in self.favorite_ids else ""
            local = "🏠" if item["local"] else "☁️"
            text = (
                f"{star}{local} {item['name']}\n"
                f"{item['source_label']} · {item['type']}"
                + (f" · {item['author']}" if item["author"] else "")
            )
            row = QListWidgetItem(text)
            row.setData(0x0100, item)
            row.setToolTip(item["description"])
            self.list.addItem(row)
            if item["key"] == old_key:
                selected = i
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(selected if selected >= 0 else 0)
        else:
            self.current = None
            self.details.setPlainText("Aucun résultat ne correspond aux filtres.")
            self.update_buttons()

    def select(self, current, previous):
        self.current = current.data(0x0100) if current else None
        if not self.current:
            self.update_buttons(); return
        item = self.current
        tags = ", ".join(item["tags"]) or "non indiqués"
        locality = "Pensé pour un usage local / téléchargeable" if item["local"] else "Application ou service à évaluer avant usage local"
        description = html.escape(item["description"] or "Pas de description fournie.")
        action = universal_actions.action_for(item)
        self.details.setHtml(
            f"<h2>{html.escape(item['name'])}</h2>"
            f"<p><b>{html.escape(item['source_label'])}</b> · {html.escape(item['type'])}</p>"
            f"<p>{description}</p>"
            f"<p><b>Auteur :</b> {html.escape(item['author'] or 'non indiqué')}</p>"
            f"<p><b>Tags :</b> {html.escape(tags)}</p>"
            f"<p><b>Mode :</b> {html.escape(locality)}</p>"
            f"<p><b>Action proposée :</b> {html.escape(action['label'])}</p>"
            + (f"<p><a href='{html.escape(item['url'])}'>Ouvrir la page officielle</a></p>" if item["url"] else "")
        )
        self.update_buttons()

    def update_buttons(self):
        has = bool(self.current)
        self.favorite_btn.setEnabled(has)
        self.open_btn.setEnabled(has and bool((self.current or {}).get("url")))
        self.action_btn.setEnabled(has and self.action_process is None)
        if has:
            self.favorite_btn.setText(
                "★ Retirer des favoris" if self.current["key"] in self.favorite_ids else "☆ Ajouter aux favoris"
            )
            self.action_btn.setText(universal_actions.action_for(self.current)["label"])
        else:
            self.action_btn.setText("Action adaptée")

    def toggle_favorite(self):
        if not self.current:
            return
        key = self.current["key"]
        if key in self.favorite_ids:
            self.favorite_ids.remove(key)
        else:
            self.favorite_ids.add(key)
        settings.set("studio_v109_source_favorites", sorted(self.favorite_ids))
        self.refresh_list()

    def open_current(self):
        if self.current and self.current.get("url"):
            QDesktopServices.openUrl(QUrl(self.current["url"]))

    def run_adapted_action(self):
        if not self.current or self.action_process is not None:
            return
        action = universal_actions.action_for(self.current)
        kind = action["kind"]

        if kind == "search":
            self.open_search_result.emit(action["source_index"], action["query"])
            return

        if kind == "pinokio-download":
            reply = QMessageBox.question(
                self, "Télécharger dans Pinokio",
                f"Télécharger « {self.current['name']} » dans Pinokio sans lancer ses scripts ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                command = universal_actions.pinokio_download_command(self.current)
            except Exception as exc:
                QMessageBox.warning(self, "Pinokio", str(exc))
                self.open_pinokio.emit(self.current.get("name", ""))
                return
            self.start_process(command["program"], command["args"], "", "Téléchargement Pinokio")
            return

        if kind == "clone-space":
            git = shutil.which("git")
            if not git:
                QMessageBox.warning(self, "Hugging Face Space", "Git n'est pas installé ou introuvable.")
                return
            parent = QFileDialog.getExistingDirectory(self, "Dossier où cloner le Space")
            if not parent:
                return
            try:
                command = universal_actions.clone_command(self.current, parent, git)
            except Exception as exc:
                QMessageBox.warning(self, "Hugging Face Space", str(exc))
                return
            reply = QMessageBox.question(
                self, "Cloner le Space",
                f"Cloner le dépôt public dans :\n{command['target']}\n\n"
                "Le code sera téléchargé mais ne sera pas exécuté automatiquement.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.start_process(command["program"], command["args"], command["cwd"], "Clonage du Space")
            return

        self.open_current()

    def start_process(self, program, args, cwd, label):
        p = QProcess(self)
        self.action_process = p
        if cwd:
            p.setWorkingDirectory(cwd)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.finished.connect(lambda code, status: self.process_done(p, code, label))
        p.errorOccurred.connect(lambda _e: self.process_error(p, label))
        self.status.setText("⏳ " + label + "…")
        self.update_buttons()
        p.start(program, args)

    def process_error(self, process, label):
        if self.action_process is process:
            self.status.setText("❌ " + label + " : " + process.errorString())

    def process_done(self, process, code, label):
        if self.action_process is not process:
            return
        output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        self.action_process = None
        process.deleteLater()
        self.status.setText(
            ("✅ " if code == 0 else "❌ ") + label + f" · code {code}"
            + (f" · {output[-500:]}" if output else "")
        )
        self.update_buttons()
