"""Onglet Chat - discuter avec l'IA (locale ou distante), projet actif, fichiers joints,
code copiable, téléchargement du code en zip."""

import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QImage, QKeyEvent, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend import attachments as att
from src.backend import code_tools, providers, settings
from src.backend import model_registry as reg
from src.backend.ai_manager import AIManager
from src.backend.project_manager import now_iso, slugify
from src.ui import style
from src.ui.tabs.projects_tab import get_project_manager
from src.ui.workers import ChatWorker

NO_PROJECT = "(aucun projet — discussion libre)"
MAX_IMAGE_SIDE = 1600
COLORS = {"code_bg": "#2b2d3a", "code_fg": "#e6e6f0", "block_bg": "#0d0e12", "muted": style.TEXT_MUTED}


def qimage_to_png(img: QImage) -> bytes:
    if max(img.width(), img.height()) > MAX_IMAGE_SIDE:
        img = img.scaled(MAX_IMAGE_SIDE, MAX_IMAGE_SIDE, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(data)


class MessageInput(QTextEdit):
    """Zone de saisie : Entrée envoie, Maj+Entrée va à la ligne, Ctrl+V colle aussi les images"""

    def __init__(self, on_send, on_image, on_files):
        super().__init__()
        self.on_send = on_send
        self.on_image = on_image
        self.on_files = on_files
        self.setAcceptRichText(False)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.on_send()
            return
        super().keyPressEvent(event)

    def canInsertFromMimeData(self, source) -> bool:
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.on_image(img)
                return
        if source.hasUrls():
            files = [u.toLocalFile() for u in source.urls() if u.isLocalFile()]
            if files:
                self.on_files(files)
                return
        super().insertFromMimeData(source)


class ChatTab(QWidget):
    """Interface de chat"""

    conversation_saved = pyqtSignal(str)  # identifiant du projet

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.pm = get_project_manager()
        self.worker: Optional[ChatWorker] = None
        self.project_id: Optional[str] = None
        self.messages: List[Dict] = []
        self.pending: List[Dict] = []          # fichiers joints pas encore envoyés
        self.conv_id: Optional[str] = None
        self.conv_created: Optional[str] = None
        self.image_counter = 0
        self.setAcceptDrops(True)
        self.init_ui()
        self.refresh_models()
        self.refresh_projects()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("Discussion")
        title.setObjectName("Title")
        head.addWidget(title)
        head.addStretch()
        self.code_mode = QCheckBox("📦 Mode projet de code")
        self.code_mode.setToolTip("Demande à l'IA d'indiquer le chemin de chaque fichier, "
                                  "pour pouvoir tout télécharger en zip proprement.")
        self.code_mode.setChecked(bool(settings.get("code_mode")))
        self.code_mode.toggled.connect(lambda on: (settings.set("code_mode", on), self.show_hint()))
        head.addWidget(self.code_mode)
        clear_btn = QPushButton("🧹 Nouvelle discussion")
        clear_btn.clicked.connect(self.clear_chat)
        head.addWidget(clear_btn)
        root.addLayout(head)

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Projet :"))
        self.project_select = QComboBox()
        self.project_select.setMinimumWidth(260)
        self.project_select.currentIndexChanged.connect(self.on_project_selected)
        selectors.addWidget(self.project_select, 1)
        selectors.addSpacing(12)
        selectors.addWidget(QLabel("IA :"))
        self.model_select = QComboBox()
        self.model_select.setMinimumWidth(320)
        self.model_select.currentIndexChanged.connect(self.show_hint)
        selectors.addWidget(self.model_select, 2)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser les IA et les projets")
        refresh_btn.clicked.connect(self.refresh_all)
        selectors.addWidget(refresh_btn)
        root.addLayout(selectors)

        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenLinks(False)
        self.chat_display.anchorClicked.connect(self.on_link)
        root.addWidget(self.chat_display, 1)

        self.status = QLabel()
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.status.setOpenExternalLinks(True)
        root.addWidget(self.status)

        self.attach_bar = QWidget()
        self.attach_layout = QHBoxLayout(self.attach_bar)
        self.attach_layout.setContentsMargins(0, 0, 0, 0)
        self.attach_layout.setSpacing(6)
        self.attach_bar.setVisible(False)
        root.addWidget(self.attach_bar)

        input_row = QHBoxLayout()
        attach_btn = QPushButton("📎")
        attach_btn.setToolTip("Joindre des fichiers ou des images\n"
                              "(ou glissez-les dans la fenêtre, ou collez une image avec Ctrl+V)")
        attach_btn.setMinimumHeight(100)
        attach_btn.clicked.connect(self.choose_files)
        input_row.addWidget(attach_btn)
        self.message_input = MessageInput(self.send_message, self.add_qimage, self.add_files)
        self.message_input.setFixedHeight(100)
        self.message_input.setPlaceholderText(
            "Écrivez votre message… (Entrée = envoyer, Maj+Entrée = nouvelle ligne, "
            "📎 ou glisser-déposer pour joindre des fichiers)")
        input_row.addWidget(self.message_input, 1)
        self.send_btn = QPushButton("Envoyer ➤")
        self.send_btn.setObjectName("Primary")
        self.send_btn.setMinimumHeight(100)
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)
        root.addLayout(input_row)

    # ------------------------------------------------------ glisser-déposer
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            self.add_files([u.toLocalFile() for u in md.urls() if u.isLocalFile()])
        elif md.hasImage():
            img = md.imageData()
            if isinstance(img, QImage):
                self.add_qimage(img)
        event.acceptProposedAction()

    # ------------------------------------------------------ fichiers joints
    def choose_files(self):
        start = str(self.pm.files_folder(self.project_id)) if self.project_id else str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self, "Joindre des fichiers", start,
            "Tous les fichiers (*);;Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp);;"
            "Documents (*.pdf *.docx *.txt *.md);;Code (*.py *.js *.ts *.html *.css *.json *.kt *.dart *.java *.cs);;"
            "Archives (*.zip)")
        self.add_files(files)

    def add_files(self, paths: List[str]):
        errors = []
        for path in paths:
            if not path or Path(path).is_dir():
                continue
            try:
                if Path(path).suffix.lower() in att.IMAGE_EXT:
                    img = QImage(path)
                    if img.isNull():
                        raise ValueError("image illisible")
                    a = att.image_attachment(Path(path).name, qimage_to_png(img))
                else:
                    a = att.load_attachment(path)
                self.pending.append(a)
            except Exception as e:
                errors.append(f"{Path(path).name} : {e}")
        self.refresh_attach_bar()
        if errors:
            self.status.setText("⚠️ " + " · ".join(errors))

    def add_qimage(self, img: QImage):
        self.image_counter += 1
        name = f"image_collee_{self.image_counter}.png"
        self.pending.append(att.image_attachment(name, qimage_to_png(img)))
        self.refresh_attach_bar()

    def remove_pending(self, index: int):
        if 0 <= index < len(self.pending):
            self.pending.pop(index)
        self.refresh_attach_bar()

    def refresh_attach_bar(self):
        while self.attach_layout.count():
            item = self.attach_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, a in enumerate(self.pending):
            icon = "🖼️" if a["kind"] == "image" else "📄"
            chip = QPushButton(f"{icon} {a['name']} ({att.human_size(a['size'])})  ✕")
            chip.setObjectName("Chip")
            chip.setToolTip("Cliquer pour retirer ce fichier")
            chip.clicked.connect(lambda _c, idx=i: self.remove_pending(idx))
            self.attach_layout.addWidget(chip)
        self.attach_layout.addStretch()
        self.attach_bar.setVisible(bool(self.pending))
        self.show_hint()

    # ------------------------------------------------------ modèles / projets
    def refresh_all(self):
        self.refresh_models()
        self.refresh_projects()

    def current_ref(self) -> str:
        return self.model_select.currentData() or ""

    def select_ref(self, ref: str) -> bool:
        if not ref:
            return False
        for candidate in (ref, providers.make_ref("ollama", ref)):
            idx = self.model_select.findData(candidate)
            if idx >= 0:
                self.model_select.setCurrentIndex(idx)
                return True
        return False

    def refresh_models(self):
        current = self.current_ref()
        self.model_select.blockSignals(True)
        self.model_select.clear()
        local = self.ai_manager.get_available_models()
        for label, ref in providers.all_model_choices(local):
            self.model_select.addItem(label, ref)
        self.select_ref(current)
        self.model_select.blockSignals(False)
        self.show_hint()

        if self.model_select.count() == 0 and not self.messages:
            self.chat_display.clear()
            if not self.ai_manager.is_ollama_running():
                self.system_message(
                    "⚠️ Aucune IA disponible. Installez Ollama depuis "
                    "<a href='https://ollama.com'>ollama.com</a> pour les IA locales, ou ajoutez "
                    "Claude / ChatGPT dans l'onglet <b>Connexions</b>, puis cliquez sur 🔄."
                )
            else:
                self.system_message(
                    "⚠️ Aucun modèle installé. Allez dans l'onglet <b>Analyse</b> "
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
            self.select_ref(meta.get("default_model", ""))
            self.system_message(f"📁 Projet actif : <b>{html.escape(meta.get('name', pid))}</b>. "
                                "Les discussions seront sauvegardées dans ce projet.")
        self.show_hint()

    def instructions(self) -> str:
        parts = []
        if self.project_id:
            parts.append(self.pm.get_instructions(self.project_id).strip())
        if self.code_mode.isChecked():
            parts.append(code_tools.CODE_MODE_INSTRUCTIONS)
        return "\n\n".join(p for p in parts if p)

    def show_hint(self):
        parts = []
        ref = self.current_ref()
        pid, name = providers.split_ref(ref) if ref else ("", "")
        model = reg.get_model(name) if pid == "ollama" else None
        if model:
            parts.append(f"{reg.CATEGORIES[model['category']]['label']} · {model['desc']}")
        elif pid and pid != "ollama":
            parts.append("☁️ IA en ligne : vos messages et fichiers sont envoyés à ce service.")
        if self.project_id:
            instr = self.pm.get_instructions(self.project_id).strip()
            if instr:
                first = instr.splitlines()[0][:110]
                parts.append(f"📝 Consignes actives : « {first}{'…' if len(instr) > len(first) else ''} »")
            else:
                parts.append("📝 Ce projet n'a pas encore de consignes (onglet Projets).")
        if any(a["kind"] == "image" for a in self.pending) and ref and not att.model_accepts_images(ref):
            parts.append("⚠️ Cette IA ne voit probablement pas les images : choisissez un modèle "
                         "« Images » (ex. qwen3-vl, gemma3) ou Claude / GPT.")
        self.hint.setText("\n".join(parts))

    # ------------------------------------------------------------ affichage
    def append_html(self, fragment: str):
        self.chat_display.append(fragment)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def system_message(self, text: str):
        self.append_html(f"<p style='color:{style.TEXT_MUTED}'>{text}</p>")

    def bubble_html(self, who: str, body_html: str, bg: str, color: str) -> str:
        return (f"<table width='100%' cellpadding='14' cellspacing='0' "
                f"style='background-color:{bg}; margin-top:10px'>"
                f"<tr><td><span style='color:{color}; font-weight:600'>{html.escape(who)}</span>"
                f"<br>{body_html}</td></tr></table>")

    def image_html(self, data_b64: str) -> str:
        img = QImage.fromData(base64.b64decode(data_b64))
        if img.isNull():
            return ""
        if img.width() > 360:
            img = img.scaledToWidth(360, Qt.TransformationMode.SmoothTransformation)
        self.image_counter += 1
        url = QUrl(f"img://chat/{self.image_counter}")
        self.chat_display.document().addResource(QTextDocument.ResourceType.ImageResource.value, url, img)
        return f"<img src='{url.toString()}'> "

    def render_message(self, index: int, model_ref: str):
        m = self.messages[index]
        if m["role"] == "user":
            text = m.get("display", m["content"])
            body = html.escape(text).replace("\n", "<br>")
            if m.get("attachments"):
                body += (f"<br><span style='color:{style.TEXT_MUTED}'>📎 "
                         f"{html.escape(', '.join(m['attachments']))}</span>")
            imgs = "".join(self.image_html(i["data"]) for i in m.get("images", []))
            if imgs:
                body += "<br>" + imgs
            self.append_html(self.bubble_html("Vous", body, style.SURFACE_2, style.ACCENT_HOVER))
        else:
            body = code_tools.markdown_to_html(m["content"], index, COLORS)
            who = f"IA · {providers.label_for(model_ref)[2:].strip()}" if model_ref else "IA"
            self.append_html(self.bubble_html(who, body, style.SURFACE, style.GREEN))

    # ------------------------------------------------------------ liens
    def on_link(self, url: QUrl):
        link = url.toString()
        if link.startswith(("http://", "https://")):
            QDesktopServices.openUrl(url)
            return
        kind, _, rest = link.partition(":")
        try:
            if kind == "copyall":
                QApplication.clipboard().setText(self.messages[int(rest)]["content"])
                self.status.setText("📋 Réponse copiée.")
            elif kind == "copy":
                mi, bi = (int(x) for x in rest.split(":"))
                block = code_tools.extract_code_blocks(self.messages[mi]["content"])[bi]
                QApplication.clipboard().setText(block["code"])
                self.status.setText(f"📋 Code copié ({block['filename'] or block['lang'] or 'bloc'}).")
            elif kind == "save":
                mi, bi = (int(x) for x in rest.split(":"))
                block = code_tools.extract_code_blocks(self.messages[mi]["content"])[bi]
                name = Path(block["filename"] or code_tools.default_name(block, bi + 1)).name
                path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le code",
                                                      str(self.save_folder() / name))
                if path:
                    Path(path).write_text(block["code"] + "\n", encoding="utf-8")
                    self.status.setText(f"💾 Enregistré : {path}")
            elif kind == "zip":
                self.save_zip(int(rest))
        except (IndexError, ValueError) as e:
            self.status.setText(f"⚠️ Action impossible : {e}")

    def save_folder(self) -> Path:
        if self.project_id:
            return self.pm.files_folder(self.project_id)
        return Path.home()

    def save_zip(self, index: int):
        blocks = code_tools.extract_code_blocks(self.messages[index]["content"])
        if not blocks:
            return
        base = slugify((self.pm.get(self.project_id) or {}).get("name", "code")) if self.project_id else "code"
        default = self.save_folder() / f"{base}_{datetime.now():%Y%m%d_%H%M}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le zip", str(default), "Archive zip (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        out = code_tools.build_zip(blocks, path, Path(path).stem)
        folder_url = QUrl.fromLocalFile(str(out.parent)).toString()
        self.status.setText(f"📦 Zip créé : {html.escape(str(out))} — <a href='{folder_url}'>ouvrir le dossier</a>")

    # ------------------------------------------------------------ discussions
    def reset_conversation(self):
        self.messages = []
        self.conv_id = None
        self.conv_created = None
        self.chat_display.clear()
        self.status.setText("")

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
        self.messages = [dict(m) for m in data.get("messages", [])]
        self.conv_id = cid
        self.conv_created = data.get("created")
        ref = data.get("model", "")
        self.select_ref(ref)
        self.system_message(f"📂 Discussion reprise : <b>{html.escape(data.get('title', ''))}</b>")
        for i in range(len(self.messages)):
            self.render_message(i, ref)

    def save_current(self, ref: str):
        if not self.project_id or not self.messages:
            return
        first = next((m.get("display", m["content"]) for m in self.messages if m["role"] == "user"), "")
        title = " ".join(first.split())[:60] or "Discussion"
        existing_title = None
        if self.conv_id:
            try:
                existing_title = self.pm.load_conversation(self.project_id, self.conv_id).get("title")
            except Exception:
                existing_title = None
        self.conv_id = self.pm.save_conversation(self.project_id, {
            "id": self.conv_id,
            "title": existing_title or title,
            "model": ref,
            "created": self.conv_created or now_iso(),
            "messages": self.messages,
        })
        self.conv_created = self.conv_created or now_iso()
        self.conversation_saved.emit(self.project_id)

    def send_message(self):
        ref = self.current_ref()
        text = self.message_input.toPlainText().strip()

        if not ref:
            QMessageBox.warning(self, "Aucune IA", "Installez un modèle ou ajoutez une connexion, "
                                                   "puis sélectionnez-la.")
            return
        if not text and not self.pending:
            return
        if self.worker is not None and self.worker.isRunning():
            return
        if not text:
            text = "Voici les fichiers joints."

        self.messages.append(att.build_message(text, self.pending))
        self.render_message(len(self.messages) - 1, ref)
        self.pending = []
        self.refresh_attach_bar()
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ …")
        self.status.setText("L'IA réfléchit…")

        self.worker = ChatWorker(ref, self.messages, self.instructions())
        self.worker.answered.connect(lambda answer: self.on_answer(ref, answer))
        self.worker.start()

    def on_answer(self, ref: str, text: str):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer ➤")
        self.status.setText("")
        if text.startswith(("Erreur", "Ollama n'est pas lancé")):
            # Pas une vraie réponse : on l'affiche sans la garder dans l'historique
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            self.system_message(f"❌ {html.escape(text)}")
            return
        self.messages.append({"role": "assistant", "content": text})
        self.render_message(len(self.messages) - 1, ref)
        try:
            self.save_current(ref)
        except Exception as e:
            self.system_message(f"⚠️ Sauvegarde impossible : {html.escape(str(e))}")
