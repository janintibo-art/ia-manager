"""Extension v126 : pont Modèles -> Obliteratus et moteur intégré sans serveur."""
from types import MethodType
import re

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)

from src.backend import local_jobs
from src.backend import obliteratus as ob


OLLAMA_TO_HF = {
    "llama3.2:1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama3.2:3b": "meta-llama/Llama-3.2-3B-Instruct",
    "llama3.1:8b": "meta-llama/Llama-3.1-8B-Instruct",
    "llama3.1:70b": "meta-llama/Llama-3.1-70B-Instruct",
    "llama3.3:70b": "meta-llama/Llama-3.3-70B-Instruct",
    "mistral-nemo:12b": "mistralai/Mistral-Nemo-Instruct-2407",
    "mistral-small:24b": "mistralai/Mistral-Small-24B-Instruct-2501",
    "phi4:14b": "microsoft/phi-4",
    "phi4-mini:3.8b": "microsoft/Phi-4-mini-instruct",
    "deepseek-r1:8b": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "deepseek-r1:14b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "deepseek-r1:32b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "deepseek-r1:70b": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
}


def huggingface_source(model_id: str):
    model_id = (model_id or "").strip()
    if not model_id:
        return "", False
    if model_id in OLLAMA_TO_HF:
        return OLLAMA_TO_HF[model_id], True

    base, sep, tag = model_id.partition(":")
    tag_l = tag.lower()
    if sep and re.fullmatch(r"\d+(?:\.\d+)?b", tag_l):
        size_upper = tag_l[:-1] + "B"
        size_lower = tag_l[:-1] + "b"
        if base == "qwen3":
            return f"Qwen/Qwen3-{size_upper}", True
        if base == "qwen2.5":
            return f"Qwen/Qwen2.5-{size_upper}-Instruct", True
        if base == "gemma3":
            return f"google/gemma-3-{size_lower}-it", True

    if "/" in model_id and " " not in model_id:
        return model_id, True
    return model_id, False


def integrated_command(source: str, method: str):
    source = (source or "").strip()
    if not source:
        raise ValueError("Choisissez un modèle Hugging Face ou un checkpoint local.")
    allowed = {
        "basic", "advanced", "aggressive", "spectral_cascade", "informed",
        "surgical", "optimized", "som", "inverted", "nuclear",
    }
    if method not in allowed:
        raise ValueError("Méthode Obliteratus inconnue.")
    python = ob.environment_python()
    if not python.is_file():
        raise ValueError("Installez Obliteratus avant d'utiliser le mode intégré.")
    return str(python), [
        "-u", "-m", "obliteratus", "obliterate", source, "--method", method,
    ]


