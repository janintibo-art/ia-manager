"""Page Source Pinokio v107."""
import html
import platform as py_platform

from PyQt6.QtCore import QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QTextBrowser, QMessageBox, QSplitter
)

from src.backend import pinokio_integration as pinokio


class PinokioPage(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current = None
        self.process = None

        root = QVBoxLayout(self)
        intro = QLabel(
            "Recherchez les applications et modèles disponibles dans le registre Pinokio. "
            "Le téléchargement et le lancement restent deux actions séparées."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Exemples : image, video, TTS, ComfyUI, face, music, 3D…")
        self.query.returnPressed.connect(self.search)
        self.sort = QComboBox()
        for label, value in (
            ("Pertinence", "relevance"), ("Populaires", "popular"),
            ("Tendances", "trending"), ("Récents", "latest"), ("Nom", "name")
        ):
            self.sort.addItem(label, value)
        self.gpu = QComboBox()
        self.gpu.addItem("Tous GPU", "")
        self.gpu.addItem("NVIDIA", "nvidia")
        self.gpu.addItem("AMD", "amd")
        self.gpu.addItem("Apple", "apple")
        search_btn = QPushButton("Rechercher dans Pinokio")
        search_btn.clicked.connect(self.search)
        row.addWidget(self.query, 1); row.addWidget(self.sort); row.addWidget(self.gpu); row.addWidget(search_btn)
        root.addLayout(row)

        status_row = QHBoxLayout()
        self.status = QLabel()
        self.status.setWordWrap(True)
        detect = QPushButton("Détecter Pinokio")
        detect.clicked.connect(self.detect)
        install_pterm = QPushButton("Ouvrir la documentation pterm")
        install_pterm.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/pinokiocomputer/pterm"))
        )
        status_row.addWidget(self.status, 1); status_row.addWidget(detect); status_row.addWidget(install_pterm)
        root.addLayout(status_row)

        split = QSplitter()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.select)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        split.addWidget(self.list); split.addWidget(self.details); split.setSizes([360, 700])
        root.addWidget(split, 1)

        actions = QHBoxLayout()
        self.download_btn = QPushButton("Télécharger dans Pinokio")
        self.run_btn = QPushButton("Lancer / installer dans Pinokio")
        self.open_btn = QPushButton("Ouvrir la fiche / dépôt")
        self.download_btn.clicked.connect(self.download)
        self.run_btn.clicked.connect(self.run_app)
        self.open_btn.clicked.connect(self.open_page)
        actions.addWidget(self.download_btn); actions.addWidget(self.run_btn); actions.addWidget(self.open_btn); actions.addStretch(1)
        root.addLayout(actions)

        self.log = QLabel()
        self.log.setWordWrap(True)
        root.addWidget(self.log)
        self.detect()
        self.update_buttons()

    def platform_key(self):
        name = py_platform.system().lower()
        return "windows" if name.startswith("win") else ("mac" if name == "darwin" else "linux")

    def detect(self):
        state = pinokio.local_status()
        parts = []
        if state["pterm"]:
            parts.append("✅ pterm détecté")
        else:
            parts.append("⚪ pterm absent du PATH")
        if state["running"]:
            version = state.get("version") or {}
            label = version.get("pinokio") or version.get("pinokiod") or ""
            parts.append("✅ Pinokio actif" + (f" ({label})" if label else ""))
        else:
            parts.append("⚪ serveur local Pinokio non détecté sur 127.0.0.1:42000")
        self.status.setText(" · ".join(parts))
        self.update_buttons()

    def search(self):
        self.status.setText("⏳ Recherche dans le registre Pinokio…")
        try:
            self.results = pinokio.search_registry(
                self.query.text(), 30, self.sort.currentData(),
                self.platform_key(), self.gpu.currentData()
            )
        except Exception as exc:
            self.results = []
            self.list.clear()
            self.status.setText("❌ Recherche Pinokio impossible : " + str(exc))
            return
        self.list.clear()
        for index, item in enumerate(self.results):
            tags = ", ".join(item["tags"][:4])
            line = f"{item['name']}\n{item['author']}"
            if tags:
                line += " · " + tags
            qitem = QListWidgetItem(line)
            qitem.setData(0x0100, index)
            qitem.setToolTip(item["description"])
            self.list.addItem(qitem)
        self.status.setText(f"✅ {len(self.results)} résultat(s) Pinokio.")
        if self.list.count():
            self.list.setCurrentRow(0)

    def select(self, current, previous):
        self.current = None
        if not current:
            self.details.clear(); self.update_buttons(); return
        index = current.data(0x0100)
        if not isinstance(index, int) or not (0 <= index < len(self.results)):
            return
        self.current = self.results[index]
        item = self.current
        tags = ", ".join(item["tags"]) or "non indiqués"
        self.details.setHtml(
            f"<h2>{html.escape(item['name'])}</h2>"
            f"<p>{html.escape(item['description'] or 'Pas de description fournie par le registre.')}</p>"
            f"<p><b>Auteur :</b> {html.escape(item['author'] or 'non indiqué')}</p>"
            f"<p><b>Tags :</b> {html.escape(tags)}</p>"
            f"<p><b>Identifiant :</b> {html.escape(item['id'])}</p>"
            "<p><b>Sécurité :</b> IA Manager ne lance jamais automatiquement cette app. "
            "Télécharger clone seulement les fichiers ; Lancer/installer peut exécuter les scripts Pinokio "
            "et demande donc une confirmation séparée.</p>"
        )
        self.update_buttons()

    def update_buttons(self):
        has = bool(self.current)
        pterm = bool(pinokio.pterm_path())
        self.download_btn.setEnabled(has and pterm and bool(self.current.get("install_uri") if self.current else False))
        self.run_btn.setEnabled(has and pterm and bool(self.current.get("install_uri") if self.current else False))
        self.open_btn.setEnabled(has and bool((self.current or {}).get("url") or (self.current or {}).get("repo")))

    def open_page(self):
        if not self.current: return
        url = self.current.get("url") or self.current.get("repo")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def execute(self, command, label):
        if self.process is not None:
            QMessageBox.information(self, "Pinokio", "Une action Pinokio est déjà en cours.")
            return
        p = QProcess(self)
        self.process = p
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.finished.connect(lambda code, status: self.finished_process(p, code, label))
        p.errorOccurred.connect(lambda _err: self.log.setText("❌ " + p.errorString()))
        self.log.setText("⏳ " + label + "…")
        p.start(command["program"], command["args"])

    def finished_process(self, process, code, label):
        if self.process is not process: return
        output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        self.process = None
        process.deleteLater()
        self.log.setText(("✅ " if code == 0 else "❌ ") + label + f" · code {code}" +
                         (f"\n{output[-800:]}" if output else ""))
        self.detect()

    def download(self):
        if not self.current: return
        try:
            command = pinokio.download_command(self.current)
        except Exception as exc:
            QMessageBox.warning(self, "Pinokio", str(exc)); return
        reply = QMessageBox.question(
            self, "Télécharger dans Pinokio",
            f"Cloner « {self.current['name']} » dans le dossier d'applications Pinokio ?\n\n"
            "Cette action utilise pterm download et ne lance pas encore les scripts de l'application.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.execute(command, "Téléchargement Pinokio")

    def run_app(self):
        if not self.current: return
        try:
            command = pinokio.run_command(self.current)
        except Exception as exc:
            QMessageBox.warning(self, "Pinokio", str(exc)); return
        reply = QMessageBox.warning(
            self, "Exécuter une application Pinokio",
            f"« {self.current['name']} » peut exécuter des commandes et installer des dépendances sur ce PC.\n\n"
            "Continuer uniquement si vous faites confiance à cette entrée et à son dépôt source.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.execute(command, "Lancement Pinokio")
