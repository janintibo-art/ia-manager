"""Onglet Chat - discuter avec l'IA, avec projet actif (consignes + sauvegarde auto)"""

import html
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg
from src.backend.ai_manager import AIManager
from src.backend.project_manager import now_iso
from src.ui import style
from src.ui.tabs.projects_tab import get_project_manager
from src.ui.workers import ChatWorker

NO_PROJECT = "(aucun projet — discussion libre)"


class MessageInput(QTextEdit):
    """Zone de saisie : Entrée envoie, Maj+Entrée va à la ligne"""

    def __init__(self, on_send):
        super().__init__()
        self.on_send = on_send
        self.setAcceptRichText(False)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.on_send()
            return
        super().keyPressEvent(event)


class ChatTab(QWidget):
    """Interface de chat avec l'IA"""

    conversation_saved = pyqtSignal(str)  # identifiant du projet

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.pm = get_project_manager()
        self.worker: Optional[ChatWorker] = None
        self.project_id: Optional[str] = None
        self.messages: List[Dict] = []
        self.conv_id: Optional[str] = None
        self.conv_created: Optional[str] = None
        self.init_ui()
        self.refresh_models()
        self.refresh_projects()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Discussion")
        title.setObjectName("Title")
        head.addWidget(title)
        head.addStretch()
        clear_btn = QPushButton("🧹 Nouvelle discussion")
        clear_btn.clicked.connect(self.clear_chat)
        head.addWidget(clear_btn)
        root.addLayout(head)

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Projet :"))
        self.project_select = QComboBox()
        self.project_select.setMinimumWidth(300)
        self.project_select.currentIndexChanged.connect(self.on_project_selected)
        selectors.addWidget(self.project_select, 1)
        selectors.addSpacing(16)
        selectors.addWidget(QLabel("Modèle :"))
        self.model_select = QComboBox()
        self.model_select.setMinimumWidth(280)
        self.model_select.currentIndexChanged.connect(self.show_hint)
        selectors.addWidget(self.model_select, 1)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser les modèles et les projets")
        refresh_btn.clicked.connect(self.refresh_all)
        selectors.addWidget(refresh_btn)
        root.addLayout(selectors)

        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        root.addWidget(self.chat_display, 1)

        input_row = QHBoxLayout()
        self.message_input = MessageInput(self.send_message)
        self.message_input.setFixedHeight(100)
        self.message_input.setPlaceholderText(
            "Écrivez votre message… (Entrée pour envoyer, Maj+Entrée pour aller à la ligne)")
        input_row.addWidget(self.message_input, 1)
        self.send_btn = QPushButton("Envoyer ➤")
        self.send_btn.setObjectName("Primary")
        self.send_btn.setMinimumHeight(100)
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)
        root.addLayout(input_row)

    # ------------------------------------------------------ modèles / projets
    def refresh_all(self):
        self.refresh_models()
        self.refresh_projects()

    def refresh_models(self):
        current = self.model_select.currentText()
        self.model_select.blockSignals(True)
        self.model_select.clear()
        models = self.ai_manager.get_available_models()
        self.model_select.addItems(models)
        if current in models:
            self.model_select.setCurrentText(current)
        self.model_select.blockSignals(False)
        self.show_hint()

        if not models and not self.messages:
            self.chat_display.clear()
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

    def refresh_projects(self):
        self.pm = get_project_manager()
        keep = self.project_id
        self.project_select.blockSignals(True)
        self.project_select.clear()
        self.project_select.addItem(NO_PROJECT, "")
        for p in sorted(self.pm.list_projects(), key=lambda p: (not p["favorite"], p["name"].lower())):
            star = "⭐ " if p["favorite"] else ""
            self.project_select.addItem(f"{star}{p['name']}", p["id"])
        idx = self.project_select.findData(keep or "")
        if idx < 0:
            idx = 0
            self.project_id = None
        self.project_select.setCurrentIndex(idx)
        self.project_select.blockSignals(False)
        self.show_hint()

    def on_project_selected(self, _index: int):
        pid = self.project_select.currentData() or None
        if pid == self.project_id:
            return
        self.project_id = pid
        self.reset_conversation()
        if pid:
            meta = self.pm.get(pid) or {}
            wanted = meta.get("default_model", "")
            if wanted and self.model_select.findText(wanted) >= 0:
                self.model_select.setCurrentText(wanted)
            self.system_message(f"📁 Projet actif : <b>{html.escape(meta.get('name', pid))}</b>. "
                                "Les discussions seront sauvegardées dans ce projet.")
        self.show_hint()

    def instructions(self) -> str:
        return self.pm.get_instructions(self.project_id) if self.project_id else ""

    def show_hint(self):
        parts = []
        model = reg.get_model(self.model_select.currentText())
        if model:
            parts.append(f"{reg.CATEGORIES[model['category']]['label']} · {model['desc']}")
        if self.project_id:
            instr = self.instructions().strip()
            if instr:
                first = instr.splitlines()[0][:110]
                parts.append(f"📝 Consignes actives : « {first}{'…' if len(instr) > len(first) else ''} »")
            else:
                parts.append("📝 Ce projet n'a pas encore de consignes (onglet Projets).")
        self.hint.setText("\n".join(parts))

    # ------------------------------------------------------------ affichage
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

    def render_message(self, m: Dict, model: str):
        if m["role"] == "user":
            self.bubble("Vous", m["content"], style.SURFACE_2, style.ACCENT_HOVER)
        else:
            self.bubble(f"IA · {model}", m["content"], style.SURFACE, style.GREEN)

    # ------------------------------------------------------------ discussions
    def reset_conversation(self):
        self.messages = []
        self.conv_id = None
        self.conv_created = None
        self.chat_display.clear()

    def clear_chat(self):
        self.reset_conversation()
        if self.project_id:
            meta = self.pm.get(self.project_id) or {}
            self.system_message(f"📁 Nouvelle discussion dans <b>{html.escape(meta.get('name', ''))}</b>.")

    def select_project(self, pid: str):
        self.refresh_projects()
        idx = self.project_select.findData(pid)
        if idx >= 0:
            self.project_select.setCurrentIndex(idx)
            self.on_project_selected(idx)

    def new_conversation_in(self, pid: str):
        self.select_project(pid)
        self.clear_chat()

    def load_conversation(self, pid: str, cid: str):
        """Rouvrir une discussion sauvegardée"""
        self.select_project(pid)
        data = self.pm.load_conversation(pid, cid)
        self.reset_conversation()
        self.messages = [{"role": m["role"], "content": m["content"]} for m in data.get("messages", [])]
        self.conv_id = cid
        self.conv_created = data.get("created")
        model = data.get("model", "")
        if model and self.model_select.findText(model) >= 0:
            self.model_select.setCurrentText(model)
        self.system_message(f"📂 Discussion reprise : <b>{html.escape(data.get('title', ''))}</b>")
        for m in self.messages:
            self.render_message(m, model)

    def save_current(self, model: str):
        if not self.project_id or not self.messages:
            return
        first_user = next((m["content"] for m in self.messages if m["role"] == "user"), "Discussion")
        title = " ".join(first_user.split())[:60]
        existing_title = None
        if self.conv_id:
            try:
                existing_title = self.pm.load_conversation(self.project_id, self.conv_id).get("title")
            except Exception:
                existing_title = None
        self.conv_id = self.pm.save_conversation(self.project_id, {
            "id": self.conv_id,
            "title": existing_title or title,
            "model": model,
            "created": self.conv_created or now_iso(),
            "messages": self.messages,
        })
        self.conv_created = self.conv_created or now_iso()
        self.conversation_saved.emit(self.project_id)

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

        self.messages.append({"role": "user", "content": message})
        self.render_message(self.messages[-1], model)
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ …")

        self.worker = ChatWorker(self.ai_manager, model, self.messages, self.instructions())
        self.worker.answered.connect(lambda text: self.on_answer(model, text))
        self.worker.start()

    def on_answer(self, model: str, text: str):
        if text.startswith(("Erreur", "Ollama n'est pas lancé")):
            # Pas une vraie réponse : on l'affiche sans la garder dans l'historique
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            self.system_message(f"❌ {html.escape(text)}")
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Envoyer ➤")
            return
        self.messages.append({"role": "assistant", "content": text})
        self.render_message(self.messages[-1], model)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer ➤")
        try:
            self.save_current(model)
        except Exception as e:
            self.system_message(f"⚠️ Sauvegarde impossible : {html.escape(str(e))}")
