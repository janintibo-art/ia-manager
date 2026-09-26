"""Onglet Tableau de bord - RAM/VRAM en direct, IA chargées en mémoire, bouton pour les décharger"""

from typing import Dict, List, Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from src.backend import dashboard as dash
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
    """Une IA actuellement chargée en mémoire, avec son bouton pour la décharger"""

    unload = pyqtSignal(str)

    def __init__(self, info: Dict):
        super().__init__()
        self.setObjectName("Card")
        self.name = info.get("name") or info.get("model") or "?"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        name_label = QLabel(f"<b>{self.name}</b>")
        lay.addWidget(name_label, 2)

        size_gb = (info.get("size") or 0) / (1024 ** 3)
        vram_gb = (info.get("size_vram") or 0) / (1024 ** 3)
        vram_pct = int(round((vram_gb / size_gb) * 100)) if size_gb else 0
        detail = QLabel(f"{human_gb(size_gb)} · {vram_pct}% en VRAM")
        detail.setObjectName("Muted")
        lay.addWidget(detail, 2)

        expiry = QLabel(info.get("expiry_text") or "")
        expiry.setObjectName("Muted")
        lay.addWidget(expiry, 1)

        btn = QPushButton("⏏️ Décharger")
        btn.setToolTip("Libère la VRAM/RAM tout de suite (l'IA se recharge au prochain message)")
        btn.clicked.connect(lambda: self.unload.emit(self.name))
        lay.addWidget(btn)


class DashboardTab(QWidget):
    """RAM/VRAM en direct et IA actuellement en mémoire"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.worker: Optional[FunctionWorker] = None
        self.unload_worker: Optional[FunctionWorker] = None
        self.rows: List[ModelRow] = []
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
        if not result["ollama_up"]:
            self.hint.setText("⚠️ Ollama n'est pas lancé : pas d'IA locale en mémoire pour l'instant.")
        else:
            self.hint.setText("")
        self.ram_meter.update_value(result["ram_used_gb"], result["ram_total_gb"])
        gpu = result["gpu"]
        if gpu["total_gb"] > 0:
            self.vram_meter.setVisible(True)
            self.vram_meter.update_value(gpu["used_gb"], gpu["total_gb"], gpu["exact"])
        else:
            self.vram_meter.setVisible(False)
        self.fill_running(result["running"])

    def fill_running(self, running: List[Dict]):
        for row in self.rows:
            self.list_layout.removeWidget(row)
            row.deleteLater()
        self.rows = []
        self.empty_label.setVisible(not running)
        self.unload_all_btn.setEnabled(bool(running))
        for info in running:
            row = ModelRow(info)
            row.unload.connect(self.unload_one)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self.rows.append(row)

    # ------------------------------------------------------------ décharger
    def unload_one(self, name: str):
        self.run_unload([name])

    def unload_all(self):
        names = [r.name for r in self.rows]
        if not names:
            return
        if QMessageBox.question(
            self, "Tout décharger", f"Décharger {len(names)} IA de la mémoire maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.run_unload(names)

    def run_unload(self, names: List[str]):
        if self.unload_worker is not None and self.unload_worker.isRunning():
            return

        def unload_several():
            for n in names:
                self.ai_manager.unload_model(n)
            return names

        self.unload_worker = FunctionWorker(unload_several)
        self.unload_worker.done.connect(lambda _ok, _r: self.refresh())
        self.unload_worker.start()
