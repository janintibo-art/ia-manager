"""Page Mon Studio v103."""
import html

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextBrowser,
    QPushButton, QListWidget, QListWidgetItem, QSplitter, QMessageBox
)

from src.backend import settings, studio_advisor as advisor


class StudioPlannerPage(QWidget):
    open_local_tools = pyqtSignal()

    def __init__(self, hub):
        super().__init__()
        self.hub = hub
        self.current_plan = None
        root = QVBoxLayout(self)
        intro = QLabel(
            "IA Manager prépare un studio cohérent selon la RAM/VRAM détectée. "
            "Aucun modèle lourd n'est téléchargé automatiquement : vous gardez le contrôle."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        row = QHBoxLayout()
        self.pack = QComboBox()
        for p in advisor.PACKS:
            self.pack.addItem(p["name"], p["id"])
        self.refresh_btn = QPushButton("Analyser ce pack")
        self.prepare_btn = QPushButton("Préparer ce pack")
        self.tools_btn = QPushButton("Ouvrir Outils locaux")
        row.addWidget(QLabel("Pack :"))
        row.addWidget(self.pack, 1)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.prepare_btn)
        row.addWidget(self.tools_btn)
        root.addLayout(row)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        split = QSplitter()
        self.models = QListWidget()
        self.details = QTextBrowser()
        split.addWidget(self.models)
        split.addWidget(self.details)
        split.setSizes([420, 650])
        root.addWidget(split, 1)

        self.refresh_btn.clicked.connect(self.refresh)
        self.pack.currentIndexChanged.connect(self.refresh)
        self.prepare_btn.clicked.connect(self.prepare)
        self.tools_btn.clicked.connect(self.open_local_tools.emit)
        self.models.currentItemChanged.connect(self.show_item)
        self.refresh()

    def refresh(self):
        pack_id = self.pack.currentData()
        self.current_plan = advisor.pack_plan(pack_id, self.hub.vram, self.hub.ram)
        p = self.current_plan["pack"]
        cap = []
        if self.hub.ram:
            cap.append(f"RAM ~{self.hub.ram:g} Go")
        if self.hub.vram:
            cap.append(f"VRAM ~{self.hub.vram:g} Go")
        hardware = " · ".join(cap) if cap else "matériel non encore analysé"
        self.summary.setText(
            f"{p['name']} — {p['description']}  |  {hardware}  |  Pipeline conseillé : {p['pipeline']}"
        )
        self.models.clear()
        icons = {"bon": "✅", "limite": "🟠", "difficile": "🔴", "inconnu": "⚪"}
        for model in self.current_plan["models"]:
            item = QListWidgetItem(
                f"{icons.get(model['status'], '⚪')} {model['name']}\n"
                f"{model['engine']} · ~{model['size_gb']:g} Go"
            )
            item.setData(0x0100, ("model", model))
            self.models.addItem(item)
        for tool in self.current_plan["tools"]:
            item = QListWidgetItem(f"🛠 {tool['name']}\n{tool['category']} · {tool['description']}")
            item.setData(0x0100, ("tool", tool))
            self.models.addItem(item)
        if self.models.count():
            self.models.setCurrentRow(0)

    def show_item(self, item, previous):
        if not item:
            self.details.clear()
            return
        kind, data = item.data(0x0100)
        if kind == "model":
            labels = {
                "bon": "Bon candidat pour ce matériel",
                "limite": "Possible avec réglages prudents / offload",
                "difficile": "Trop exigeant pour le profil détecté",
                "inconnu": "Lancez Analyse pour affiner la compatibilité",
            }
            self.details.setHtml(
                f"<h2>{html.escape(data['name'])}</h2>"
                f"<p><b>{labels.get(data['status'], data['status'])}</b></p>"
                f"<p>{html.escape(data['reason'])}</p>"
                f"<p><b>Moteur :</b> {html.escape(data['engine'])}</p>"
                f"<p><b>Taille indicative :</b> ~{data['size_gb']:g} Go selon variante/quantification.</p>"
            )
        else:
            self.details.setHtml(
                f"<h2>{html.escape(data['name'])}</h2>"
                f"<p>{html.escape(data['description'])}</p>"
                f"<p><b>Famille :</b> {html.escape(data['category'])}</p>"
                "<p>Double-cliquez l'outil dans l'onglet Outils du Studio pour ouvrir sa page officielle.</p>"
            )

    def prepare(self):
        if not self.current_plan:
            return
        ids = advisor.suitable_model_ids(self.current_plan)
        self.hub.favorite_ids.update(ids)
        settings.set("studio_v101_favorites", sorted(self.hub.favorite_ids))
        self.hub.refresh_models()

        pipeline = self.current_plan["pack"]["pipeline"]
        index = self.hub.pipeline_templates.findText(pipeline)
        if index >= 0:
            self.hub.pipeline_templates.setCurrentIndex(index)
            self.hub.load_pipeline_template()

        good = sum(1 for m in self.current_plan["models"] if m["status"] == "bon")
        limited = sum(1 for m in self.current_plan["models"] if m["status"] == "limite")
        hard = sum(1 for m in self.current_plan["models"] if m["status"] == "difficile")
        QMessageBox.information(
            self, "Mon Studio",
            f"Pack préparé.\n\n{len(ids)} modèle(s) ajoutés aux favoris.\n"
            f"Compatibilité : {good} bon(s), {limited} limite(s), {hard} trop exigeant(s).\n"
            f"Pipeline conseillé préparé : {pipeline}.\n\n"
            "Aucun téléchargement n'a été lancé automatiquement."
        )
