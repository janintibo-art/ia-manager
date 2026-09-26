"""Onglet Comparateur - poser la même question à 2 ou 3 IA et voir leurs réponses côte à côte"""

from typing import List, Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextBrowser, QTextEdit,
    QVBoxLayout, QWidget,
)

from src.backend import providers
from src.backend.ai_manager import AIManager
from src.ui.workers import StreamWorker

COLUMN_COUNT = 3


class CompareColumn(QWidget):
    """Une colonne : choix de l'IA, réponse au fil de l'eau, statistiques"""

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.worker: Optional[StreamWorker] = None
        self.buffer: List[str] = []
        self.flush_timer = QTimer(self)
        self.flush_timer.setInterval(80)
        self.flush_timer.timeout.connect(self.flush)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.combo = QComboBox()
        lay.addWidget(self.combo)
        self.body = QTextBrowser()
        self.body.setObjectName("Console")
        lay.addWidget(self.body, 1)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

    def ref(self) -> str:
        return self.combo.currentData() or ""

    def start(self, messages: List[dict], system: str):
        ref = self.ref()
        self.body.clear()
        self.buffer = []
        if not ref:
            self.status.setText("—")
            return
        self.status.setText("⏳ L'IA réfléchit…")
        self.worker = StreamWorker(ref, messages, system)
        self.worker.token.connect(self.buffer.append)
        self.worker.phase.connect(self.status.setText)
        self.worker.done.connect(self.on_done)
        self.worker.start()
        self.flush_timer.start()

    def flush(self):
        if not self.buffer:
            return
        chunk = "".join(self.buffer)
        self.buffer.clear()
        cursor = self.body.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.body.setTextCursor(cursor)
        if self.status.text().startswith("⏳"):
            self.status.setText("✍️ L'IA écrit…")

    def on_done(self, text: str, stats: dict):
        self.flush_timer.stop()
        self.flush()
        if text.startswith(("Erreur", "Ollama n'est pas lancé")):
            self.status.setText(f"❌ {text}")
            return
        parts = []
        if stats.get("tokens_per_s"):
            parts.append(f"⚡ {stats['tokens_per_s']:.1f} tokens/s")
        if stats.get("seconds"):
            parts.append(f"{stats['seconds']:.0f} s")
        if stats.get("tokens"):
            parts.append(f"{stats['tokens']} tokens")
        self.status.setText(" · ".join(parts) or "✅ Terminé")

    def stop(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()

    def busy(self) -> bool:
        return self.worker is not None and self.worker.isRunning()


class ComparatorTab(QWidget):
    """Envoie la même question à plusieurs IA en même temps pour comparer les réponses"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.columns: List[CompareColumn] = []
        self.init_ui()
        self.refresh_models()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("Comparateur")
        title.setObjectName("Title")
        root.addWidget(title)
        hint = QLabel("Choisissez 2 ou 3 IA, posez la même question, comparez leurs réponses côte à côte.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.prompt = QTextEdit()
        self.prompt.setFixedHeight(80)
        self.prompt.setPlaceholderText("Votre question, envoyée telle quelle à chaque IA sélectionnée…")
        root.addWidget(self.prompt)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser la liste des IA")
        refresh_btn.clicked.connect(self.refresh_models)
        btn_row.addWidget(refresh_btn)
        self.send_btn = QPushButton("⚖️ Comparer")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self.compare)
        btn_row.addWidget(self.send_btn)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(self.stop_all)
        btn_row.addWidget(self.stop_btn)
        root.addLayout(btn_row)

        columns_row = QHBoxLayout()
        columns_row.setSpacing(10)
        for i in range(COLUMN_COUNT):
            col = CompareColumn(i)
            self.columns.append(col)
            columns_row.addWidget(col, 1)
        root.addLayout(columns_row, 1)

    def refresh_models(self):
        local = self.ai_manager.get_available_models()
        choices = providers.all_model_choices(local)
        for i, col in enumerate(self.columns):
            current = col.ref()
            col.combo.blockSignals(True)
            col.combo.clear()
            col.combo.addItem("— (ne pas utiliser)", "")
            for label, ref in choices:
                col.combo.addItem(label, ref)
            idx = col.combo.findData(current) if current else -1
            if idx >= 0:
                col.combo.setCurrentIndex(idx)
            elif i < min(2, len(choices)):
                col.combo.setCurrentIndex(i + 1)
            col.combo.blockSignals(False)

    def compare(self):
        text = self.prompt.toPlainText().strip()
        if not text:
            return
        active = [c for c in self.columns if c.ref()]
        if len(active) < 2:
            QMessageBox.information(self, "Pas assez d'IA", "Choisissez au moins deux IA à comparer.")
            return
        if any(c.busy() for c in self.columns):
            QMessageBox.information(self, "Déjà en cours", "Une comparaison est déjà en cours.")
            return
        messages = [{"role": "user", "content": text}]
        for col in self.columns:
            col.start(messages, "")

    def stop_all(self):
        for col in self.columns:
            col.stop()
