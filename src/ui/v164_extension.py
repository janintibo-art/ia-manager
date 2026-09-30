"""v164 : Assistant local IA Manager."""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextBrowser,
    QVBoxLayout, QWidget,
)

from src.backend import local_manager_assistant as assistant
from src.backend.ai_manager import AIManager
from src.backend import universal_history as uh


QUICK = (
    ("🩺 Pourquoi ça ne marche pas ?", "Quelles erreurs ou problèmes récents vois-tu dans IA Manager ?"),
    ("🎨 État de ComfyUI", "Pourquoi ComfyUI ne démarre pas ou n'est pas prêt ?"),
    ("🦙 État d’Ollama", "Quel est l'état d'Ollama et quels modèles sont disponibles ?"),
    ("🧠 Quel modèle choisir ?", "Quel modèle est adapté à mon matériel actuel ?"),
    ("📁 Où sont mes fichiers ?", "Où sont stockés mes modèles, conversions et sauvegardes ?"),
    ("💽 Espace disque", "Combien d'espace disque reste-t-il pour IA Manager ?"),
)


class AnswerWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model, question, state, parent=None):
        super().__init__(parent)
        self.model = model
        self.question = question
        self.state = state

    def run(self):
        try:
            prompt = assistant.ollama_prompt(self.question, self.state)
            answer = AIManager().chat(self.model, prompt)
            self.done.emit(str(answer))
        except Exception as exc:
            self.failed.emit(str(exc))


class LocalAssistantTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.state = {}
        self.worker = None
        self.suggested_target = ""
        self.build_ui()
        self.refresh_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🤖 Assistant IA Manager")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Posez une question sur votre installation. Le diagnostic direct fonctionne sans IA. "
            "Vous pouvez aussi demander à un modèle Ollama local d'enrichir la réponse à partir du même état vérifié."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        quick = QHBoxLayout()
        for label, question in QUICK:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, q=question: self.ask_quick(q))
            quick.addWidget(b)
        root.addLayout(quick)

        self.question = QPlainTextEdit()
        self.question.setPlaceholderText(
            "Exemple : Pourquoi ComfyUI ne démarre pas ? Où est mon modèle Qwen ? "
            "Quel modèle puis-je utiliser avec mon GPU ?"
        )
        self.question.setMaximumHeight(110)
        root.addWidget(self.question)

        row = QHBoxLayout()
        self.direct_btn = QPushButton("⚡ Diagnostic direct")
        self.direct_btn.setObjectName("Primary")
        self.direct_btn.clicked.connect(self.answer_direct)
        row.addWidget(self.direct_btn)

        row.addWidget(QLabel("IA locale facultative :"))
        self.model = QComboBox()
        self.model.setMinimumWidth(280)
        row.addWidget(self.model, 1)

        self.ai_btn = QPushButton("🧠 Réponse enrichie avec Ollama")
        self.ai_btn.clicked.connect(self.answer_ai)
        row.addWidget(self.ai_btn)

        self.refresh_btn = QPushButton("🔄 Actualiser l’état")
        self.refresh_btn.clicked.connect(self.refresh_state)
        row.addWidget(self.refresh_btn)
        root.addLayout(row)

        self.state_label = QLabel("")
        self.state_label.setWordWrap(True)
        self.state_label.setObjectName("Muted")
        root.addWidget(self.state_label)

        self.answer = QTextBrowser()
        self.answer.setOpenExternalLinks(False)
        root.addWidget(self.answer, 1)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("➡ Ouvrir l’écran conseillé")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.open_suggested)
        actions.addWidget(self.open_btn)

        health = QPushButton("🩺 Centre de santé")
        health.clicked.connect(lambda: self.open_attr("health_tab"))
        actions.addWidget(health)

        history = QPushButton("🕘 Historique")
        history.clicked.connect(lambda: self.open_attr("history_tab"))
        actions.addWidget(history)
        actions.addStretch()
        root.addLayout(actions)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh_state(self):
        self.state = assistant.collect_state(self.window)
        models = self.state.get("ollama", {}).get("models") or []
        keep = self.model.currentText() if self.model.count() else ""
        self.model.clear()
        self.model.addItems(models)
        if keep:
            idx = self.model.findText(keep)
            if idx >= 0:
                self.model.setCurrentIndex(idx)

        sys = self.state.get("system") or {}
        comfy = self.state.get("comfyui") or {}
        ollama = self.state.get("ollama") or {}
        self.state_label.setText(
            f"État actuel · GPU {sys.get('gpu_type','?')} · VRAM {float(sys.get('vram_gb') or 0):.1f} Go · "
            f"Ollama {'OK' if ollama.get('running') else 'arrêté'} · "
            f"ComfyUI {'OK' if comfy.get('running') else 'arrêté'} · "
            f"{len(models)} modèle(s) Ollama"
        )
        self.ai_btn.setEnabled(bool(models) and bool(ollama.get("running")))
        self.status.setText("État actualisé.")

    def ask_quick(self, question):
        self.question.setPlainText(question)
        self.answer_direct()

    def answer_direct(self):
        self.refresh_state()
        text, target = assistant.direct_answer(self.question.toPlainText(), self.state)
        self.answer.setPlainText(text)
        self.suggested_target = target
        self.open_btn.setEnabled(bool(target) and getattr(self.window, target, None) is not None)
        self.status.setText("Réponse basée sur l’état réel détecté par IA Manager.")
        try:
            uh.record(
                "Système",
                "Question à l’assistant IA Manager",
                self.question.toPlainText()[:180],
                "info",
                "",
                "Assistant local",
            )
        except Exception:
            pass

    def answer_ai(self):
        question = self.question.toPlainText().strip()
        model = self.model.currentText().strip()
        if not question:
            self.status.setText("Écrivez d’abord une question.")
            return
        if not model:
            self.status.setText("Aucun modèle Ollama local disponible.")
            return

        self.refresh_state()
        self.set_busy(True)
        self.answer.setPlainText(
            "Analyse de l’état IA Manager puis réponse par le modèle local…"
        )
        self.worker = AnswerWorker(model, question, dict(self.state), self)
        self.worker.done.connect(self.ai_done)
        self.worker.failed.connect(self.ai_failed)
        self.worker.start()

    def set_busy(self, busy):
        self.direct_btn.setEnabled(not busy)
        self.ai_btn.setEnabled(not busy and self.model.count() > 0)
        self.refresh_btn.setEnabled(not busy)
        self.model.setEnabled(not busy)

    def ai_done(self, text):
        self.set_busy(False)
        self.worker = None
        self.answer.setPlainText(text)
        self.status.setText("Réponse générée localement avec Ollama à partir du contexte IA Manager.")
        try:
            uh.record(
                "Système",
                "Réponse assistant local via Ollama",
                self.model.currentText(),
                "success",
                "",
                "Assistant local",
            )
        except Exception:
            pass

    def ai_failed(self, error):
        self.set_busy(False)
        self.worker = None
        self.answer.setPlainText("Erreur : " + error)
        self.status.setText("La réponse Ollama a échoué. Le diagnostic direct reste disponible.")

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)

    def open_suggested(self):
        if self.suggested_target:
            self.open_attr(self.suggested_target)


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ACCUEIL":
                if not any(e[0] == "local_assistant_tab" for e in entries):
                    entries.insert(1, (
                        "local_assistant_tab",
                        "Assistant IA Manager",
                        "Posez des questions sur l’état réel de l’application et du PC."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v164(window):
    if getattr(window, "_v164_local_assistant", False):
        return

    tab = LocalAssistantTab(window)
    window.local_assistant_tab = tab

    goal = getattr(window, "goal_assistant_tab", None)
    idx = window.tabs.indexOf(goal)
    window.tabs.insertTab(idx + 1 if idx >= 0 else 0, tab, "🤖 Assistant IA Manager")

    _add_nav(window)
    window._v164_local_assistant = True
