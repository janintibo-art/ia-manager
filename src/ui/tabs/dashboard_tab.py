"""Onglet Tableau de bord - RAM/VRAM en direct, IA chargées en mémoire, bouton pour les décharger"""

import html
from typing import Dict, List, Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from src.backend import dashboard as dash
from src.backend import lmstudio
from src.backend.ai_manager import AIManager
from src.ui import style
from src.ui.workers import FunctionWorker

REFRESH_MS = 4000


def human_gb(value: float) -> str:
    return f"{value:.1f} Go"


class MeterRow(QWidget):
    """Une jauge : titre, barre de progression, texte "X / Y Go" """

    def __init__(self, title: str):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        head = QHBoxLayout()
        self.title_label = QLabel(title)
        head.addWidget(self.title_label)
        head.addStretch()
        self.value_label = QLabel("—")
        self.value_label.setObjectName("Muted")
        head.addWidget(self.value_label)
        lay.addLayout(head)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        lay.addWidget(self.bar)

    def update_value(self, used_gb: float, total_gb: float, exact: bool = True):
        pct = int(min(1000, max(0, (used_gb / total_gb) * 1000))) if total_gb > 0 else 0
        self.bar.setValue(pct)
        approx = "" if exact else " (approx.)"
        self.value_label.setText(f"{human_gb(used_gb)} / {human_gb(total_gb)}{approx}")
        color = style.RED if pct > 900 else (style.ORANGE if pct > 700 else style.GREEN)
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")


