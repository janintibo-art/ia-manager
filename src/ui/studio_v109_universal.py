"""Page Recherche universelle v109."""
import html

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QListWidget, QListWidgetItem, QTextBrowser, QSplitter
)

from src.backend import settings, universal_search
from src.ui.workers import FunctionWorker


class UniversalSearchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.all_results = []
        self.workers = []
        self.errors = {}
        self.pending = set()
        self.favorite_ids = set(settings.get("studio_v109_source_favorites") or [])
        self.current = None

        root = QVBoxLayout(self)
        intro = QLabel(
            "Une seule recherche interroge plusieurs catalogues en parallèle. "
            "Une source en erreur n'empêche pas les autres de répondre."
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
        self.favorite_btn = QPushButton("☆ Ajouter aux favoris")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.open_btn = QPushButton("Ouvrir la source")
        self.open_btn.clicked.connect(self.open_current)
        self.pinokio_btn = QPushButton("Voir dans l'onglet Pinokio")
        self.pinokio_btn.setVisible(False)
        actions.addWidget(self.favorite_btn); actions.addWidget(self.open_btn); actions.addWidget(self.pinokio_btn); actions.addStretch(1)
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
                    f"✅ {len(self.all_results)} résultat(s). "
                    f"Sources indisponibles : {', '.join(labels)}."
                )
            else:
                self.status.setText(f"✅ {len(self.all_results)} résultat(s) sur toutes les sources.")

    def visible_results(self):
        favorites = self.favorite_ids if self.favorites_only.isChecked() else None
        return universal_search.filter_results(
            self.all_results,
            self.source_filter.currentData(),
            self.type_filter.currentText(),
            self.local_only.isChecked(),
            favorites,
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
        self.details.setHtml(
            f"<h2>{html.escape(item['name'])}</h2>"
            f"<p><b>{html.escape(item['source_label'])}</b> · {html.escape(item['type'])}</p>"
            f"<p>{description}</p>"
            f"<p><b>Auteur :</b> {html.escape(item['author'] or 'non indiqué')}</p>"
            f"<p><b>Tags :</b> {html.escape(tags)}</p>"
            f"<p><b>Mode :</b> {html.escape(locality)}</p>"
            + (f"<p><a href='{html.escape(item['url'])}'>Ouvrir la page officielle</a></p>" if item["url"] else "")
        )
        self.update_buttons()

    def update_buttons(self):
        has = bool(self.current)
        self.favorite_btn.setEnabled(has)
        self.open_btn.setEnabled(has and bool((self.current or {}).get("url")))
        if has:
            self.favorite_btn.setText(
                "★ Retirer des favoris" if self.current["key"] in self.favorite_ids else "☆ Ajouter aux favoris"
            )

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
