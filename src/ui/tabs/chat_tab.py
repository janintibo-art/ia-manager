"""Onglet Chat - Discuter avec l'IA"""

import html
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg
from src.backend.ai_manager import AIManager
from src.ui import style
from src.ui.workers import ChatWorker


class MessageInput(QTextEdit):
    """Zone de saisie : Entrée envoie, Maj+Entrée va à la ligne"""

    def __init__(self, on_send):
        super().__init__()
        self.on_send = on_send

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.on_send()
            return
        super().keyPressEvent(event)


class ChatTab(QWidget):
    """Interface de chat avec l'IA"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.worker: Optional[ChatWorker] = None
        self.init_ui()
        self.refresh_models()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Discussion")
        title.setObjectName("Title")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(QLabel("Modèle :"))
        self.model_select = QComboBox()
        self.model_select.setMinimumWidth(320)
        self.model_select.currentIndexChanged.connect(self.show_model_hint)
        head.addWidget(self.model_select)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser la liste des modèles")
        refresh_btn.clicked.connect(self.refresh_models)
        head.addWidget(refresh_btn)
        clear_btn = QPushButton("🧹 Nouvelle discussion")
        clear_btn.clicked.connect(self.clear_chat)
        head.addWidget(clear_btn)
        root.addLayout(head)

        self.model_hint = QLabel()
        self.model_hint.setObjectName("Muted")
        self.model_hint.setWordWrap(True)
        root.addWidget(self.model_hint)

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        root.addWidget(self.chat_display, 1)

        input_row = QHBoxLayout()
        self.message_input = MessageInput(self.send_message)
        self.message_input.setFixedHeight(100)
        self.message_input.setPlaceholderText("Écrivez votre message… (Entrée pour envoyer, Maj+Entrée pour aller à la ligne)")
        input_row.addWidget(self.message_input, 1)
        self.send_btn = QPushButton("Envoyer ➤")
        self.send_btn.setObjectName("Primary")
        self.send_btn.setMinimumHeight(100)
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)
        root.addLayout(input_row)

    # ------------------------------------------------------------ modèles
    def refresh_models(self):
        current = self.model_select.currentText()
        self.model_select.blockSignals(True)
        self.model_select.clear()
        models = self.ai_manager.get_available_models()
        self.model_select.addItems(models)
        if current in models:
            self.model_select.setCurrentText(current)
        self.model_select.blockSignals(False)
        self.show_model_hint()

        if not models and not self.chat_display.toPlainText().strip():
            if not self.ai_manager.is_ollama_running():
                self.system_message(
                    "⚠️ Ollama n'est pas lancé. Installez-le depuis "
                    "<a href='https://ollama.com'>ollama.com</a>, lancez-le, puis cliquez sur 🔄."
                )
            else:
                self.system_message(
                    "⚠️ Aucun modèle installé. Allez dans l'onglet <b>Analyse du PC</b> "
                    "pour télécharger un modèle conseillé."
                )

    def show_model_hint(self):
        model = reg.get_model(self.model_select.currentText())
        if model:
            cat = reg.CATEGORIES[model["category"]]["label"]
            self.model_hint.setText(f"{cat} · {model['desc']}")
        else:
            self.model_hint.setText("")

    # ------------------------------------------------------------ messages
    def append_html(self, fragment: str):
        self.chat_display.append(fragment)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def system_message(self, text: str):
        self.append_html(f"<p style='color:{style.TEXT_MUTED}'>{text}</p>")

    def bubble(self, who: str, text: str, bg: str, color: str):
        safe = html.escape(text).replace("\n", "<br>")
        self.append_html(
            f"<table width='100%' cellpadding='14' cellspacing='0' "
            f"style='background-color:{bg}; margin-top:10px'>"
            f"<tr><td><span style='color:{color}; font-weight:600'>{html.escape(who)}</span>"
            f"<br>{safe}</td></tr></table>"
        )

    def clear_chat(self):
        self.chat_display.clear()

    def send_message(self):
        model = self.model_select.currentText()
        message = self.message_input.toPlainText().strip()

        if not model:
            QMessageBox.warning(self, "Aucun modèle", "Installez un modèle puis sélectionnez-le.")
            return
        if not message:
            return
        if self.worker is not None and self.worker.isRunning():
            return

        self.bubble("Vous", message, style.SURFACE_2, style.ACCENT_HOVER)
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ …")

        self.worker = ChatWorker(self.ai_manager, model, message)
        self.worker.answered.connect(lambda text: self.on_answer(model, text))
        self.worker.start()

    def on_answer(self, model: str, text: str):
        self.bubble(f"IA · {model}", text, style.SURFACE, style.GREEN)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer ➤")
