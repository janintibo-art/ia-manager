"""Extension v128 : comparaison Avant / Après Obliteratus."""
from datetime import datetime
import json
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QSplitter, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from src.backend.ai_manager import AIManager
from src.ui.workers import FunctionWorker


def _history_file() -> Path:
    path = Path.home() / ".ia_manager" / "obliteratus_comparisons.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _compare(ai: AIManager, original: str, modified: str, prompt: str):
    before = ai.chat(original, prompt)
    after = ai.chat(modified, prompt)
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "original": original,
        "modified": modified,
        "prompt": prompt,
        "before": before,
        "after": after,
    }


def _save_history(item: dict):
    with _history_file().open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")


def _load_history(limit=30):
    path = _history_file()
    if not path.is_file():
        return []
    rows = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                try:
                    rows.append(json.loads(line))
                except (json.JSONDecodeError, TypeError):
                    pass
    except OSError:
        return []
    return rows[-limit:][::-1]


def install_v128(window):
    tab = getattr(window, "obliteratus_tab", None)
    if tab is None or getattr(window, "_v128_obliteratus", False):
        return

    tab.v128_ai = AIManager()
    tab.v128_worker = None
    tab.v128_history_rows = []

    group = QGroupBox("6 · Comparatif Avant / Après Obliteratus")
    layout = QVBoxLayout(group)

    hint = QLabel(
        "Testez exactement le même prompt sur le modèle d’origine et sur sa version "
        "Obliteratus importée dans Ollama. Les deux réponses sont affichées côte à côte."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    selectors = QHBoxLayout()
    selectors.addWidget(QLabel("Avant"))
    tab.v128_original = QComboBox()
    tab.v128_original.setMinimumWidth(220)
    selectors.addWidget(tab.v128_original, 1)

    selectors.addWidget(QLabel("Après"))
    tab.v128_modified = QComboBox()
    tab.v128_modified.setMinimumWidth(220)
    selectors.addWidget(tab.v128_modified, 1)

    tab.v128_refresh = QPushButton("🔄 Modèles")
    selectors.addWidget(tab.v128_refresh)
    layout.addLayout(selectors)

    tab.v128_prompt = QTextEdit()
    tab.v128_prompt.setPlaceholderText(
        "Écrivez un prompt de test. Il sera envoyé à l’identique aux deux modèles."
    )
    tab.v128_prompt.setFixedHeight(90)
    layout.addWidget(tab.v128_prompt)

    actions = QHBoxLayout()
    tab.v128_compare = QPushButton("⚖️ Comparer les deux modèles")
    tab.v128_compare.setObjectName("Primary")
    actions.addWidget(tab.v128_compare)

    tab.v128_to_chat_before = QPushButton("💬 Ouvrir l’original dans Chat")
    actions.addWidget(tab.v128_to_chat_before)

    tab.v128_to_chat_after = QPushButton("💬 Ouvrir la version Obliteratus dans Chat")
    actions.addWidget(tab.v128_to_chat_after)
    actions.addStretch()
    layout.addLayout(actions)

    tab.v128_status = QLabel("Prêt.")
    tab.v128_status.setWordWrap(True)
    layout.addWidget(tab.v128_status)

    splitter = QSplitter(Qt.Orientation.Horizontal)

    before_widget = QWidget()
    before_layout = QVBoxLayout(before_widget)
    before_layout.setContentsMargins(0, 0, 0, 0)
    before_title = QLabel("AVANT · modèle original")
    before_title.setStyleSheet("font-weight: 700;")
    before_layout.addWidget(before_title)
    tab.v128_before = QTextBrowser()
    tab.v128_before.setPlaceholderText("La réponse du modèle original apparaîtra ici.")
    before_layout.addWidget(tab.v128_before)

    after_widget = QWidget()
    after_layout = QVBoxLayout(after_widget)
    after_layout.setContentsMargins(0, 0, 0, 0)
    after_title = QLabel("APRÈS · modèle Obliteratus")
    after_title.setStyleSheet("font-weight: 700;")
    after_layout.addWidget(after_title)
    tab.v128_after = QTextBrowser()
    tab.v128_after.setPlaceholderText("La réponse du modèle modifié apparaîtra ici.")
    after_layout.addWidget(tab.v128_after)

    splitter.addWidget(before_widget)
    splitter.addWidget(after_widget)
    splitter.setSizes([500, 500])
    splitter.setMinimumHeight(260)
    layout.addWidget(splitter)

    hist_title = QLabel("Historique des comparaisons")
    hist_title.setStyleSheet("font-weight: 600;")
    layout.addWidget(hist_title)
    tab.v128_history = QListWidget()
    tab.v128_history.setMaximumHeight(150)
    layout.addWidget(tab.v128_history)

    tab.layout().addWidget(group)

    def v128_refresh_models(self):
        current_before = self.v128_original.currentText()
        current_after = self.v128_modified.currentText()
        self.v128_original.clear()
        self.v128_modified.clear()

        models = self.v128_ai.get_available_models(force=True)
        for model in models:
            self.v128_original.addItem(model)
            self.v128_modified.addItem(model)

        preferred_before = getattr(self, "v126_selected_ollama", "") or current_before
        preferred_after = getattr(self, "chat_ready_name", "") or current_after

        if preferred_before:
            idx = self.v128_original.findText(preferred_before)
            if idx >= 0:
                self.v128_original.setCurrentIndex(idx)

        if preferred_after:
            idx = self.v128_modified.findText(preferred_after)
            if idx >= 0:
                self.v128_modified.setCurrentIndex(idx)

        self.v128_status.setText(
            f"{len(models)} modèle(s) Ollama disponible(s)." if models
            else "Aucun modèle Ollama détecté."
        )
        self.v128_update_buttons()

    def v128_update_buttons(self):
        busy = self.v128_worker is not None and self.v128_worker.isRunning()
        before = self.v128_original.currentText().strip()
        after = self.v128_modified.currentText().strip()
        prompt = self.v128_prompt.toPlainText().strip()
        self.v128_compare.setEnabled(not busy and bool(before) and bool(after) and bool(prompt))
        self.v128_refresh.setEnabled(not busy)
        self.v128_original.setEnabled(not busy)
        self.v128_modified.setEnabled(not busy)
        self.v128_prompt.setEnabled(not busy)
        self.v128_to_chat_before.setEnabled(not busy and bool(before))
        self.v128_to_chat_after.setEnabled(not busy and bool(after))

    def v128_start_compare(self):
        before = self.v128_original.currentText().strip()
        after = self.v128_modified.currentText().strip()
        prompt = self.v128_prompt.toPlainText().strip()
        if not before or not after or not prompt:
            return
        if before == after:
            answer = QMessageBox.question(
                self,
                "Même modèle",
                "Vous avez choisi le même modèle des deux côtés. Continuer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.v128_before.clear()
        self.v128_after.clear()
        self.v128_status.setText("⏳ Comparaison en cours : original puis version Obliteratus…")

        worker = FunctionWorker(_compare, self.v128_ai, before, after, prompt)
        self.v128_worker = worker
        worker.done.connect(lambda ok, value, w=worker: self.v128_compare_done(w, ok, value))
        self.v128_update_buttons()
        worker.start()

    def v128_compare_done(self, worker, ok, value):
        if self.v128_worker is not worker:
            return
        self.v128_worker = None

        if not ok:
            self.v128_status.setText("❌ Comparaison impossible : " + str(value))
            self.v128_update_buttons()
            return

        result = dict(value)
        self.v128_before.setPlainText(result.get("before", ""))
        self.v128_after.setPlainText(result.get("after", ""))
        try:
            _save_history(result)
        except OSError:
            pass
        self.v128_status.setText(
            f"✅ Comparaison terminée · {result.get('original')} ↔ {result.get('modified')}"
        )
        self.v128_reload_history()
        self.v128_update_buttons()

    def v128_reload_history(self):
        self.v128_history_rows = _load_history()
        self.v128_history.clear()
        for row in self.v128_history_rows:
            stamp = str(row.get("time", "")).replace("T", " ")
            prompt = str(row.get("prompt", "")).replace("\n", " ")
            if len(prompt) > 80:
                prompt = prompt[:77] + "…"
            self.v128_history.addItem(
                f"{stamp} · {row.get('original', '?')} → {row.get('modified', '?')} · {prompt}"
            )

    def v128_history_selected(self, row):
        if row < 0 or row >= len(self.v128_history_rows):
            return
        item = self.v128_history_rows[row]
        self.v128_prompt.setPlainText(str(item.get("prompt", "")))
        self.v128_before.setPlainText(str(item.get("before", "")))
        self.v128_after.setPlainText(str(item.get("after", "")))

        for combo, key in (
            (self.v128_original, "original"),
            (self.v128_modified, "modified"),
        ):
            idx = combo.findText(str(item.get(key, "")))
            if idx >= 0:
                combo.setCurrentIndex(idx)

        self.v128_status.setText("Historique chargé.")

    def v128_chat_before(self):
        model = self.v128_original.currentText().strip()
        if model:
            self.open_model_chat.emit(model)

    def v128_chat_after(self):
        model = self.v128_modified.currentText().strip()
        if model:
            self.open_model_chat.emit(model)

    tab.v128_refresh_models = MethodType(v128_refresh_models, tab)
    tab.v128_update_buttons = MethodType(v128_update_buttons, tab)
    tab.v128_start_compare = MethodType(v128_start_compare, tab)
    tab.v128_compare_done = MethodType(v128_compare_done, tab)
    tab.v128_reload_history = MethodType(v128_reload_history, tab)
    tab.v128_history_selected = MethodType(v128_history_selected, tab)
    tab.v128_chat_before = MethodType(v128_chat_before, tab)
    tab.v128_chat_after = MethodType(v128_chat_after, tab)

    tab.v128_refresh.clicked.connect(tab.v128_refresh_models)
    tab.v128_compare.clicked.connect(tab.v128_start_compare)
    tab.v128_to_chat_before.clicked.connect(tab.v128_chat_before)
    tab.v128_to_chat_after.clicked.connect(tab.v128_chat_after)
    tab.v128_history.currentRowChanged.connect(tab.v128_history_selected)
    tab.v128_original.currentIndexChanged.connect(tab.v128_update_buttons)
    tab.v128_modified.currentIndexChanged.connect(tab.v128_update_buttons)
    tab.v128_prompt.textChanged.connect(tab.v128_update_buttons)

    # Après un export Obliteratus réussi, recharger les modèles pour retrouver
    # automatiquement le nouveau nom Ollama.
    old_finished = tab.finished

    def finished(self, code, exit_status):
        old_finished(code, exit_status)
        try:
            self.v128_refresh_models()
        except Exception:
            pass

    tab.finished = MethodType(finished, tab)

    tab.v128_reload_history()
    tab.v128_refresh_models()
    window._v128_obliteratus = True
