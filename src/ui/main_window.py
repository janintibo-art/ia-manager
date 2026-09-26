"""Interface principale - PyQt6"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from src.ui.tabs.chat_tab import ChatTab
from src.ui.tabs.models_tab import ModelsTab
from src.ui.tabs.setup_tab import SetupTab


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IA Manager — Gestionnaire d'IA locales")
        self.resize(1280, 860)
        self.setMinimumSize(1000, 700)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.setup_tab = SetupTab()
        self.models_tab = ModelsTab()
        self.chat_tab = ChatTab()

        self.tabs.addTab(self.setup_tab, "⚙️  Analyse du PC")
        self.tabs.addTab(self.models_tab, "📦  Modèles")
        self.tabs.addTab(self.chat_tab, "💬  Chat")

        # Quand un modèle est installé ou supprimé, tous les onglets se mettent à jour
        self.setup_tab.models_changed.connect(self.on_models_changed)
        self.models_tab.models_changed.connect(self.on_models_changed)
        # L'analyse du PC sert aussi à noter la compatibilité des modèles
        self.setup_tab.analysis_done.connect(self.models_tab.set_system_info)
        # Depuis l'analyse, « Voir la fiche » ouvre l'onglet Modèles
        self.setup_tab.show_model.connect(self.open_model)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

    def on_models_changed(self):
        self.models_tab.refresh_installed_models()
        self.chat_tab.refresh_models()
        self.setup_tab.refresh_installed()

    def open_model(self, model_id: str):
        self.models_tab.select_model(model_id)
        self.tabs.setCurrentWidget(self.models_tab)
