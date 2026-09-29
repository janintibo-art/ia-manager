"""Extension v129 : gestionnaire de versions Obliteratus."""
from datetime import datetime
import json
from pathlib import Path
from types import MethodType
import uuid

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
)

from src.backend import obliteratus_export as oe


def _registry_path() -> Path:
    path = Path.home() / ".ia_manager" / "obliteratus_versions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_versions():
    path = _registry_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError, TypeError):
        return []


def _save_versions(items):
    path = _registry_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _find_export(checkpoint, name):
    checkpoint = str(Path(checkpoint).resolve()) if checkpoint else ""
    if not checkpoint or not name:
        return ""
    try:
        for model in oe.model_library():
            if str(Path(model.get("path", "")).resolve()) != checkpoint:
                continue
            for export in model.get("exports", []):
                if export.get("name") == name:
                    return str(export.get("path") or "")
    except Exception:
        pass
    return ""


def _new_version(tab, name=None):
    checkpoint = str(tab.checkpoints.currentData() or "")
    return {
        "id": uuid.uuid4().hex,
        "created": datetime.now().isoformat(timespec="seconds"),
        "source_model": getattr(tab, "v126_selected_ollama", "") or "",
        "source_checkpoint": checkpoint,
        "method": getattr(tab, "v126_method", None).currentData() if hasattr(tab, "v126_method") else "",
        "ollama_name": name or tab.export_name.text().strip(),
        "gguf_path": _find_export(checkpoint, name or tab.export_name.text().strip()),
        "note": "",
        "favorite": False,
    }