class ModelRow(QFrame):
    """Une IA actuellement chargée en mémoire, avec son bouton pour la décharger.
    source = "ollama" (name = nom du modèle) ou "lmstudio" (name = identifiant de l'instance)."""

    unload = pyqtSignal(str, str)  # source, nom

    def __init__(self, source: str, name: str, title: str, detail: str, extra: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.source = source
        self.name = name
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        badge = "💻 Ollama" if source == "ollama" else "🧪 LM Studio"
        name_label = QLabel(f"<b>{html.escape(title)}</b><br><span style='color:{style.TEXT_MUTED}'>{badge}</span>")
        lay.addWidget(name_label, 2)
        detail_label = QLabel(detail)
        detail_label.setObjectName("Muted")
        lay.addWidget(detail_label, 2)
        extra_label = QLabel(extra)
        extra_label.setObjectName("Muted")
        lay.addWidget(extra_label, 1)
        btn = QPushButton("⏏️ Décharger")
        btn.setToolTip("Libère la VRAM/RAM tout de suite (l'IA se recharge au prochain message)")
        btn.clicked.connect(lambda: self.unload.emit(self.source, self.name))
        lay.addWidget(btn)

    @classmethod
    def from_ollama(cls, info: Dict) -> "ModelRow":
        name = info.get("name") or info.get("model") or "?"
        size_gb = (info.get("size") or 0) / (1024 ** 3)
        vram_gb = (info.get("size_vram") or 0) / (1024 ** 3)
        vram_pct = int(round((vram_gb / size_gb) * 100)) if size_gb else 0
        return cls("ollama", name, name, f"{human_gb(size_gb)} · {vram_pct}% en VRAM",
                   info.get("expiry_text") or "")

    @classmethod
    def from_lmstudio(cls, model: Dict, instance: Dict) -> "ModelRow":
        parts = []
        if model.get("size_bytes"):
            parts.append(human_gb(model["size_bytes"] / (1024 ** 3)))
        if model.get("quant"):
            parts.append(model["quant"])
        if model.get("params"):
            parts.append(model["params"])
        extra = f"contexte {instance['ctx']}" if instance.get("ctx") else ""
        return cls("lmstudio", instance.get("id") or model["key"], model.get("name") or model["key"],
                   " · ".join(parts), extra)


class DashboardTab(QWidget):
    """RAM/VRAM en direct et IA actuellement en mémoire (Ollama et LM Studio)"""

    models_changed = pyqtSignal()  # LM Studio détecté ou sa liste de modèles a changé

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.worker: Optional[FunctionWorker] = None
        self.unload_worker: Optional[FunctionWorker] = None
        self.rows: List[ModelRow] = []
        self.lmstudio_up = False
        self.warning = ""
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(REFRESH_MS)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        QTimer.singleShot(150, self.refresh)

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(12)

        title = QLabel("Tableau de bord")
        title.setObjectName("Title")
        root.addWidget(title)

        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        meters = QFrame()
        meters.setObjectName("Card")
        ml = QVBoxLayout(meters)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(10)
        self.ram_meter = MeterRow("🧠 RAM")
        ml.addWidget(self.ram_meter)
        self.vram_meter = MeterRow("🎮 VRAM")
        ml.addWidget(self.vram_meter)
        root.addWidget(meters)

        head = QHBoxLayout()
        head.addWidget(QLabel("IA actuellement chargées en mémoire"))
        head.addStretch()
        self.unload_all_btn = QPushButton("⏏️ Tout décharger")
        self.unload_all_btn.clicked.connect(self.unload_all)
        head.addWidget(self.unload_all_btn)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser maintenant")
        refresh_btn.clicked.connect(self.refresh)
        head.addWidget(refresh_btn)
        root.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setSpacing(8)
        self.empty_label = QLabel("Aucune IA chargée actuellement.")
        self.empty_label.setObjectName("Muted")
        self.list_layout.addWidget(self.empty_label)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_host)
        root.addWidget(scroll, 1)

    # ------------------------------------------------------------ rafraîchissement
    def refresh(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.worker = FunctionWorker(dash.snapshot, self.ai_manager)
        self.worker.done.connect(self.on_snapshot)
        self.worker.start()

    def on_snapshot(self, ok: bool, result):
        if not ok or not isinstance(result, dict):
            self.hint.setText(f"⚠️ Impossible de lire l'état du système : {result}")
            return
        lm = result.get("lmstudio")
        self.lmstudio_up = lm is not None
        notes = []
        if not result["ollama_up"]:
            notes.append("Ollama n'est pas lancé")
        notes.append("🧪 LM Studio détecté" if self.lmstudio_up else "LM Studio n'est pas lancé (serveur local)")
        if self.warning:
            notes.append(self.warning)
            self.warning = ""
        self.hint.setText(" · ".join(notes))
        self.ram_meter.update_value(result["ram_used_gb"], result["ram_total_gb"])
        gpu = result["gpu"]
        if gpu["total_gb"] > 0:
            self.vram_meter.setVisible(True)
            self.vram_meter.update_value(gpu["used_gb"], gpu["total_gb"], gpu["exact"])
        else:
            self.vram_meter.setVisible(False)
        self.fill_running(result["running"], lm or [])
        if lmstudio.apply_models(lm):
            self.models_changed.emit()

    def fill_running(self, running: List[Dict], lm_models: Optional[List[Dict]] = None):
        for row in self.rows:
            self.list_layout.removeWidget(row)
            row.deleteLater()
        self.rows = []
        new_rows = [ModelRow.from_ollama(info) for info in running]
        for m in lm_models or []:
            for inst in m.get("instances") or []:
                new_rows.append(ModelRow.from_lmstudio(m, inst))
        self.empty_label.setVisible(not new_rows)
        self.unload_all_btn.setEnabled(bool(new_rows))
        for row in new_rows:
            row.unload.connect(self.unload_one)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self.rows.append(row)

    # ------------------------------------------------------------ décharger
    def unload_one(self, source: str, name: str):
        self.run_unload([(source, name)])

    def unload_all(self):
        targets = [(r.source, r.name) for r in self.rows]
        if not targets:
            return
        if QMessageBox.question(
            self, "Tout décharger", f"Décharger {len(targets)} IA de la mémoire maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.run_unload(targets)

    def run_unload(self, targets: List[tuple]):
        if self.unload_worker is not None and self.unload_worker.isRunning():
            return
        ai = self.ai_manager

        def unload_several():
            failed = []
            for source, name in targets:
                ok = ai.unload_model(name) if source == "ollama" else lmstudio.unload(name)
                if not ok:
                    failed.append(name)
            return failed

        self.unload_worker = FunctionWorker(unload_several)
        self.unload_worker.done.connect(self.on_unloaded)
        self.unload_worker.start()

    def on_unloaded(self, ok: bool, failed):
        if ok and failed:
            self.warning = ("⚠️ Impossible de décharger : " + ", ".join(failed)
                            + " (pour LM Studio, la version 0.4 ou plus récente est nécessaire)")
        self.refresh()
