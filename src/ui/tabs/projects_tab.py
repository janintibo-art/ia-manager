"""Onglet Projets - consignes, sauvegardes de discussions, classement"""

import html
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend import settings
from src.backend.ai_manager import AIManager
from src.backend import project_memory
from src.backend.project_manager import (
    INSTRUCTION_TEMPLATES, ProjectManager, filter_projects, search_conversations, sort_projects,
)

SORT_MODES = ["Modifié récemment", "Nom", "Catégorie", "Nombre de discussions"]
ALL_CATEGORIES = "Toutes les catégories"
ALL_TAGS = "Toutes les étiquettes"


def open_folder(path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def get_project_manager() -> ProjectManager:
    return ProjectManager(settings.get("projects_dir"))


class ProjectsTab(QWidget):
    """Gestion des projets"""

    open_conversation = pyqtSignal(str, str)   # projet, discussion
    new_conversation = pyqtSignal(str)         # projet
    projects_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.pm = get_project_manager()
        self.ai_manager = AIManager()
        self.current_pid: Optional[str] = None
        self.installed_models: List[str] = []
        self.init_ui()
        self.refresh_models()
        self.reload()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Projets")
        title.setObjectName("Title")
        subtitle = QLabel("Un projet regroupe des consignes pour l'IA, les discussions sauvegardées "
                          "et vos fichiers. Choisissez un projet dans le Chat pour l'activer.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        head.addLayout(titles, 1)
        root.addLayout(head)

        loc = QHBoxLayout()
        self.location_label = QLabel()
        self.location_label.setObjectName("Muted")
        self.location_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        loc.addWidget(self.location_label, 1)
        change_loc = QPushButton("📁 Changer l'emplacement")
        change_loc.clicked.connect(self.change_location)
        loc.addWidget(change_loc)
        open_loc = QPushButton("Ouvrir le dossier")
        open_loc.clicked.connect(lambda: open_folder(self.pm.root))
        loc.addWidget(open_loc)
        root.addLayout(loc)

        gs_row = QHBoxLayout()
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("🔎 Rechercher dans discussions et documents de tous les projets…")
        self.global_search.setClearButtonEnabled(True)
        self.global_search.returnPressed.connect(self.run_global_search)
        self.global_search.textChanged.connect(lambda t: self.run_global_search() if not t.strip() else None)
        gs_row.addWidget(self.global_search, 1)
        gs_btn = QPushButton("Rechercher")
        gs_btn.clicked.connect(self.run_global_search)
        gs_row.addWidget(gs_btn)
        root.addLayout(gs_row)
        self.global_results = QListWidget()
        self.global_results.setMaximumHeight(230)
        self.global_results.setVisible(False)
        self.global_results.itemDoubleClicked.connect(self.open_global_result)
        root.addWidget(self.global_results)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Colonne gauche : recherche, classement, liste
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Rechercher un projet…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self.populate_list())
        left_lay.addWidget(self.search)

        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(lambda _i: self.populate_list())
        left_lay.addWidget(self.category_filter)
        self.tag_filter = QComboBox()
        self.tag_filter.currentIndexChanged.connect(lambda _i: self.populate_list())
        left_lay.addWidget(self.tag_filter)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Trier :"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(SORT_MODES)
        self.sort_combo.currentIndexChanged.connect(lambda _i: self.populate_list())
        sort_row.addWidget(self.sort_combo, 1)
        left_lay.addLayout(sort_row)

        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self.on_project_changed)
        left_lay.addWidget(self.project_list, 1)

        btns = QHBoxLayout()
        new_btn = QPushButton("➕ Nouveau projet")
        new_btn.setObjectName("Primary")
        new_btn.clicked.connect(self.ask_new_project)
        btns.addWidget(new_btn, 1)
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("Danger")
        del_btn.setToolTip("Mettre le projet à la corbeille")
        del_btn.clicked.connect(self.delete_project)
        btns.addWidget(del_btn)
        left_lay.addLayout(btns)
        splitter.addWidget(left)

        # ---- Colonne droite : le projet
        right = QFrame()
        right.setObjectName("Card")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(18, 16, 18, 16)

        self.project_title = QLabel("Aucun projet")
        self.project_title.setObjectName("CardTitle")
        right_lay.addWidget(self.project_title)
        self.project_info = QLabel()
        self.project_info.setObjectName("Muted")
        self.project_info.setWordWrap(True)
        right_lay.addWidget(self.project_info)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setObjectName("SubTabs")
        self.inner_tabs.addTab(self.build_instructions_tab(), "📝 Consignes")
        self.inner_tabs.addTab(self.build_saves_tab(), "💾 Sauvegardes")
        self.inner_tabs.addTab(self.build_settings_tab(), "🏷️ Classement et réglages")
        right_lay.addWidget(self.inner_tabs, 1)
        self.right_panel = right
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([360, 900])
        root.addWidget(splitter, 1)

    def build_instructions_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        hint = QLabel("Ces consignes sont envoyées à l'IA au début de chaque discussion de ce projet : "
                      "rôle, ton, langue, règles à respecter…")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        tpl_row = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItem("Choisir un modèle de consignes…")
        self.template_combo.addItems(list(INSTRUCTION_TEMPLATES))
        tpl_row.addWidget(self.template_combo, 1)
        insert_btn = QPushButton("Insérer")
        insert_btn.clicked.connect(self.insert_template)
        tpl_row.addWidget(insert_btn)
        lay.addLayout(tpl_row)

        self.instructions = QTextEdit()
        self.instructions.setAcceptRichText(False)
        self.instructions.setPlaceholderText("Exemple : Tu es mon assistant pour le projet X. Réponds toujours "
                                             "en français, de façon concise…")
        lay.addWidget(self.instructions, 1)

        row = QHBoxLayout()
        self.instructions_status = QLabel()
        self.instructions_status.setObjectName("Muted")
        row.addWidget(self.instructions_status, 1)
        save_btn = QPushButton("💾 Enregistrer les consignes")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.save_instructions)
        row.addWidget(save_btn)
        lay.addLayout(row)
        return w

    def build_saves_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        hint = QLabel("Les discussions du Chat sont enregistrées ici automatiquement quand ce projet est actif.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.conv_list = QListWidget()
        self.conv_list.itemDoubleClicked.connect(lambda _i: self.open_selected_conversation())
        lay.addWidget(self.conv_list, 1)

        row1 = QHBoxLayout()
        open_btn = QPushButton("💬 Ouvrir dans le Chat")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(self.open_selected_conversation)
        row1.addWidget(open_btn)
        rename_btn = QPushButton("✏️ Renommer")
        rename_btn.clicked.connect(self.rename_conversation)
        row1.addWidget(rename_btn)
        export_btn = QPushButton("📄 Exporter en texte")
        export_btn.clicked.connect(self.export_conversation)
        row1.addWidget(export_btn)
        export_pdf_btn = QPushButton("📕 PDF")
        export_pdf_btn.clicked.connect(self.export_conversation_pdf)
        row1.addWidget(export_pdf_btn)
        export_docx_btn = QPushButton("📘 Word")
        export_docx_btn.clicked.connect(self.export_conversation_docx)
        row1.addWidget(export_docx_btn)
        del_btn = QPushButton("🗑 Supprimer")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self.delete_conversation)
        row1.addWidget(del_btn)
        row1.addStretch()
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        new_btn = QPushButton("➕ Nouvelle discussion dans ce projet")
        new_btn.clicked.connect(lambda: self.current_pid and self.new_conversation.emit(self.current_pid))
        row2.addWidget(new_btn)
        backup_btn = QPushButton("📦 Sauvegarde complète (.zip)")
        backup_btn.clicked.connect(self.export_project)
        row2.addWidget(backup_btn)
        files_btn = QPushButton("📂 Dossier fichiers")
        files_btn.setToolTip("Rangez ici vos documents pour ce projet")
        files_btn.clicked.connect(lambda: self.current_pid and open_folder(self.pm.files_folder(self.current_pid)))
        row2.addWidget(files_btn)
        row2.addStretch()
        lay.addLayout(row2)

        self.saves_status = QLabel()
        self.saves_status.setObjectName("Muted")
        self.saves_status.setWordWrap(True)
        lay.addWidget(self.saves_status)
        return w

    def build_settings_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(10)

        self.name_edit = QLineEdit()
        form.addRow("Nom :", self.name_edit)
        self.category_edit = QComboBox()
        self.category_edit.setEditable(True)
        form.addRow("Catégorie :", self.category_edit)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("séparées par des virgules : android, urgent, perso")
        form.addRow("Étiquettes :", self.tags_edit)
        self.favorite_check = QCheckBox("⭐ Favori (toujours en haut de la liste)")
        form.addRow("", self.favorite_check)
        self.model_combo = QComboBox()
        form.addRow("Modèle par défaut :", self.model_combo)

        gh_title = QLabel("GitHub (utilisé par l'onglet GitHub)")
        gh_title.setObjectName("Muted")
        form.addRow("", gh_title)
        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText("propriétaire/depot-github (tiret simple)")
        form.addRow("Dépôt GitHub :", self.repo_edit)
        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText("dossier_termux (tiret bas)")
        form.addRow("Dossier Termux :", self.local_edit)
        folder_row = QHBoxLayout()
        self.pc_folder_edit = QLineEdit()
        self.pc_folder_edit.setPlaceholderText("Dossier du dépôt sur ce PC")
        folder_row.addWidget(self.pc_folder_edit, 1)
        browse = QPushButton("Parcourir")
        browse.clicked.connect(self.browse_pc_folder)
        folder_row.addWidget(browse)
        form.addRow("Dossier PC :", folder_row)
        lay.addLayout(form)

        row = QHBoxLayout()
        self.settings_status = QLabel()
        self.settings_status.setObjectName("Muted")
        row.addWidget(self.settings_status, 1)
        save = QPushButton("💾 Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_settings)
        row.addWidget(save)
        lay.addLayout(row)
        lay.addStretch()
        return w

    # ------------------------------------------------------------ données
    def refresh_models(self):
        self.installed_models = self.ai_manager.get_available_models()
        if self.current_pid:
            self.fill_model_combo(self.pm.get(self.current_pid) or {})

    def fill_model_combo(self, meta: Dict):
        from src.backend import providers
        self.model_combo.clear()
        self.model_combo.addItem("(aucun, choisir dans le Chat)", "")
        wanted = meta.get("default_model", "")
        if wanted and providers.SEP not in wanted:
            wanted = providers.make_ref("ollama", wanted)
        choices = providers.all_model_choices(self.installed_models)
        if wanted and wanted not in [r for _l, r in choices]:
            choices.append((providers.label_for(wanted) + " (indisponible)", wanted))
        for label, ref in choices:
            self.model_combo.addItem(label, ref)
        idx = self.model_combo.findData(wanted)
        self.model_combo.setCurrentIndex(max(0, idx))

    def reload(self, select: Optional[str] = None):
        self.pm = get_project_manager()
        self.location_label.setText(f"📁 Emplacement : {self.pm.root}")
        keep = select or self.current_pid

        self.category_filter.blockSignals(True)
        current_cat = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem(ALL_CATEGORIES)
        self.category_filter.addItems(self.pm.categories())
        i = self.category_filter.findText(current_cat)
        self.category_filter.setCurrentIndex(max(0, i))
        self.category_filter.blockSignals(False)

        self.tag_filter.blockSignals(True)
        current_tag = self.tag_filter.currentText()
        self.tag_filter.clear()
        self.tag_filter.addItem(ALL_TAGS)
        self.tag_filter.addItems(self.pm.all_tags())
        i = self.tag_filter.findText(current_tag)
        self.tag_filter.setCurrentIndex(max(0, i))
        self.tag_filter.blockSignals(False)

        self.category_edit.blockSignals(True)
        self.category_edit.clear()
        self.category_edit.addItems(self.pm.categories())
        self.category_edit.blockSignals(False)

        self.current_pid = keep
        self.populate_list()

    def populate_list(self):
        projects = self.pm.list_projects()
        cat = self.category_filter.currentText()
        tag = self.tag_filter.currentText()
        projects = filter_projects(
            projects, self.search.text(),
            "" if cat in ("", ALL_CATEGORIES) else cat,
            "" if tag in ("", ALL_TAGS) else tag,
        )
        projects = sort_projects(projects, self.sort_combo.currentText())

        keep = self.current_pid
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for p in projects:
            star = "⭐ " if p["favorite"] else ""
            tags = ("  #" + " #".join(p["tags"])) if p["tags"] else ""
            text = (f"{star}{p['name']}\n"
                    f"      {p['category']} · {p['conversation_count']} discussion(s){tags}")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.project_list.addItem(item)
        self.project_list.blockSignals(False)

        if not projects:
            self.current_pid = None
            self.show_project(None)
            return
        row = 0
        for i in range(self.project_list.count()):
            if self.project_list.item(i).data(Qt.ItemDataRole.UserRole) == keep:
                row = i
                break
        self.project_list.setCurrentRow(row)
        self.on_project_changed(self.project_list.currentItem(), None)

    def on_project_changed(self, current, _previous):
        if current is None:
            return
        self.current_pid = current.data(Qt.ItemDataRole.UserRole)
        self.show_project(self.current_pid)

    def show_project(self, pid: Optional[str]):
        meta = self.pm.get(pid) if pid else None
        self.inner_tabs.setEnabled(meta is not None)
        if meta is None:
            self.project_title.setText("Aucun projet")
            self.project_info.setText("Créez votre premier projet avec « ➕ Nouveau projet ».")
            self.instructions.clear()
            self.conv_list.clear()
            return

        star = "⭐ " if meta["favorite"] else ""
        self.project_title.setText(f"{star}{meta['name']}")
        tags = " · #" + " #".join(meta["tags"]) if meta["tags"] else ""
        self.project_info.setText(f"{meta['category']}{tags} · dossier : {self.pm.project_folder(pid)}")

        self.instructions.setPlainText(self.pm.get_instructions(pid))
        self.instructions_status.setText("")

        self.name_edit.setText(meta["name"])
        self.category_edit.setCurrentText(meta["category"])
        self.tags_edit.setText(", ".join(meta["tags"]))
        self.favorite_check.setChecked(bool(meta["favorite"]))
        self.repo_edit.setText(meta["github_repo"])
        self.local_edit.setText(meta["local_name"])
        self.pc_folder_edit.setText(meta["pc_folder"])
        self.fill_model_combo(meta)
        self.settings_status.setText("")

        self.refresh_conversations()

    def refresh_conversations(self):
        self.conv_list.clear()
        if not self.current_pid:
            return
        convs = self.pm.list_conversations(self.current_pid)
        for c in convs:
            date = c["updated"].replace("T", " ")[:16]
            item = QListWidgetItem(f"💬 {c['title']}\n      {c['model']} · {date} · {c['count']} messages")
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.conv_list.addItem(item)
        if not convs:
            self.conv_list.addItem("Aucune discussion sauvegardée pour l'instant.")
        self.saves_status.setText("")

    def on_conversation_saved(self, pid: str):
        """Appelé par le Chat après chaque réponse"""
        if pid == self.current_pid:
            self.refresh_conversations()
        self.populate_list()

    # ------------------------------------------------------------ actions
    def change_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Emplacement des projets", str(self.pm.root))
        if folder:
            settings.set("projects_dir", folder)
            self.current_pid = None
            self.reload()
            self.projects_changed.emit()

    def ask_new_project(self):
        name, ok = QInputDialog.getText(self, "Nouveau projet", "Nom du projet :")
        if ok and name.strip():
            self.create_project(name.strip())

    def create_project(self, name: str, category: str = "Général") -> str:
        pid = self.pm.create_project(name, category)
        self.search.clear()
        self.category_filter.setCurrentIndex(0)
        self.tag_filter.setCurrentIndex(0)
        self.reload(select=pid)
        self.inner_tabs.setCurrentIndex(0)
        self.projects_changed.emit()
        return pid

    def delete_project(self):
        if not self.current_pid:
            return
        meta = self.pm.get(self.current_pid) or {}
        reply = QMessageBox.question(
            self, "Supprimer le projet",
            f"Mettre « {meta.get('name', self.current_pid)} » à la corbeille ?\n\n"
            "Il sera déplacé dans le dossier .corbeille de l'emplacement des projets "
            "(récupérable à la main).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.pm.delete_project(self.current_pid)
            self.current_pid = None
            self.reload()
            self.projects_changed.emit()

    def insert_template(self):
        name = self.template_combo.currentText()
        if name in INSTRUCTION_TEMPLATES:
            current = self.instructions.toPlainText().strip()
            text = INSTRUCTION_TEMPLATES[name]
            self.instructions.setPlainText(f"{current}\n\n{text}" if current else text)
            self.instructions_status.setText("Modèle inséré — pensez à enregistrer.")

    def save_instructions(self):
        if not self.current_pid:
            return
        self.pm.set_instructions(self.current_pid, self.instructions.toPlainText())
        self.instructions_status.setText("✅ Consignes enregistrées.")
        self.projects_changed.emit()

    def browse_pc_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier du dépôt sur ce PC",
                                                  self.pc_folder_edit.text() or str(self.pm.root))
        if folder:
            self.pc_folder_edit.setText(folder)

    def save_settings(self):
        if not self.current_pid:
            return
        tags = [t.strip().lstrip("#") for t in self.tags_edit.text().split(",") if t.strip()]
        self.pm.save_meta(self.current_pid, {
            "name": self.name_edit.text().strip() or self.current_pid,
            "category": self.category_edit.currentText().strip() or "Général",
            "tags": tags,
            "favorite": self.favorite_check.isChecked(),
            "default_model": self.model_combo.currentData() or "",
            "github_repo": self.repo_edit.text().strip(),
            "local_name": self.local_edit.text().strip(),
            "pc_folder": self.pc_folder_edit.text().strip(),
        })
        self.reload(select=self.current_pid)
        self.settings_status.setText("✅ Enregistré.")
        self.inner_tabs.setCurrentIndex(2)
        self.projects_changed.emit()

    def selected_conversation(self) -> Optional[str]:
        item = self.conv_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def open_selected_conversation(self):
        cid = self.selected_conversation()
        if self.current_pid and cid:
            self.open_conversation.emit(self.current_pid, cid)

    def rename_conversation(self):
        cid = self.selected_conversation()
        if not (self.current_pid and cid):
            return
        data = self.pm.load_conversation(self.current_pid, cid)
        title, ok = QInputDialog.getText(self, "Renommer", "Nouveau titre :", text=data.get("title", ""))
        if ok and title.strip():
            self.pm.rename_conversation(self.current_pid, cid, title.strip())
            self.refresh_conversations()

    def export_conversation(self):
        cid = self.selected_conversation()
        if not (self.current_pid and cid):
            return
        out = self.pm.export_conversation_markdown(self.current_pid, cid)
        self.saves_status.setText(f"✅ Exporté : {out}")

    def export_conversation_pdf(self):
        cid = self.selected_conversation()
        if not (self.current_pid and cid):
            return
        try:
            out = self.pm.export_conversation_pdf(self.current_pid, cid)
            self.saves_status.setText(f"✅ PDF créé : {html.escape(str(out))}")
        except Exception as e:
            self.saves_status.setText(f"❌ Export PDF impossible : {html.escape(str(e))}")

    def export_conversation_docx(self):
        cid = self.selected_conversation()
        if not (self.current_pid and cid):
            return
        try:
            out = self.pm.export_conversation_docx(self.current_pid, cid)
            self.saves_status.setText(f"✅ Word créé : {html.escape(str(out))}")
        except Exception as e:
            self.saves_status.setText(f"❌ Export Word impossible : {html.escape(str(e))}")

    def delete_conversation(self):
        cid = self.selected_conversation()
        if not (self.current_pid and cid):
            return
        reply = QMessageBox.question(self, "Supprimer", "Supprimer cette discussion ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.pm.delete_conversation(self.current_pid, cid)
            self.refresh_conversations()
            self.populate_list()

    def export_project(self):
        if not self.current_pid:
            return
        folder = QFileDialog.getExistingDirectory(self, "Où enregistrer la sauvegarde ?", str(self.pm.root))
        if folder:
            out = self.pm.export_project(self.current_pid, folder)
            self.saves_status.setText(f"✅ Sauvegarde créée : {html.escape(str(out))}")

    # ------------------------------------------------------------ recherche globale
    def run_global_search(self):
        query = self.global_search.text().strip()
        self.global_results.clear()
        if len(query) < 2:
            self.global_results.setVisible(False)
            return
        results = search_conversations(str(self.pm.root), query)
        for row in project_memory.search_all(str(self.pm.root), query):
            results.append({"project": row["project"], "project_name": row["project"],
                            "id": "", "title": "📚 " + row["name"],
                            "snippet": row["text"], "hits": row["score"],
                            "updated": "", "document": True})
        results.sort(key=lambda r: (r["hits"], r.get("updated", "")), reverse=True)
        if not results:
            self.global_results.addItem(f"Aucune discussion ne contient « {query} ».")
        for r in results:
            date = r["updated"].replace("T", " ")[:16]
            icon = "📚" if r.get("document") else "💬"
            item = QListWidgetItem(f"{icon} {r['title']}   ·   📁 {r['project_name']}   ·   {date}   ·   "
                                   f"{r['hits']} occurrence(s)\n      {r['snippet'][:160]}")
            item.setData(Qt.ItemDataRole.UserRole, (r["project"], r["id"], bool(r.get("document"))))
            item.setToolTip("Document indexé" if r.get("document") else "Double-clic pour rouvrir cette discussion dans le Chat")
            self.global_results.addItem(item)
        self.global_results.setVisible(True)

    def open_global_result(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            pid, cid, is_document = (*data, False) if len(data) == 2 else data
            if is_document:
                self.status.setText("Ouvrez l’Espace de travail pour consulter et interroger ce document.")
                return
            self.open_conversation.emit(pid, cid)