def install_v129(window):
    tab = getattr(window, "obliteratus_tab", None)
    if tab is None or getattr(window, "_v129_obliteratus", False):
        return

    tab.v129_versions = []
    tab.v129_selected_id = ""

    group = QGroupBox("7 · Versions Obliteratus")
    layout = QVBoxLayout(group)

    hint = QLabel(
        "Gardez plusieurs variantes d’un même modèle sans les confondre. "
        "Chaque version conserve sa source, sa méthode, son nom Ollama, son checkpoint, "
        "son GGUF et vos notes."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    tab.v129_table = QTableWidget(0, 6)
    tab.v129_table.setHorizontalHeaderLabels(
        ["★", "Date", "Source", "Méthode", "Nom Ollama", "Note"]
    )
    tab.v129_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tab.v129_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tab.v129_table.verticalHeader().hide()
    tab.v129_table.horizontalHeader().setStretchLastSection(True)
    tab.v129_table.setMinimumHeight(220)
    layout.addWidget(tab.v129_table)

    edit_row = QHBoxLayout()
    tab.v129_name = QLineEdit()
    tab.v129_name.setPlaceholderText("Nom Ollama de la version")
    edit_row.addWidget(QLabel("Nom"))
    edit_row.addWidget(tab.v129_name, 1)
    tab.v129_favorite = QPushButton("☆ Favori")
    edit_row.addWidget(tab.v129_favorite)
    layout.addLayout(edit_row)

    tab.v129_note = QTextEdit()
    tab.v129_note.setPlaceholderText(
        "Notes : réglages utilisés, résultat, qualité, cas d’usage, problèmes observés…"
    )
    tab.v129_note.setFixedHeight(80)
    layout.addWidget(tab.v129_note)

    actions = QHBoxLayout()
    tab.v129_add = QPushButton("＋ Enregistrer la version actuelle")
    actions.addWidget(tab.v129_add)
    tab.v129_save = QPushButton("💾 Enregistrer les modifications")
    actions.addWidget(tab.v129_save)
    tab.v129_compare = QPushButton("⚖️ Envoyer au comparatif")
    actions.addWidget(tab.v129_compare)
    tab.v129_chat = QPushButton("💬 Ouvrir dans Chat")
    actions.addWidget(tab.v129_chat)
    tab.v129_open = QPushButton("📁 Ouvrir les fichiers")
    actions.addWidget(tab.v129_open)
    tab.v129_delete = QPushButton("🗑 Supprimer de la liste")
    tab.v129_delete.setObjectName("Danger")
    actions.addWidget(tab.v129_delete)
    actions.addStretch()
    layout.addLayout(actions)

    tab.v129_status = QLabel("Aucune version sélectionnée.")
    tab.v129_status.setWordWrap(True)
    layout.addWidget(tab.v129_status)

    tab.layout().addWidget(group)

    def v129_reload(self):
        self.v129_versions = _load_versions()
        self.v129_versions.sort(
            key=lambda x: (not bool(x.get("favorite")), str(x.get("created", ""))),
            reverse=False,
        )
        self.v129_table.setRowCount(0)
        for item in self.v129_versions:
            row = self.v129_table.rowCount()
            self.v129_table.insertRow(row)
            values = (
                "★" if item.get("favorite") else "☆",
                str(item.get("created", "")).replace("T", " "),
                item.get("source_model") or Path(item.get("source_checkpoint") or "").parent.name or "—",
                item.get("method") or "—",
                item.get("ollama_name") or "—",
                item.get("note") or "",
            )
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, item.get("id"))
                self.v129_table.setItem(row, col, cell)
        self.v129_table.resizeColumnsToContents()
        self.v129_table.horizontalHeader().setStretchLastSection(True)
        self.v129_update_buttons()

    def v129_selected(self):
        row = self.v129_table.currentRow()
        if row < 0 or not self.v129_table.item(row, 0):
            self.v129_selected_id = ""
            self.v129_status.setText("Aucune version sélectionnée.")
            self.v129_update_buttons()
            return
        item_id = self.v129_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        item = next((x for x in self.v129_versions if x.get("id") == item_id), None)
        if not item:
            return
        self.v129_selected_id = item_id
        self.v129_name.setText(str(item.get("ollama_name") or ""))
        self.v129_note.setPlainText(str(item.get("note") or ""))
        self.v129_favorite.setText("★ Favori" if item.get("favorite") else "☆ Favori")
        gguf = item.get("gguf_path") or ""
        self.v129_status.setText(
            f"Version sélectionnée · méthode {item.get('method') or 'inconnue'}"
            + (f" · GGUF : {gguf}" if gguf else "")
        )
        self.v129_update_buttons()

    def v129_current_item(self):
        return next(
            (x for x in self.v129_versions if x.get("id") == self.v129_selected_id),
            None,
        )

    def v129_update_buttons(self):
        item = self.v129_current_item()
        has_item = item is not None
        self.v129_save.setEnabled(has_item)
        self.v129_compare.setEnabled(has_item and bool(item.get("ollama_name")))
        self.v129_chat.setEnabled(has_item and bool(item.get("ollama_name")))
        self.v129_open.setEnabled(
            has_item and bool(item.get("gguf_path") or item.get("source_checkpoint"))
        )
        self.v129_delete.setEnabled(has_item)
        self.v129_favorite.setEnabled(has_item)

    def v129_add_current(self):
        name = self.export_name.text().strip()
        if not name:
            self.v129_status.setText("Donnez d'abord un nom à la version.")
            return
        item = _new_version(self, name)
        versions = _load_versions()

        # Évite les doublons exacts après un export automatiquement enregistré.
        for old in versions:
            if (
                old.get("ollama_name") == item.get("ollama_name")
                and old.get("source_checkpoint") == item.get("source_checkpoint")
            ):
                self.v129_status.setText("Cette version est déjà enregistrée.")
                return

        versions.append(item)
        _save_versions(versions)
        self.v129_reload()
        self.v129_status.setText(f"✅ Version « {name} » enregistrée.")

    def v129_save_selected(self):
        item = self.v129_current_item()
        if not item:
            return
        item["ollama_name"] = self.v129_name.text().strip()
        item["note"] = self.v129_note.toPlainText().strip()
        if not item.get("gguf_path"):
            item["gguf_path"] = _find_export(
                item.get("source_checkpoint"), item.get("ollama_name")
            )
        _save_versions(self.v129_versions)
        self.v129_reload()
        self.v129_status.setText("✅ Modifications enregistrées.")

    def v129_toggle_favorite(self):
        item = self.v129_current_item()
        if not item:
            return
        item["favorite"] = not bool(item.get("favorite"))
        _save_versions(self.v129_versions)
        self.v129_reload()
        self.v129_status.setText("Favori mis à jour.")

    def v129_send_compare(self):
        item = self.v129_current_item()
        if not item or not hasattr(self, "v128_modified"):
            return
        self.v128_refresh_models()
        idx = self.v128_modified.findText(str(item.get("ollama_name") or ""))
        if idx >= 0:
            self.v128_modified.setCurrentIndex(idx)
        source = str(item.get("source_model") or "")
        if source:
            idx = self.v128_original.findText(source)
            if idx >= 0:
                self.v128_original.setCurrentIndex(idx)
        self.v129_status.setText("Version envoyée au comparatif Avant / Après.")

    def v129_open_chat(self):
        item = self.v129_current_item()
        if item and item.get("ollama_name"):
            self.open_model_chat.emit(str(item["ollama_name"]))

    def v129_open_files(self):
        item = self.v129_current_item()
        if not item:
            return
        candidates = []
        gguf = str(item.get("gguf_path") or "")
        checkpoint = str(item.get("source_checkpoint") or "")
        if gguf:
            candidates.append(Path(gguf).parent)
        if checkpoint:
            candidates.append(Path(checkpoint))
        for path in candidates:
            if path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                return
        self.v129_status.setText("Les fichiers de cette version ne sont plus disponibles.")

    def v129_delete_selected(self):
        item = self.v129_current_item()
        if not item:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer de la liste",
            "Retirer cette version du gestionnaire ? Les fichiers et le modèle Ollama ne seront pas supprimés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.v129_versions = [
            x for x in self.v129_versions if x.get("id") != item.get("id")
        ]
        _save_versions(self.v129_versions)
        self.v129_selected_id = ""
        self.v129_reload()
        self.v129_status.setText("Version retirée de la liste.")

    def v129_auto_register_export(self, name):
        name = (name or "").strip()
        checkpoint = str(self.checkpoints.currentData() or "")
        if not name or not checkpoint:
            return
        versions = _load_versions()
        found = next(
            (
                x for x in versions
                if x.get("ollama_name") == name
                and x.get("source_checkpoint") == checkpoint
            ),
            None,
        )
        if found:
            found["gguf_path"] = _find_export(checkpoint, name) or found.get("gguf_path", "")
            found["method"] = (
                self.v126_method.currentData()
                if hasattr(self, "v126_method") else found.get("method", "")
            )
        else:
            versions.append(_new_version(self, name))
        _save_versions(versions)
        self.v129_reload()
        self.v129_status.setText(f"✅ Version « {name} » ajoutée automatiquement.")

    tab.v129_reload = MethodType(v129_reload, tab)
    tab.v129_selected = MethodType(v129_selected, tab)
    tab.v129_current_item = MethodType(v129_current_item, tab)
    tab.v129_update_buttons = MethodType(v129_update_buttons, tab)
    tab.v129_add_current = MethodType(v129_add_current, tab)
    tab.v129_save_selected = MethodType(v129_save_selected, tab)
    tab.v129_toggle_favorite = MethodType(v129_toggle_favorite, tab)
    tab.v129_send_compare = MethodType(v129_send_compare, tab)
    tab.v129_open_chat = MethodType(v129_open_chat, tab)
    tab.v129_open_files = MethodType(v129_open_files, tab)
    tab.v129_delete_selected = MethodType(v129_delete_selected, tab)
    tab.v129_auto_register_export = MethodType(v129_auto_register_export, tab)

    tab.v129_table.itemSelectionChanged.connect(tab.v129_selected)
    tab.v129_add.clicked.connect(tab.v129_add_current)
    tab.v129_save.clicked.connect(tab.v129_save_selected)
    tab.v129_favorite.clicked.connect(tab.v129_toggle_favorite)
    tab.v129_compare.clicked.connect(tab.v129_send_compare)
    tab.v129_chat.clicked.connect(tab.v129_open_chat)
    tab.v129_open.clicked.connect(tab.v129_open_files)
    tab.v129_delete.clicked.connect(tab.v129_delete_selected)

    # Hook après les wrappers v128 : l'export réussi renseigne chat_ready_name.
    old_finished = tab.finished

    def finished(self, code, exit_status):
        old_finished(code, exit_status)
        try:
            if code == 0 and getattr(self, "chat_ready_name", ""):
                self.v129_auto_register_export(self.chat_ready_name)
        except Exception:
            pass

    tab.finished = MethodType(finished, tab)

    tab.v129_reload()
    window._v129_obliteratus = True
