"""Fenêtres de réglage : réglages d'un modèle (VRAM/RAM, contexte, température) et commandes rapides"""

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)

from src.backend import model_options as mo
from src.backend import providers
from src.backend import quick_commands as qc


class ModelSettingsDialog(QDialog):
    """Réglages d'un modèle local : répartition VRAM/RAM réellement appliquée"""

    def __init__(self, ref: str, system_info: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.ref = ref
        self.system_info = system_info
        pid, self.model = providers.split_ref(ref)
        self.is_local = pid == "ollama"
        self.setWindowTitle(f"Réglages — {self.model}")
        self.setMinimumWidth(640)
        self.meta = mo.fetch_meta(self.model, timeout=3) if self.is_local else {}

        lay = QVBoxLayout(self)
        title = QLabel(f"⚙️ {providers.label_for(ref)}")
        title.setObjectName("CardTitle")
        lay.addWidget(title)

        if not self.is_local:
            note = QLabel("Les IA en ligne (Claude, GPT, serveurs distants) gèrent elles-mêmes leur mémoire : "
                          "il n'y a rien à régler ici.")
            note.setWordWrap(True)
            lay.addWidget(note)
            close = QPushButton("Fermer")
            close.clicked.connect(self.reject)
            lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
            return

        opts = mo.get_options(ref)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.mode = QComboBox()
        for key, label in mo.MODES.items():
            self.mode.addItem(label, key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(opts["mode"])))
        form.addRow("Priorité :", self.mode)
        self.mode_help = QLabel()
        self.mode_help.setObjectName("Muted")
        self.mode_help.setWordWrap(True)
        form.addRow("", self.mode_help)

        self.ctx = QSpinBox()
        self.ctx.setRange(0, 262144)
        self.ctx.setSingleStep(2048)
        self.ctx.setSpecialValueText("selon la priorité")
        self.ctx.setValue(int(opts.get("num_ctx") or 0))
        form.addRow("Mémoire de conversation (tokens) :", self.ctx)

        self.layers = QSpinBox()
        self.layers.setRange(-1, 999)
        self.layers.setSpecialValueText("calcul automatique")
        self.layers.setValue(int(opts.get("gpu_layers", -1)))
        total = (self.meta.get("layers") or 0) + 1 if self.meta.get("layers") else 0
        form.addRow(f"Couches en VRAM{f' (sur {total})' if total else ''} :", self.layers)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setDecimals(1)
        self.temp.setValue(float(opts.get("temperature", 0.7)))
        form.addRow("Créativité (température) :", self.temp)
        temp_help = QLabel("0 = précis et constant · 0,7 = équilibré · 1,2+ = très créatif")
        temp_help.setObjectName("Muted")
        form.addRow("", temp_help)
        lay.addLayout(form)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("Status")
        lay.addWidget(self.summary)
        self.scope = QLabel("Ces réglages ne concernent que ce modèle. Sans réglage propre, un modèle suit la "
                            "priorité choisie dans l'onglet Analyse." if not opts.get("custom") else
                            "Ce modèle a ses propres réglages.")
        self.scope.setObjectName("Muted")
        self.scope.setWordWrap(True)
        lay.addWidget(self.scope)

        btns = QHBoxLayout()
        reset = QPushButton("Revenir au réglage général")
        reset.clicked.connect(self.reset)
        btns.addWidget(reset)
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("💾 Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save)
        btns.addWidget(save)
        lay.addLayout(btns)

        for w in (self.mode,):
            w.currentIndexChanged.connect(self.update_summary)
        for w in (self.ctx, self.layers):
            w.valueChanged.connect(self.update_summary)
        self.update_summary()

    def current(self) -> Dict:
        return {"mode": self.mode.currentData(), "num_ctx": self.ctx.value(),
                "temperature": round(self.temp.value(), 2), "gpu_layers": self.layers.value()}

    def update_summary(self):
        self.mode_help.setText(mo.MODE_HELP.get(self.mode.currentData(), ""))
        p = mo.plan(self.current(), self.meta, self.system_info)
        self.summary.setText("📊 " + p["summary"])

    def save(self):
        if self.is_local:
            mo.set_options(self.ref, self.current())
        self.accept()

    def reset(self):
        mo.reset_options(self.ref)
        self.accept()


class QuickCommandsDialog(QDialog):
    """Ajouter, modifier, supprimer les commandes rapides"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Commandes rapides")
        self.setMinimumSize(760, 520)
        self.commands: List[Dict] = qc.load()
        self.current = -1

        lay = QVBoxLayout(self)
        hint = QLabel("Tapez la commande au début d'un message, par exemple « /resume » suivi de votre texte. "
                      "Dans le modèle, {texte} est remplacé par ce que vous écrivez après la commande.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        row = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_selected)
        row.addWidget(self.list, 2)
        form_box = QVBoxLayout()
        form = QFormLayout()
        self.trigger = QLineEdit()
        self.trigger.setPlaceholderText("/macommande")
        form.addRow("Commande :", self.trigger)
        self.name = QLineEdit()
        form.addRow("Nom :", self.name)
        form_box.addLayout(form)
        self.template = QTextEdit()
        self.template.setAcceptRichText(False)
        self.template.setPlaceholderText("Consigne envoyée à l'IA. Utilisez {texte} pour votre texte.")
        form_box.addWidget(self.template, 1)
        row.addLayout(form_box, 3)
        lay.addLayout(row, 1)

        btns = QHBoxLayout()
        add = QPushButton("➕ Nouvelle")
        add.clicked.connect(self.add)
        btns.addWidget(add)
        delete = QPushButton("🗑 Supprimer")
        delete.setObjectName("Danger")
        delete.clicked.connect(self.delete)
        btns.addWidget(delete)
        reset = QPushButton("Rétablir les commandes d'origine")
        reset.clicked.connect(self.reset_defaults)
        btns.addWidget(reset)
        btns.addStretch()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("💾 Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save)
        btns.addWidget(save)
        lay.addLayout(btns)
        self.refresh()

    def refresh(self, select: int = 0):
        self.list.blockSignals(True)
        self.list.clear()
        for c in self.commands:
            self.list.addItem(QListWidgetItem(f"{c['trigger']}  —  {c['name']}"))
        self.list.blockSignals(False)
        self.current = -1
        if self.commands:
            self.list.setCurrentRow(min(select, len(self.commands) - 1))
            self.on_selected(self.list.currentRow())

    def store_current(self):
        if 0 <= self.current < len(self.commands):
            self.commands[self.current] = {"trigger": self.trigger.text().strip(),
                                           "name": self.name.text().strip(),
                                           "template": self.template.toPlainText()}

    def on_selected(self, row: int):
        if row == self.current:
            return
        self.store_current()
        self.current = row
        if 0 <= row < len(self.commands):
            c = self.commands[row]
            self.trigger.setText(c["trigger"])
            self.name.setText(c["name"])
            self.template.setPlainText(c["template"])

    def add(self):
        self.store_current()
        self.commands.append({"trigger": "/nouvelle", "name": "Nouvelle commande",
                              "template": "Fais ceci avec le texte suivant :\n\n{texte}"})
        self.refresh(len(self.commands) - 1)

    def delete(self):
        if 0 <= self.current < len(self.commands):
            self.commands.pop(self.current)
            self.refresh(max(0, self.current - 1))

    def reset_defaults(self):
        self.commands = [dict(c) for c in qc.DEFAULT_COMMANDS]
        self.refresh()

    def save(self):
        self.store_current()
        qc.save(self.commands)
        self.accept()