def install_v126(window):
    models = getattr(window, "models_tab", None)
    tab = getattr(window, "obliteratus_tab", None)
    if models is None or tab is None or getattr(window, "_v126_obliteratus", False):
        return

    send_box = QGroupBox("Obliteratus")
    send_layout = QHBoxLayout(send_box)
    send_text = QLabel("Envoyez le modèle sélectionné directement vers l'atelier Obliteratus.")
    send_text.setWordWrap(True)
    send_layout.addWidget(send_text, 1)
    models.obliteratus_btn = QPushButton("🧪 Ouvrir dans Obliteratus")
    models.obliteratus_btn.setToolTip(
        "Préremplit Obliteratus avec l'équivalent Hugging Face de ce modèle."
    )
    send_layout.addWidget(models.obliteratus_btn)
    models.layout().insertWidget(3, send_box)

    old_update_buttons = models.update_buttons

    def update_buttons(self):
        old_update_buttons()
        self.obliteratus_btn.setEnabled(bool(self.current_id))

    models.update_buttons = MethodType(update_buttons, models)

    native = QGroupBox("Mode intégré · sans serveur ni navigateur")
    native_layout = QVBoxLayout(native)
    native_hint = QLabel(
        "IA Manager pilote directement le moteur Obliteratus dans son environnement Python "
        "isolé. Aucun serveur Gradio n'est lancé. Le modèle peut être une référence "
        "Hugging Face ou un checkpoint local."
    )
    native_hint.setWordWrap(True)
    native_layout.addWidget(native_hint)

    form = QFormLayout()
    tab.v126_source = QLineEdit()
    tab.v126_source.setPlaceholderText("Ex. Qwen/Qwen3-8B ou chemin vers un checkpoint local")
    form.addRow("Modèle source", tab.v126_source)

    tab.v126_method = QComboBox()
    for key, label in (
        ("advanced", "Advanced · équilibré"),
        ("informed", "Informed · analyse automatique"),
        ("surgical", "Surgical · intervention ciblée"),
        ("basic", "Basic · rapide"),
        ("aggressive", "Aggressive · plus fort"),
        ("spectral_cascade", "Spectral cascade"),
        ("optimized", "Optimized"),
        ("som", "SOM"),
        ("inverted", "Inverted"),
        ("nuclear", "Nuclear"),
    ):
        tab.v126_method.addItem(label, key)
    form.addRow("Méthode", tab.v126_method)
    native_layout.addLayout(form)

    buttons = QHBoxLayout()
    tab.v126_run = QPushButton("▶ Lancer dans IA Manager")
    tab.v126_run.setObjectName("Primary")
    buttons.addWidget(tab.v126_run)
    tab.v126_stop = QPushButton("■ Arrêter")
    tab.v126_stop.setEnabled(False)
    buttons.addWidget(tab.v126_stop)
    buttons.addStretch()
    native_layout.addLayout(buttons)

    tab.v126_status = QLabel(
        "Prêt · choisissez un modèle ou utilisez « Ouvrir dans Obliteratus » depuis l'onglet Modèles."
    )
    tab.v126_status.setWordWrap(True)
    native_layout.addWidget(tab.v126_status)
    tab.layout().insertWidget(2, native)

    tab.v126_process = QProcess(tab)
    tab.v126_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v126_resource_token = None
    tab.v126_selected_ollama = ""

    def v126_append_log(self):
        text = bytes(self.v126_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)

    def v126_set_busy(self, busy):
        self.v126_run.setEnabled(not busy)
        self.v126_stop.setEnabled(busy)
        self.v126_source.setEnabled(not busy)
        self.v126_method.setEnabled(not busy)
        if busy:
            self.start.setEnabled(False)
            self.install.setEnabled(False)
            self.export_button.setEnabled(False)
        else:
            self.update_buttons()

    def v126_start(self):
        if self.v126_process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.mode or self.detecting:
            self.v126_status.setText(
                "Une autre opération Obliteratus est déjà active. Arrêtez-la ou attendez sa fin."
            )
            return
        try:
            program, args = integrated_command(
                self.v126_source.text(), self.v126_method.currentData()
            )
        except Exception as exc:
            self.v126_status.setText(str(exc))
            return

        if local_jobs.enabled():
            self.v126_resource_token = local_jobs.reserve("Obliteratus intégré")
            if self.v126_resource_token is None:
                self.v126_status.setText(
                    "Un autre travail local utilise déjà les ressources. Attendez sa fin."
                )
                return

        self.log.clear()
        self.v126_status.setText(
            "Traitement Obliteratus en cours · progression détaillée dans le journal."
        )
        v126_set_busy(self, True)

        env = QProcessEnvironment.systemEnvironment()
        for key, value in {
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "OBLITERATUS_TELEMETRY": "0",
            "GRADIO_ANALYTICS_ENABLED": "False",
        }.items():
            env.insert(key, value)
        self.v126_process.setProcessEnvironment(env)
        ob.tools_dir().mkdir(parents=True, exist_ok=True)
        self.v126_process.setWorkingDirectory(str(ob.tools_dir()))
        self.v126_process.start(program, args)

    def v126_stop_run(self):
        if self.v126_process.state() != QProcess.ProcessState.NotRunning:
            self.v126_status.setText("Arrêt du traitement demandé…")
            self.v126_process.terminate()

    def v126_finished(self, code, exit_status):
        v126_append_log(self)
        local_jobs.release(self.v126_resource_token)
        self.v126_resource_token = None
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if ok:
            self.v126_status.setText(
                "✅ Traitement terminé. Actualisation de la bibliothèque Obliteratus…"
            )
            try:
                self.reload_checkpoints()
            except Exception:
                pass
        else:
            self.v126_status.setText(
                f"❌ Traitement interrompu ou en échec (code {code}). Consultez le journal."
            )
        v126_set_busy(self, False)

    def v126_failed(self, _error):
        local_jobs.release(self.v126_resource_token)
        self.v126_resource_token = None
        self.v126_status.setText("Démarrage impossible : " + self.v126_process.errorString())
        v126_set_busy(self, False)

    def v126_select_source(self, model_id):
        source, known = huggingface_source(model_id)
        self.v126_selected_ollama = model_id
        self.v126_source.setText(source)
        if known:
            self.v126_status.setText(f"✅ « {model_id} » préparé pour Obliteratus : {source}")
        else:
            self.v126_status.setText(
                "Le nom Ollama n'a pas de correspondance Hugging Face automatique. "
                "La valeur a été préremplie : corrigez-la si nécessaire avant de lancer."
            )

    tab.v126_append_log = MethodType(v126_append_log, tab)
    tab.v126_set_busy = MethodType(v126_set_busy, tab)
    tab.v126_start = MethodType(v126_start, tab)
    tab.v126_stop_run = MethodType(v126_stop_run, tab)
    tab.v126_finished = MethodType(v126_finished, tab)
    tab.v126_failed = MethodType(v126_failed, tab)
    tab.v126_select_source = MethodType(v126_select_source, tab)

    tab.v126_process.readyReadStandardOutput.connect(tab.v126_append_log)
    tab.v126_process.finished.connect(tab.v126_finished)
    tab.v126_process.errorOccurred.connect(tab.v126_failed)
    tab.v126_run.clicked.connect(tab.v126_start)
    tab.v126_stop.clicked.connect(tab.v126_stop_run)

    def send_selected():
        model_id = models.current_id or ""
        if model_id:
            tab.v126_select_source(model_id)
            window.tabs.setCurrentWidget(tab)

    models.obliteratus_btn.clicked.connect(send_selected)
    models.update_buttons()

    old_shutdown = tab.shutdown

    def shutdown(self):
        if self.v126_process.state() != QProcess.ProcessState.NotRunning:
            self.v126_process.terminate()
            if not self.v126_process.waitForFinished(1500):
                self.v126_process.kill()
                self.v126_process.waitForFinished(1500)
        local_jobs.release(self.v126_resource_token)
        self.v126_resource_token = None
        old_shutdown()

    tab.shutdown = MethodType(shutdown, tab)
    window._v126_obliteratus = True
