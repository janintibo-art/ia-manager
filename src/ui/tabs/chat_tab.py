"""Onglet Chat - discuter avec l'IA (locale ou distante), projet actif, fichiers joints,
code copiable, téléchargement du code en zip."""

import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QImage, QImageReader, QKeyEvent, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMenu,
    QMessageBox, QPlainTextEdit, QPushButton, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend import attachments as att
from src.backend import code_tools, providers, settings, change_review
from src.backend import github_tools as gt
from src.backend import quick_commands as qc
from src.backend import model_registry as reg
from src.backend import web_tools, project_memory
from src.backend.ai_manager import AIManager
from src.backend.project_manager import now_iso, slugify
from src.ui import style
from src.ui.tabs.projects_tab import get_project_manager
from src.ui.dialogs import ModelSettingsDialog, QuickCommandsDialog
from src.ui.change_review_dialog import ChangeReviewDialog
from src.ui.tabs.github_tab import CommandRunner
from src.ui.workers import AttachmentWorker, FunctionWorker, StreamWorker

NO_PROJECT = "(aucun projet — discussion libre)"
MAX_IMAGE_SIDE = 1600


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


def load_chat_file(path):
    att.check_size(path)
    if Path(path).suffix.lower() in att.IMAGE_EXT:
        dimensions = QImageReader(path).size()
        if dimensions.isValid() and dimensions.width() * dimensions.height() > 16_000_000:
            raise ValueError("image trop grande : 16 millions de pixels maximum")
        img = QImage(path)
        if img.isNull():
            raise ValueError("image illisible")
        return att.image_attachment(Path(path).name, qimage_to_png(img))
    return att.load_attachment(path)



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
        self.worker: Optional[StreamWorker] = None
        self.stream_pos = 0
        self.abandoned: List[StreamWorker] = []
        self.stream_buffer: List[str] = []
        self.stream_ref = ""
        self.system_info: Optional[Dict] = None
        self.flush_timer = QTimer(self)
        self.flush_timer.setInterval(60)
        self.flush_timer.timeout.connect(self.flush_stream)
        self.project_id: Optional[str] = None
        self.messages: List[Dict] = []
        self.pending: List[Dict] = []          # fichiers joints pas encore envoyés
        self.conv_id: Optional[str] = None
        self.conv_created: Optional[str] = None
        self.image_counter = 0
        self.attachment_worker = None
        self.attachment_gen = 0
        self.attachment_loading = False
        self.apply_runner = CommandRunner(self)
        self.apply_runner.output.connect(self.on_apply_output)
        self.apply_runner.done.connect(self.on_apply_done)
        self.apply_folder = ""
        self.web_worker: Optional[FunctionWorker] = None
        self.web_ctx = ""
        self.memory_ctx = ""
        self.memory_sources = []
        self.web_sources: List[Dict] = []
        self.web_gen = 0
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
        self.web_mode = QCheckBox("🌐 Internet")
        self.web_mode.setToolTip("Avant d'envoyer, cherche sur internet et donne les résultats "
                                 "(avec les sources) à l'IA — utile pour l'actualité ou un sujet récent.")
        self.web_mode.setChecked(bool(settings.get("web_search")))
        self.web_mode.toggled.connect(lambda on: settings.set("web_search", on))
        head.addWidget(self.web_mode)
        self.memory_mode = QCheckBox("📚 Documents du projet")
        self.memory_mode.setChecked(bool(settings.get("project_memory_enabled")))
        self.memory_mode.toggled.connect(lambda on: settings.set("project_memory_enabled", on))
        head.addWidget(self.memory_mode)
        self.commands_btn = QPushButton("⚡ Commandes")
        self.commands_btn.setToolTip("Commandes rapides : tapez par exemple /resume suivi de votre texte")
        self.commands_menu = QMenu(self)
        self.commands_menu.aboutToShow.connect(self.fill_commands_menu)
        self.commands_btn.setMenu(self.commands_menu)
        head.addWidget(self.commands_btn)
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
        settings_btn = QPushButton("⚙️")
        settings_btn.setToolTip("Réglages de cette IA : répartition VRAM/RAM, mémoire, créativité")
        settings_btn.clicked.connect(self.open_model_settings)
        selectors.addWidget(settings_btn)
        root.addLayout(selectors)

        self.profile_instructions = ""
        self.profile_label = QLabel("Profil : aucun")
        root.addWidget(self.profile_label)
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

        self.apply_console = QPlainTextEdit()
        self.apply_console.setObjectName("Console")
        self.apply_console.setReadOnly(True)
        self.apply_console.setMaximumBlockCount(2000)
        self.apply_console.setFixedHeight(120)
        self.apply_console.setVisible(False)
        root.addWidget(self.apply_console)
        self.restore_code_btn = QPushButton("↶ Restaurer la dernière application de code")
        self.restore_code_btn.setToolTip("Restaure les fichiers locaux ; ne réécrit pas les commits GitHub.")
        self.restore_code_btn.setEnabled(bool(settings.get("last_code_backup")))
        self.restore_code_btn.clicked.connect(self.restore_code)
        root.addWidget(self.restore_code_btn)

        self.attach_bar = QWidget()
        self.attach_layout = QHBoxLayout(self.attach_bar)
        self.attach_layout.setContentsMargins(0, 0, 0, 0)
        self.attach_layout.setSpacing(6)
        self.attach_bar.setVisible(False)
        root.addWidget(self.attach_bar)
        self.cancel_attach_btn = QPushButton("Annuler le chargement des documents")
        self.cancel_attach_btn.setVisible(False)
        self.cancel_attach_btn.clicked.connect(self.cancel_attachments)
        root.addWidget(self.cancel_attach_btn)

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
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setMinimumHeight(100)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_generation)
        input_row.addWidget(self.stop_btn)
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
        paths = [p for p in paths if p and not Path(p).is_dir()]
        if not paths:
            return
        if self.attachment_worker is not None:
            self.status.setText("Un chargement est en cours. Attendez ou annulez-le avant d'ajouter d'autres fichiers.")
            return
        self.attachment_gen += 1
        generation = self.attachment_gen
        worker = AttachmentWorker(paths, load_chat_file)
        self.attachment_worker = worker
        self.attachment_loading = True
        worker.finished.connect(lambda: self.attachment_finished(worker))
        worker.progress.connect(lambda i, n, name: self.attachment_progress(generation, i, n, name))
        worker.loaded.connect(lambda result, errors: self.attachments_loaded(generation, result, errors))
        self.cancel_attach_btn.setVisible(True)
        self.status.setText("Chargement des documents…")
        worker.start()

    def attachment_progress(self, generation, index, total, name):
        if generation == self.attachment_gen:
            self.status.setText(f"Lecture {index}/{total} : {name}")

    def attachments_loaded(self, generation, result, errors):
        if generation != self.attachment_gen:
            return
        self.attachment_loading = False
        self.cancel_attach_btn.setVisible(False)
        self.pending.extend(result)
        self.refresh_attach_bar()
        self.status.setText("⚠️ " + " · ".join(errors) if errors else f"{len(result)} fichier(s) chargé(s).")

    def cancel_attachments(self):
        self.attachment_gen += 1
        if self.attachment_worker is not None:
            self.attachment_worker.stop()
        self.attachment_loading = False
        self.cancel_attach_btn.setVisible(False)
        self.status.setText("Chargement annulé. Aucun fichier du lot n'a été ajouté.")

    def attachment_finished(self, worker):
        if self.attachment_worker is worker:
            self.attachment_worker = None

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
        parts = [getattr(self, "profile_instructions", "")]
        if self.memory_ctx:
            parts.append(self.memory_ctx)
        if self.project_id:
            parts.append(self.pm.get_instructions(self.project_id).strip())
        if self.code_mode.isChecked():
            parts.append(code_tools.CODE_MODE_INSTRUCTIONS)
        if self.web_ctx:
            parts.append("Tu as accès à ces informations trouvées à l'instant sur internet — "
                         "utilise-les si elles sont utiles, ignore-les sinon :\n\n" + self.web_ctx)
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
            body = code_tools.markdown_to_html(m["content"], index, style.code_colors())
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
            elif kind == "apply":
                self.apply_to_repo(int(rest))
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

    # ------------------------------------------------------------ appliquer au dépôt
    def apply_to_repo(self, index: int):
        blocks = code_tools.extract_code_blocks(self.messages[index]["content"])
        if not blocks:
            return
        if self.apply_runner.busy():
            QMessageBox.information(self, "Déjà en cours", "Une application au dépôt est déjà en cours.")
            return
        if not self.project_id:
            QMessageBox.information(self, "Aucun projet actif",
                                    "Choisissez un projet en haut du Chat : c'est son dossier de dépôt "
                                    "(configuré dans l'onglet Projets ou GitHub) qui recevra les fichiers.")
            return
        meta = self.pm.get(self.project_id) or {}
        folder = (meta.get("pc_folder") or "").strip()
        if not folder or not Path(folder).is_dir():
            QMessageBox.information(
                self, "Dossier du dépôt manquant",
                "Ce projet n'a pas encore de dossier de dépôt sur ce PC.\n\n"
                "Indiquez-le dans l'onglet Projets (champ « Dossier sur ce PC »), ou clonez le dépôt "
                "depuis l'onglet GitHub, puis réessayez.")
            return
        try:
            review = change_review.prepare(blocks, folder)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Aperçu impossible", str(error))
            return
        if not review["entries"]:
            self.status.setText("Les fichiers proposés sont déjà identiques : rien à appliquer.")
            return
        dialog = ChangeReviewDialog(review, self)
        if not dialog.exec():
            return
        message = ""
        if dialog.publish:
            if not gt.tool_status()["git"]:
                QMessageBox.information(self, "Git manquant", "Installez Git avant l'envoi au dépôt.")
                return
            message, ok = QInputDialog.getText(self, "Message de commit", "Ce qui a changé :",
                                               text="Code ajouté depuis le Chat IA Manager")
            if not ok:
                return  # rien n'a encore été écrit
        try:
            backup = change_review.apply(review)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Application impossible", str(error))
            return
        self.last_code_backup = backup
        self.restore_code_btn.setEnabled(True)
        try:
            settings.set("last_code_backup", backup)
        except OSError:
            QMessageBox.warning(self, "Sauvegarde conservée", "Le raccourci n'a pas pu être enregistré. "
                                "La sauvegarde reste disponible ici :\n" + backup)
        if not dialog.publish:
            self.status.setText("Fichiers appliqués localement. Sauvegarde disponible pour revenir en arrière.")
            return
        self.apply_folder = folder
        self.apply_console.clear()
        self.apply_console.setVisible(True)
        self.restore_code_btn.setEnabled(False)
        self.status.setText("⏳ Envoi des fichiers vérifiés vers le dépôt…")
        names = [entry["name"] for entry in review["entries"]]
        self.apply_runner.run(change_review.commit_steps(names, message.strip() or "Mise à jour"), folder)

    def restore_code(self):
        if self.apply_runner.busy():
            return
        backup = getattr(self, "last_code_backup", "") or settings.get("last_code_backup")
        if not backup:
            return
        try:
            import json
            manifest = json.loads((Path(backup) / "manifest.json").read_text(encoding="utf-8"))
            listing = "\n".join(entry["name"] for entry in manifest["files"])
            prompt = (f"Restaurer les fichiers locaux dans :\n{manifest['root']}\n\n{listing}\n\n"
                      "Les nouveaux fichiers seront supprimés. Les fichiers modifiés depuis l'application "
                      "bloqueront la restauration. Les commits déjà envoyés sur GitHub restent en place.")
            if QMessageBox.question(self, "Restaurer la sauvegarde", prompt,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                    ) != QMessageBox.StandardButton.Yes:
                return
            folder = change_review.restore(backup)
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.warning(self, "Restauration impossible", str(error))
            return
        self.last_code_backup = ""
        self.restore_code_btn.setEnabled(False)
        try:
            settings.set("last_code_backup", "")
        except OSError:
            pass
        self.status.setText(f"Fichiers restaurés dans {folder}. Aucun envoi GitHub effectué.")

    def on_apply_output(self, text: str):
        self.apply_console.moveCursor(QTextCursor.MoveOperation.End)
        self.apply_console.insertPlainText(gt.strip_ansi(text))
        self.apply_console.moveCursor(QTextCursor.MoveOperation.End)

    def on_apply_done(self, code: int):
        self.restore_code_btn.setEnabled(bool(getattr(self, "last_code_backup", "") or settings.get("last_code_backup")))
        if code == 0:
            self.status.setText(f"✅ Code envoyé sur GitHub depuis {self.apply_folder}.")
        else:
            self.status.setText("⚠️ L'envoi vers le dépôt a échoué — détail dans la zone ci-dessus.")

    # ------------------------------------------------------------ discussions
    def reset_conversation(self):
        self.cancel_attachments()
        self.pending = []
        self.refresh_attach_bar()
        self.web_gen += 1
        self.memory_ctx = ""
        self.memory_sources = []
        self.web_ctx = ""
        self.web_sources = []
        if self.worker is not None and self.worker.isRunning():
            # Une réponse arrivait encore : on l'abandonne pour ne pas polluer la nouvelle discussion
            try:
                self.worker.done.disconnect()
                self.worker.token.disconnect()
                self.worker.phase.disconnect()
            except TypeError:
                pass
            self.worker.stop()
            # garder une référence tant qu'il tourne (détruire un QThread actif ferme l'application)
            self.abandoned = [w for w in self.abandoned if w.isRunning()] + [self.worker]
            self.worker = None
            self.flush_timer.stop()
            self.stream_buffer.clear()
            self.send_btn.setVisible(True)
            self.stop_btn.setVisible(False)
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

    # ------------------------------------------------------------ commandes rapides
    def fill_commands_menu(self):
        self.commands_menu.clear()
        for c in qc.load():
            action = self.commands_menu.addAction(f"{c['trigger']}   {c['name']}")
            action.triggered.connect(lambda _c=False, t=c["trigger"]: self.insert_command(t))
        self.commands_menu.addSeparator()
        manage = self.commands_menu.addAction("✏️ Gérer les commandes…")
        manage.triggered.connect(self.manage_commands)

    def insert_command(self, trigger: str):
        current = self.message_input.toPlainText()
        if current.startswith("/"):
            current = current.partition(" ")[2]
        self.message_input.setPlainText(f"{trigger} {current}")
        self.message_input.moveCursor(QTextCursor.MoveOperation.End)
        self.message_input.setFocus()

    def manage_commands(self):
        QuickCommandsDialog(self).exec()

    # ------------------------------------------------------------ réglages
    def set_system_info(self, info: Dict):
        self.system_info = info

    def open_model_settings(self):
        ref = self.current_ref()
        if not ref:
            QMessageBox.information(self, "Aucune IA", "Choisissez d'abord une IA.")
            return
        if ModelSettingsDialog(ref, self.system_info, self).exec():
            self.status.setText("✅ Réglages enregistrés : ils s'appliquent dès le prochain message.")

    # ------------------------------------------------------------ envoi / réception
    def send_message(self):
        if self.attachment_loading:
            self.status.setText("Attendez la fin du chargement ou annulez-le avant d’envoyer.")
            return
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
        if self.web_worker is not None and self.web_worker.isRunning():
            return
        had_text = bool(text)
        if not text:
            text = "Voici les fichiers joints."

        expanded, command = qc.expand(text)
        message = att.build_message(expanded, self.pending)
        if command:
            message["display"] = text
        self.messages.append(message)
        self.render_message(len(self.messages) - 1, ref)
        self.pending = []
        self.refresh_attach_bar()
        self.message_input.clear()
        self.web_ctx = ""
        self.web_sources = []
        self.memory_ctx = ""
        self.memory_sources = []
        memory_folder = str(self.pm.project_folder(self.project_id)) if self.project_id and self.memory_mode.isChecked() else ""
        if (self.web_mode.isChecked() and had_text) or memory_folder:
            self.status.setText("🌐 Recherche sur internet…")
            gen = self.web_gen
            use_web = self.web_mode.isChecked() and had_text
            def gather():
                result = {"context": "", "sources": []}
                if use_web:
                    try:
                        result.update(web_tools.research(expanded))
                    except Exception as error:
                        result["warning"] = str(error)
                if memory_folder:
                    try:
                        result["documents"] = project_memory.search(memory_folder, expanded)
                    except Exception as error:
                        result["memory_warning"] = str(error)
                return result
            self.web_worker = FunctionWorker(gather)
            self.web_worker.done.connect(lambda ok, res, r=ref, g=gen: self.on_web_research(ok, res, r, g))
            self.web_worker.start()
        else:
            self.start_stream(ref)

    def on_web_research(self, ok: bool, result, ref: str, gen: int):
        if gen != self.web_gen:
            return  # la discussion a été réinitialisée entre-temps
        if ok and isinstance(result, dict):
            self.web_ctx = result.get("context", "")
            self.memory_sources = result.get("documents", [])
            self.memory_ctx = project_memory.context(self.memory_sources)
            if result.get("warning"):
                self.system_message("⚠️ Recherche internet impossible : " + html.escape(result["warning"]))
            if result.get("memory_warning"):
                self.system_message("⚠️ Recherche documentaire impossible : " + html.escape(result["memory_warning"]))
            elif self.memory_mode.isChecked() and self.project_id and not self.memory_sources:
                self.system_message("📚 Aucun passage pertinent trouvé dans les documents indexés.")
            self.web_sources = result.get("sources", [])
        else:
            self.system_message(f"⚠️ Recherche internet impossible ({html.escape(str(result))}) "
                                "— réponse sans internet.")
        self.start_stream(ref)

    def start_stream(self, ref: str):
        self.stream_ref = ref
        self.stream_buffer = []
        self.send_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.status.setText("⏳ L'IA réfléchit…")
        who = providers.label_for(ref)[2:].strip()
        doc = self.chat_display.document()
        self.stream_pos = doc.characterCount() - 1
        self.append_html(f"<p style='margin-top:10px'><span style='color:{style.GREEN}; font-weight:600'>"
                         f"IA · {html.escape(who)}</span></p><p></p>")
        system = self.instructions()
        self.web_ctx = ""  # ne sert qu'au message en cours, déjà inclus dans "system"
        self.worker = StreamWorker(ref, self.messages, system)
        self.worker.token.connect(self.stream_buffer.append)
        self.worker.phase.connect(self.status.setText)
        self.worker.done.connect(self.on_stream_done)
        self.worker.start()
        self.flush_timer.start()

    def flush_stream(self):
        if not self.stream_buffer:
            return
        chunk = "".join(self.stream_buffer)
        self.stream_buffer.clear()
        bar = self.chat_display.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 30
        cursor = QTextCursor(self.chat_display.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        if at_bottom:
            bar.setValue(bar.maximum())
        if self.status.text().startswith("⏳"):
            self.status.setText("✍️ L'IA écrit… (⏹ Stop pour l'interrompre)")

    def stop_generation(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.status.setText("⏹ Arrêt demandé…")

    def remove_stream_area(self):
        cursor = QTextCursor(self.chat_display.document())
        cursor.setPosition(min(self.stream_pos, self.chat_display.document().characterCount() - 1))
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    def on_stream_done(self, text: str, stats: Dict):
        self.flush_timer.stop()
        self.stream_buffer.clear()
        self.remove_stream_area()
        self.send_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.on_answer(self.stream_ref, text, stats)

    def on_answer(self, ref: str, text: str, stats: Optional[Dict] = None):
        stats = stats or {}
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer ➤")
        self.status.setText("")
        if text.startswith(("Erreur", "Ollama n'est pas lancé")) or (not text and not stats.get("stopped")):
            # Pas une vraie réponse : on l'affiche sans la garder dans l'historique
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            self.system_message(f"❌ {html.escape(text or 'Réponse vide.')}")
            self.web_sources = []
            return
        if stats.get("stopped"):
            text = (text + "\n\n*(réponse interrompue)*") if text else "*(réponse interrompue)*"
        if self.memory_sources:
            text += "\n\n**Passages transmis à l’IA :**\n" + "\n".join(
                f"- [D{i}] {r['name']} — passage {r['passage']}" for i, r in enumerate(self.memory_sources, 1))
            self.memory_sources = []
        self.messages.append({"role": "assistant", "content": text})
        self.render_message(len(self.messages) - 1, ref)
        if self.web_sources:
            links = " · ".join(f"<a href='{html.escape(s['url'])}'>{html.escape(s['title'] or s['url'])}</a>"
                               for s in self.web_sources[:5])
            self.system_message(f"🌐 Sources : {links}")
            self.web_sources = []
        self.status.setText(self.stats_text(stats))
        try:
            self.save_current(ref)
        except Exception as e:
            self.system_message(f"⚠️ Sauvegarde impossible : {html.escape(str(e))}")

    @staticmethod
    def stats_text(stats: Dict) -> str:
        parts = []
        if stats.get("tokens_per_s"):
            parts.append(f"⚡ {stats['tokens_per_s']:.1f} tokens/s")
        if stats.get("tokens"):
            parts.append(f"{stats['tokens']} tokens")
        if stats.get("seconds"):
            parts.append(f"{stats['seconds']:.0f} s")
        opts = stats.get("options") or {}
        if "num_gpu" in opts:
            parts.append(f"{opts['num_gpu']} couches en VRAM")
        if opts.get("num_ctx"):
            parts.append(f"contexte {opts['num_ctx']}")
        return " · ".join(parts)
