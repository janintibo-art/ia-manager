"""Onglet Chat - Discuter avec l'IA"""

import html

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from src.backend.ai_manager import AIManager


class ChatWorker(QThread):
    """Interroge l'IA sans figer la fenêtre"""
    answered = pyqtSignal(str)

    def __init__(self, ai_manager, model, message):
        super().__init__()
        self.ai_manager = ai_manager
        self.model = model
        self.message = message

    def run(self):
        self.answered.emit(self.ai_manager.chat(self.model, self.message))


class ChatTab(QWidget):
    """Interface de chat avec l'IA"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.worker = None
        self.init_ui()
        self.refresh_models()

    def init_ui(self):
        layout = QVBoxLayout()

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Modèle :"))
        self.model_select = QComboBox()
        model_layout.addWidget(self.model_select, 1)
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_models)
        model_layout.addWidget(refresh_btn)
        layout.addLayout(model_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Entrez votre message...")
        input_layout.addWidget(self.message_input)
        self.send_btn = QPushButton("Envoyer")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.setLayout(layout)

    def refresh_models(self):
        self.model_select.clear()
        models = self.ai_manager.get_available_models()
        if models:
            self.model_select.addItems(models)
        elif not self.ai_manager.is_ollama_running():
            self.chat_display.setText(
                "⚠️ Ollama n'est pas lancé. Installez-le depuis https://ollama.com "
                "puis cliquez sur Actualiser."
            )
        else:
            self.chat_display.setText(
                "⚠️ Aucun modèle installé. Allez dans l'onglet « Modèles » pour en télécharger."
            )

    def send_message(self):
        model = self.model_select.currentText()
        message = self.message_input.toPlainText().strip()

        if not model:
            QMessageBox.warning(self, "Erreur", "Aucun modèle sélectionné.")
            return
        if not message:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un message.")
            return
        if self.worker is not None and self.worker.isRunning():
            return

        self.chat_display.append(f"<b>Vous :</b> {html.escape(message)}<br>")
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("…")

        self.worker = ChatWorker(self.ai_manager, model, message)
        self.worker.answered.connect(lambda text: self.on_answer(model, text))
        self.worker.start()

    def on_answer(self, model, text):
        safe = html.escape(text).replace("\n", "<br>")
        self.chat_display.append(f"<b>IA ({html.escape(model)}) :</b> {safe}<br>")
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer")
