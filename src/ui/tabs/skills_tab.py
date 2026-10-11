"""Onglet Skills - bibliothèque de skills (consignes prêtes à l'emploi) et de plugins (lots de skills)"""

from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import skills as sk

ALL = "__all__"
ACTIVE_ONLY = "__active__"


class SkillsTab(QWidget):
    """Parcourir, activer, créer et importer des skills"""

    skills_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current: Optional[Dict] = None      # skill affichée dans l'éditeur
        self.editable = False
        self.shown: List[Dict] = []
        self.init_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(8)

        title = QLabel("Skills et plugins")
        title.setObjectName("Title")
        root.addWidget(title)
        intro = QLabel("Une <b>skill</b> est une consigne prête à l'emploi (relire du code, résumer, "
                       "préparer un voyage…). Cochez celles que vous voulez : elles sont ajoutées aux "
                       "instructions de l'IA dans le Chat. Un <b>plugin</b> est un lot de skills qu'on "
                       "installe ou retire d'un clic. Les petits modèles s'en sortent mieux avec peu de "
                       "skills actives.")
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        bar = QHBoxLayout()
        self.plugin_combo = QComboBox()
        self.plugin_combo.setMinimumWidth(300)
        self.plugin_combo.currentIndexChanged.connect(self.fill_table)
        bar.addWidget(self.plugin_combo)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Chercher une skill…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.fill_table)
        bar.addWidget(self.search, 1)
        self.plugin_btn = QPushButton("➕ Installer le plugin")
        self.plugin_btn.setObjectName("Primary")
        self.plugin_btn.clicked.connect(self.toggle_plugin)
        bar.addWidget(self.plugin_btn)
        root.addLayout(bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Active", "Skill", "Plugin", "Description"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_selection)
        root.addWidget(self.table, 3)

        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        form = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom de la skill")
        form.addWidget(self.name_edit, 1)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Courte description")
        form.addWidget(self.desc_edit, 2)
        root.addLayout(form)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("La consigne donnée à l'IA quand la skill est active…")
        root.addWidget(self.prompt_edit, 2)

        btns = QHBoxLayout()
        new_btn = QPushButton("➕ Nouvelle skill")
        new_btn.clicked.connect(self.new_skill)
        btns.addWidget(new_btn)
        self.save_btn = QPushButton("💾 Enregistrer")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(self.save_skill)
        btns.addWidget(self.save_btn)
        self.copy_btn = QPushButton("📋 Copier dans mes skills")
        self.copy_btn.setToolTip("Crée votre propre version, modifiable, de la skill sélectionnée")
        self.copy_btn.clicked.connect(self.copy_to_mine)
        btns.addWidget(self.copy_btn)
        import_btn = QPushButton("📥 Importer…")
        import_btn.setToolTip("Fichiers .md ou .txt (format SKILL.md accepté) ou archive .zip")
        import_btn.clicked.connect(self.import_dialog)
        btns.addWidget(import_btn)
        self.export_btn = QPushButton("📤 Exporter")
        self.export_btn.clicked.connect(self.export_skill)
        btns.addWidget(self.export_btn)
        self.delete_btn = QPushButton("🗑 Supprimer")
        self.delete_btn.setObjectName("Danger")
        self.delete_btn.clicked.connect(self.delete_skill)
        btns.addWidget(self.delete_btn)
        btns.addStretch()
        root.addLayout(btns)

        self.status = QLabel()
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.set_editor(None)

    # ------------------------------------------------------------------ liste
    def refresh(self):
        """Recharge plugins et skills (à appeler après un changement extérieur)"""
        keep = self.plugin_combo.currentData() or ALL
        self.plugin_combo.blockSignals(True)
        self.plugin_combo.clear()
        self.plugin_combo.addItem("Toutes les skills", ALL)
        self.plugin_combo.addItem("✅ Skills actives", ACTIVE_ONLY)
        for p in sk.plugins():
            self.plugin_combo.addItem(f"{p['icon']} {p['name']}  ({p['active']}/{p['count']})", p["id"])
        idx = self.plugin_combo.findData(keep)
        self.plugin_combo.setCurrentIndex(max(idx, 0))
        self.plugin_combo.blockSignals(False)
        self.fill_table()

    def fill_table(self, *_):
        choice = self.plugin_combo.currentData() or ALL
        skills = sk.all_skills()
        enabled = sk.enabled_ids()
        if choice == ACTIVE_ONLY:
            skills = [s for s in skills if s["id"] in enabled]
        elif choice != ALL:
            skills = [s for s in skills if s["plugin"] == choice]
        skills = sk.search(skills, self.search.text())
        names = {p["id"]: f"{p['icon']} {p['name']}" for p in sk.plugins()}
        self.shown = skills
        self.table.blockSignals(True)
        self.table.setRowCount(len(skills))
        for row, s in enumerate(skills):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                           | Qt.ItemFlag.ItemIsSelectable)
            check.setCheckState(Qt.CheckState.Checked if s["id"] in enabled else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)
            name = QTableWidgetItem(s["name"])
            name.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.table.setItem(row, 1, name)
            self.table.setItem(row, 2, QTableWidgetItem(names.get(s["plugin"], s["plugin"])))
            self.table.setItem(row, 3, QTableWidgetItem(s["desc"]))
        self.table.blockSignals(False)
        plugin_choice = choice not in (ALL, ACTIVE_ONLY)
        self.plugin_btn.setEnabled(plugin_choice)
        if plugin_choice:
            p = next((x for x in sk.plugins() if x["id"] == choice), None)
            all_on = bool(p) and p["count"] > 0 and p["active"] == p["count"]
            self.plugin_btn.setText("➖ Retirer le plugin" if all_on else "➕ Installer le plugin")
        else:
            self.plugin_btn.setText("➕ Installer le plugin")
        self.update_summary()

    def update_summary(self):
        n, chars = sk.active_summary()
        if not n:
            self.summary.setText("Aucune skill active : l'IA répond avec ses seules instructions habituelles.")
        else:
            self.summary.setText(f"✅ {n} skill(s) active(s) — environ {chars} caractères ajoutés à chaque "
                                 f"message du Chat (limite : {sk.MAX_ACTIVE_CHARS}).")

    def on_item_changed(self, item: QTableWidgetItem):
        if item.column() != 0:
            return
        id_item = self.table.item(item.row(), 1)
        if id_item is None:
            return
        sk.set_enabled(id_item.data(Qt.ItemDataRole.UserRole),
                       item.checkState() == Qt.CheckState.Checked)
        self.changed()

    def changed(self):
        """Une activation a changé : met à jour les compteurs et prévient le Chat"""
        self.update_summary()
        keep = self.plugin_combo.currentData()
        self.plugin_combo.blockSignals(True)
        for i in range(self.plugin_combo.count()):
            pid = self.plugin_combo.itemData(i)
            p = next((x for x in sk.plugins() if x["id"] == pid), None)
            if p:
                self.plugin_combo.setItemText(i, f"{p['icon']} {p['name']}  ({p['active']}/{p['count']})")
        self.plugin_combo.setCurrentIndex(max(self.plugin_combo.findData(keep), 0))
        self.plugin_combo.blockSignals(False)
        self.skills_changed.emit()

    def toggle_plugin(self):
        pid = self.plugin_combo.currentData()
        p = next((x for x in sk.plugins() if x["id"] == pid), None)
        if not p or not p["count"]:
            return
        install = p["active"] < p["count"]
        n = sk.set_plugin_enabled(pid, install)
        self.fill_table()
        self.changed()
        verb = "installé" if install else "retiré"
        self.status.setText(f"✅ Plugin « {p['name']} » {verb} ({n} skill(s)).")

    # ------------------------------------------------------------------ éditeur
    def selected_skill(self) -> Optional[Dict]:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 1)
        return sk.get_skill(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def on_selection(self):
        s = self.selected_skill()
        if s:
            self.set_editor(s)

    def set_editor(self, skill: Optional[Dict], new: bool = False):
        self.current = skill
        self.editable = new or bool(skill and not skill["builtin"])
        self.name_edit.setText(skill["name"] if skill else "")
        self.desc_edit.setText(skill["desc"] if skill else "")
        self.prompt_edit.setPlainText(skill["prompt"] if skill else "")
        for w in (self.name_edit, self.desc_edit):
            w.setReadOnly(not self.editable)
        self.prompt_edit.setReadOnly(not self.editable)
        self.save_btn.setEnabled(self.editable)
        self.copy_btn.setEnabled(bool(skill and skill["builtin"]))
        self.export_btn.setEnabled(bool(skill))
        self.delete_btn.setEnabled(bool(skill and not skill["builtin"]))

    def new_skill(self):
        self.table.clearSelection()
        self.set_editor(None, new=True)
        self.name_edit.setFocus()

    def save_skill(self):
        if not self.editable:
            return
        sid = self.current["id"] if self.current and not self.current["builtin"] else ""
        try:
            saved = sk.save_user_skill(self.name_edit.text(), self.desc_edit.text(),
                                       self.prompt_edit.toPlainText(), sid)
        except ValueError as e:
            self.status.setText(f"⚠️ {e}")
            return
        self.show_saved(saved, "enregistrée")

    def copy_to_mine(self):
        if not (self.current and self.current["builtin"]):
            return
        saved = sk.save_user_skill(self.current["name"] + " (copie)", self.current["desc"],
                                   self.current["prompt"])
        self.show_saved(saved, "copiée dans Mes skills")

    def show_saved(self, saved: Dict, verb: str):
        self.refresh()
        self.status.setText(f"✅ Skill « {saved['name']} » {verb}. Cochez-la pour l'utiliser.")
        self.skills_changed.emit()
        for row, s in enumerate(self.shown):
            if s["id"] == saved["id"]:
                self.table.selectRow(row)
                return
        self.set_editor(saved)

    def delete_skill(self):
        s = self.current
        if not s or s["builtin"]:
            return
        if QMessageBox.question(self, "Supprimer", f"Supprimer la skill « {s['name']} » ?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        sk.delete_user_skill(s["id"])
        self.set_editor(None)
        self.refresh()
        self.status.setText("🗑 Skill supprimée.")
        self.skills_changed.emit()

    # ------------------------------------------------------------------ import / export
    def import_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Importer des skills", str(Path.home()),
                                                "Skills (*.md *.txt *.zip);;Tous les fichiers (*)")
        if files:
            self.import_paths(files)

    def import_paths(self, paths: List[str]):
        done, errors = sk.import_files(paths)
        self.refresh()
        text = f"✅ {done} skill(s) importée(s) dans « Mes skills »." if done else "Aucune skill importée."
        if errors:
            text += " ⚠️ " + " · ".join(errors[:4])
        self.status.setText(text)
        if done:
            self.skills_changed.emit()

    def export_skill(self):
        s = self.current
        if not s:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter la skill",
                                              str(Path.home() / f"{sk.slugify(s['name'])}.md"),
                                              "Markdown (*.md)")
        if path:
            Path(path).write_text(sk.export_skill_text(s), encoding="utf-8")
            self.status.setText(f"📤 Exportée : {path}")
