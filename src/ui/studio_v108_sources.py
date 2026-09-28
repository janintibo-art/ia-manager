"""Page Sources+ v108."""
import html

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QSplitter
)

from src.backend import extra_sources


class ExtraSourcesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current = None

        root = QVBoxLayout(self)
        intro = QLabel(
            "Sources complémentaires pour découvrir des applications, nœuds et modèles locaux. "
            "Pinokio reste dans son onglet dédié."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        self.source = QComboBox()
        for src in extra_sources.SOURCES:
            self.source.addItem(src["name"], src["id"])
        self.query = QLineEdit()
        self.query.setPlaceholderText("image, video, upscaler, TTS, ComfyUI, 3D…")
        self.query.returnPressed.connect(self.search)
        search = QPushButton("Rechercher / ouvrir")
        search.clicked.connect(self.search)
        site = QPushButton("Ouvrir la source")
        site.clicked.connect(self.open_source)
        top.addWidget(self.source)
        top.addWidget(self.query, 1)
        top.addWidget(search)
        top.addWidget(site)
        root.addLayout(top)

        self.info = QLabel()
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        split = QSplitter()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.select)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        split.addWidget(self.list)
        split.addWidget(self.details)
        split.setSizes([340, 700])
        root.addWidget(split, 1)

        self.source.currentIndexChanged.connect(self.source_changed)
        self.source_changed()

    def source_changed(self):
        src = extra_sources.source_by_id(self.source.currentData())
        local = "local-first" if src["local_first"] else "catalogue/applications"
        self.info.setText(f"{src['category']} · {local} · {src['description']}")
        self.list.clear()
        self.details.clear()
        self.current = None

    def open_source(self):
        src = extra_sources.source_by_id(self.source.currentData())
        QDesktopServices.openUrl(QUrl(src["url"]))

    def search(self):
        sid = self.source.currentData()
        query = self.query.text().strip()
        if sid != "hf-spaces":
            QDesktopServices.openUrl(QUrl(extra_sources.browser_search_url(sid, query)))
            self.info.setText(
                "Cette source est ouverte dans son interface officielle afin d'éviter un scraper fragile."
            )
            return
        try:
            self.results = extra_sources.search_hf_spaces(query)
        except Exception as exc:
            self.list.clear()
            self.info.setText("❌ Recherche Spaces impossible : " + str(exc))
            return
        self.list.clear()
        for i, item in enumerate(self.results):
            tags = ", ".join(item["tags"][:4])
            text = f"{item['name']}\n{item['author']} · {item['sdk'] or 'SDK non indiqué'}"
            if tags:
                text += " · " + tags
            row = QListWidgetItem(text)
            row.setData(0x0100, i)
            self.list.addItem(row)
        self.info.setText(f"✅ {len(self.results)} Space(s) trouvé(s).")
        if self.list.count():
            self.list.setCurrentRow(0)

    def select(self, current, previous):
        self.current = None
        if not current:
            self.details.clear()
            return
        i = current.data(0x0100)
        if not isinstance(i, int) or not (0 <= i < len(self.results)):
            return
        self.current = self.results[i]
        item = self.current
        tags = ", ".join(item["tags"]) or "non indiqués"
        visibility = "privé" if item["private"] else "public"
        self.details.setHtml(
            f"<h2>{html.escape(item['name'])}</h2>"
            f"<p><b>Space :</b> {html.escape(item['id'])}</p>"
            f"<p><b>SDK :</b> {html.escape(item['sdk'] or 'non indiqué')} · "
            f"<b>Visibilité :</b> {visibility} · <b>Likes :</b> {item['likes']}</p>"
            f"<p><b>Tags :</b> {html.escape(tags)}</p>"
            f"<p><a href='{item['url']}'>Ouvrir le Space sur Hugging Face</a></p>"
            "<p>Un Space public peut servir de démonstration ou de base à cloner, mais son exécution "
            "locale dépend de son code, de sa licence et de ses dépendances.</p>"
        )
