"""Onglet Chat - Discuter avec l'IA"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QTextEdit, QLabel, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from src.backend.ai_manager import AIManager


class ChatTab(QWidget):
    """Interface de chat avec l'IA"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.init_ui()

    def init_ui(self):
        """Initialiser l'interface du chat"""
        layout = QVBoxLayout()

        # Sélection du modèle
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Modèle :"))

        self.model_select = QComboBox()
        self.model_select.addItem("Sélectionner un modèle...")
        self.refresh_models()

        model_layout.addWidget(self.model_select)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_models)
        model_layout.addWidget(refresh_btn)

        layout.addLayout(model_layout)

        # Historique du chat
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Saisie du message
        input_layout = QHBoxLayout()

        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Entrez votre message...")
        input_layout.addWidget(self.message_input)

        send_btn = QPushButton("Envoyer")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def refresh_models(self):
        """Actualiser la liste des modèles disponibles"""
        self.model_select.clear()
        models = self.ai_manager.get_available_models()

        if models:
            for model in models:
                self.model_select.addItem(model)
        else:
            self.model_select.addItem("Aucun modèle disponible")
            self.chat_display.setText("⚠️ Aucun modèle disponible. Allez à l'onglet 'Modèles' pour en télécharger.")

    def send_message(self):
        """Envoyer un message à l'IA"""
        model = self.model_select.currentText()
        message = self.message_input.toPlainText().strip()

        if not message:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un message.")
            return

        if model == "Sélectionner un modèle..." or not model:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un modèle.")
            return

        # Afficher le message de l'utilisateur
        self.chat_display.append(f"<b>Vous :</b> {message}\n")
        self.message_input.clear()

        # Obtenir la réponse
        try:
            response = self.ai_manager.chat(model, message)
            self.chat_display.append(f"<b>IA ({model}) :</b> {response}\n")
        except Exception as e:
            self.chat_display.append(f"<b style='color:red'>Erreur :</b> {str(e)}\n")
