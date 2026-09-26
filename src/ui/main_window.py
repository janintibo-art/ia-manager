"""Interface principale - PyQt6"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon
from src.ui.tabs.chat_tab import ChatTab
from src.ui.tabs.models_tab import ModelsTab
from src.ui.tabs.setup_tab import SetupTab


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialiser l'interface utilisateur"""
        self.setWindowTitle("IA Manager - Gestionnaire d'IA Locales")
        self.setGeometry(100, 100, 1000, 700)

        # Onglets
        tabs = QTabWidget()

        self.chat_tab = ChatTab()
        self.models_tab = ModelsTab()
        self.setup_tab = SetupTab()

        tabs.addTab(self.chat_tab, "💬 Chat")
        tabs.addTab(self.models_tab, "📦 Modèles")
        tabs.addTab(self.setup_tab, "⚙️ Configuration")

        # Layout principal
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(tabs)

        self.setCentralWidget(central_widget)
