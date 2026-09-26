"""Interface principale - PyQt6"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from src.ui.tabs.chat_tab import ChatTab
from src.ui.tabs.github_tab import GithubTab
from src.ui.tabs.models_tab import ModelsTab
from src.ui.tabs.projects_tab import ProjectsTab
from src.ui.tabs.setup_tab import SetupTab


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IA Manager — Gestionnaire d'IA locales")
        self.resize(1320, 880)
        self.setMinimumSize(1050, 720)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.setup_tab = SetupTab()
        self.models_tab = ModelsTab()
        self.projects_tab = ProjectsTab()
        self.chat_tab = ChatTab()
        self.github_tab = GithubTab()

        self.tabs.addTab(self.setup_tab, "⚙️  Analyse du PC")
        self.tabs.addTab(self.models_tab, "📦  Modèles")
        self.tabs.addTab(self.projects_tab, "📁  Projets")
        self.tabs.addTab(self.chat_tab, "💬  Chat")
        self.tabs.addTab(self.github_tab, "🐙  GitHub")

        # Modèles installés ou supprimés : tous les onglets se mettent à jour
        self.setup_tab.models_changed.connect(self.on_models_changed)
        self.models_tab.models_changed.connect(self.on_models_changed)
        # L'analyse du PC sert aussi à noter la compatibilité des modèles
        self.setup_tab.analysis_done.connect(self.models_tab.set_system_info)
        # Depuis l'analyse, « Fiche » ouvre l'onglet Modèles
        self.setup_tab.show_model.connect(self.open_model)

        # Projets <-> Chat
        self.projects_tab.open_conversation.connect(self.open_conversation)
        self.projects_tab.new_conversation.connect(self.new_conversation)
        self.projects_tab.projects_changed.connect(self.on_projects_changed)
        self.chat_tab.conversation_saved.connect(self.projects_tab.on_conversation_saved)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

    def on_models_changed(self):
        self.models_tab.refresh_installed_models()
        self.chat_tab.refresh_models()
        self.setup_tab.refresh_installed()
        self.projects_tab.refresh_models()

    def on_projects_changed(self):
        self.chat_tab.refresh_projects()
        self.chat_tab.show_hint()
        self.github_tab.refresh_projects()

    def open_model(self, model_id: str):
        self.models_tab.select_model(model_id)
        self.tabs.setCurrentWidget(self.models_tab)

    def open_conversation(self, pid: str, cid: str):
        self.chat_tab.load_conversation(pid, cid)
        self.tabs.setCurrentWidget(self.chat_tab)

    def new_conversation(self, pid: str):
        self.chat_tab.new_conversation_in(pid)
        self.tabs.setCurrentWidget(self.chat_tab)
