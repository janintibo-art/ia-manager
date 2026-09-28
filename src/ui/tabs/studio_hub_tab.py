"""Studio IA v100 : catalogue multi-domaines, outils et pipelines locaux."""
import html

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QTextBrowser, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)

from src.backend import studio_catalog as catalog


class StudioHubTab(QWidget):
    open_local_tools = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.vram = 0.0
        self.ram = 0.0
        self.current_model = None
        root = QVBoxLayout(self)
        title = QLabel("Studio IA local v100")
        title.setObjectName("Title")
        root.addWidget(title)
        self.hardware = QLabel("Compatibilité : lancez Analyse pour utiliser automatiquement la RAM et la VRAM détectées.")
        self.hardware.setWordWrap(True)
        root.addWidget(self.hardware)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._models_page(), "Modèles")
        self.tabs.addTab(self._tools_page(), "Outils")
        self.tabs.addTab(self._pipelines_page(), "Pipelines")

    def _models_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.category = QComboBox(); self.category.addItem("Toutes"); self.category.addItems(catalog.CATEGORIES)
        self.search = QLineEdit(); self.search.setPlaceholderText("Rechercher : code, FLUX, musique, vidéo, 3D, RAG…")
        self.compatible = QCheckBox("Afficher seulement les choix adaptés")
        filters.addWidget(self.category); filters.addWidget(self.search, 1); filters.addWidget(self.compatible)
        lay.addLayout(filters)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.models = QListWidget(); self.models.setMinimumWidth(280)
        self.details = QTextBrowser()
        split.addWidget(self.models); split.addWidget(self.details); split.setSizes([320, 720])
        lay.addWidget(split, 1)
        actions = QHBoxLayout()
        self.model_link = QPushButton("Ouvrir la page du modèle")
        self.model_link.clicked.connect(self.open_model_link)
        local = QPushButton("Ouvrir Outils locaux")
        local.clicked.connect(self.open_local_tools.emit)
        actions.addWidget(self.model_link); actions.addWidget(local); actions.addStretch(1)
        lay.addLayout(actions)
        self.category.currentIndexChanged.connect(self.refresh_models)
        self.search.textChanged.connect(self.refresh_models)
        self.compatible.toggled.connect(self.refresh_models)
        self.models.currentItemChanged.connect(self.show_model)
        self.refresh_models()
        return page

    def _tools_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        intro = QLabel(f"{len(catalog.TOOLS)} outils locaux complémentaires. IA Manager n'installe rien automatiquement depuis cette liste : elle sert de carte de l'atelier.")
        intro.setWordWrap(True); lay.addWidget(intro)
        table = QTableWidget(len(catalog.TOOLS), 4)
        table.setHorizontalHeaderLabels(("Outil", "Famille", "Rôle", "Lien"))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for row, tool in enumerate(catalog.TOOLS):
            for col, value in enumerate((tool['name'], tool['category'], tool['description'], tool['url'])):
                item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole, tool['url']); table.setItem(row, col, item)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.cellDoubleClicked.connect(lambda r, c: QDesktopServices.openUrl(QUrl(table.item(r, 0).data(Qt.ItemDataRole.UserRole))))
        lay.addWidget(table, 1)
        local = QPushButton("Installer / démarrer les moteurs déjà gérés par IA Manager")
        local.clicked.connect(self.open_local_tools.emit); lay.addWidget(local)
        return page

    def _pipelines_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        intro = QLabel("Pipelines conseillés : ils indiquent l'ordre des briques à combiner. Ils ne lancent aucune génération sans votre action.")
        intro.setWordWrap(True); lay.addWidget(intro)
        table = QTableWidget(len(catalog.PIPELINES), 4)
        table.setHorizontalHeaderLabels(("Pipeline", "Famille", "VRAM conseillée", "Chaîne"))
        table.verticalHeader().setVisible(False); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, pipe in enumerate(catalog.PIPELINES):
            values = (pipe['name'], pipe['category'], f"{pipe['min_vram']} Go" if pipe['min_vram'] else "CPU possible", "  →  ".join(pipe['steps']))
            for col, value in enumerate(values): table.setItem(row, col, QTableWidgetItem(str(value)))
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(table, 1)
        return page

    def set_system_info(self, info):
        cap = catalog.hardware_capacity(info)
        self.vram, self.ram = cap['vram'], cap['ram']
        parts = []
        if self.ram: parts.append(f"RAM détectée ~{self.ram:g} Go")
        if self.vram: parts.append(f"VRAM détectée ~{self.vram:g} Go")
        self.hardware.setText("Compatibilité indicative : " + (" · ".join(parts) if parts else "aucune valeur RAM/VRAM exploitable dans l'analyse."))
        self.refresh_models()

    def refresh_models(self):
        if not hasattr(self, 'models'): return
        previous = self.current_model['id'] if self.current_model else None
        self.models.blockSignals(True); self.models.clear(); selected = 0
        values = catalog.filter_models(self.search.text(), self.category.currentText(), self.compatible.isChecked(), self.vram, self.ram)
        for i, model in enumerate(values):
            status, _ = catalog.compatibility(model, self.vram, self.ram)
            icon = {"bon":"✅", "limite":"🟠", "difficile":"🔴", "inconnu":"⚪"}[status]
            item = QListWidgetItem(f"{icon} {model['name']}\n{model['category']} · {model['engine']}")
            item.setData(Qt.ItemDataRole.UserRole, model); item.setToolTip(model['specialty']); self.models.addItem(item)
            if model['id'] == previous: selected = i
        self.models.blockSignals(False)
        if self.models.count(): self.models.setCurrentRow(selected)
        else: self.current_model = None; self.details.setPlainText("Aucun modèle ne correspond à ces filtres.")

    def show_model(self, item, previous):
        self.current_model = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not self.current_model: return
        model = self.current_model; status, reason = catalog.compatibility(model, self.vram, self.ram)
        labels = {"bon":"Bon candidat", "limite":"À tester avec prudence", "difficile":"Très exigeant pour ce profil", "inconnu":"Compatibilité à vérifier"}
        self.details.setHtml(
            f"<h2>{html.escape(model['name'])}</h2>"
            f"<p><b>{labels[status]}</b> — {html.escape(reason)}</p>"
            f"<p><b>Spécialité :</b> {html.escape(model['specialty'])}</p>"
            f"<p><b>Moteur :</b> {html.escape(model['engine'])}</p>"
            f"<p><b>Entrée :</b> {html.escape(model['input'])} &nbsp; <b>Sortie :</b> {html.escape(model['output'])}</p>"
            f"<p><b>Repères :</b> RAM {model['min_ram']} Go · VRAM {model['min_vram']} Go · téléchargement/poids ~{model['size_gb']} Go selon variante et quantification.</p>"
            "<p>Les valeurs sont des repères conservateurs pour trier le catalogue, pas une garantie de fonctionnement ni de vitesse.</p>"
        )

    def open_model_link(self):
        if self.current_model:
            QDesktopServices.openUrl(QUrl(self.current_model['url']))
