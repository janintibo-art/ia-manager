"""Extension v133 : sortie MergeKit -> GGUF -> Ollama -> Chat."""
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from src.backend import local_jobs
from src.backend.ai_manager import AIManager
from src.backend import obliteratus_export as oe
from src.ui import v132_extension as mk


def install_v133(window):
    tab = getattr(window, "mergekit_tab", None)
    if tab is None or getattr(window, "_v133_mergekit", False):
        return

    box = QGroupBox("3 · Exporter la fusion vers Ollama")
    layout = QVBoxLayout(box)

    hint = QLabel(
        "Une fois la fusion terminée, IA Manager peut convertir le checkpoint Hugging Face "
        "en GGUF avec llama.cpp, puis créer automatiquement le modèle dans Ollama."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    form = QFormLayout()
    tab.v133_source = QLineEdit()
    tab.v133_source.setPlaceholderText("Dossier de la fusion MergeKit")
    form.addRow("Fusion source", tab.v133_source)

    tab.v133_name = QLineEdit("fusion-mergekit")
    tab.v133_name.setPlaceholderText("nom-ollama")
    form.addRow("Nom dans Ollama", tab.v133_name)
    layout.addLayout(form)

    row = QHBoxLayout()
    tab.v133_use_last = QPushButton("↙ Utiliser la dernière fusion")
    row.addWidget(tab.v133_use_last)

    tab.v133_convert = QPushButton("⚙ Convertir en GGUF + ajouter à Ollama")
    tab.v133_convert.setObjectName("Primary")
    row.addWidget(tab.v133_convert)

    tab.v133_stop = QPushButton("■ Arrêter")
    tab.v133_stop.setObjectName("Danger")
    row.addWidget(tab.v133_stop)

    tab.v133_chat = QPushButton("💬 Ouvrir dans Chat")
    tab.v133_chat.setEnabled(False)
    row.addWidget(tab.v133_chat)
    row.addStretch()
    layout.addLayout(row)

    tab.v133_status = QLabel(
        "Prêt · terminez d’abord une fusion MergeKit ou choisissez son dossier."
    )
    tab.v133_status.setWordWrap(True)
    layout.addWidget(tab.v133_status)

    # Avant le journal existant.
    root = tab.layout()
    insert_at = max(0, root.count() - 2)
    root.insertWidget(insert_at, box)

    tab.v133_process = QProcess(tab)
    tab.v133_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v133_process.readyReadStandardOutput.connect(
        lambda: tab.v133_read_output()
    )
    tab.v133_process.finished.connect(
        lambda code, status: tab.v133_finished(code, status)
    )
    tab.v133_process.errorOccurred.connect(
        lambda error: tab.v133_failed(error)
    )
    tab.v133_queue = []
    tab.v133_resource_token = None
    tab.v133_ready_name = ""

    def v133_set_busy(self, busy):
        self.v133_convert.setEnabled(not busy)
        self.v133_stop.setEnabled(busy)
        self.v133_source.setEnabled(not busy)
        self.v133_name.setEnabled(not busy)
        self.v133_use_last.setEnabled(not busy)
        self.v133_chat.setEnabled(not busy and bool(self.v133_ready_name))

        # Évite fusion + conversion simultanées.
        if hasattr(self, "run_btn"):
            self.run_btn.setEnabled(
                not busy and mk._mergekit_exe().is_file()
                and self.process.state() == QProcess.ProcessState.NotRunning
            )
        if hasattr(self, "install_btn"):
            self.install_btn.setEnabled(
                not busy and self.process.state() == QProcess.ProcessState.NotRunning
            )

    def v133_use_last(self):
        if self.last_output and Path(self.last_output).is_dir():
            self.v133_source.setText(self.last_output)
            name = Path(self.last_output).name.lower()
            self.v133_name.setText(mk._safe_name(name))
            self.v133_status.setText(
                "✅ Dernière fusion sélectionnée : " + self.last_output
            )
        else:
            self.v133_status.setText(
                "Aucune fusion terminée dans cette session. Indiquez le dossier manuellement."
            )

    def v133_start(self):
        if self.v133_process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.v133_status.setText(
                "Une fusion MergeKit est encore en cours. Attendez sa fin avant la conversion."
            )
            return

        source = Path(self.v133_source.text().strip()).expanduser()
        name = self.v133_name.text().strip().lower()

        if not source.is_dir():
            self.v133_status.setText("Le dossier de fusion sélectionné n’existe pas.")
            return
        if not oe.valid_checkpoint(source):
            self.v133_status.setText(
                "Ce dossier n’est pas un checkpoint Hugging Face complet "
                "(config, tokenizer et poids Safetensors requis)."
            )
            return
        if not mk._venv_python().is_file():
            self.v133_status.setText(
                "MergeKit doit être installé avant la conversion."
            )
            return

        try:
            steps = oe.make_steps(
                str(source),
                name,
                mk._venv_python(),
            )
        except Exception as exc:
            self.v133_status.setText(str(exc))
            return

        if local_jobs.enabled():
            self.v133_resource_token = local_jobs.reserve("Export MergeKit vers Ollama")
            if self.v133_resource_token is None:
                self.v133_status.setText(
                    "Un autre travail local utilise déjà les ressources. Attendez sa fin."
                )
                return

        self.v133_queue = list(steps)
        self.v133_ready_name = ""
        self.v133_chat.setEnabled(False)
        self.log.clear()
        self.v133_status.setText(
            "Conversion GGUF puis import Ollama en cours · progression dans le journal."
        )
        self.v133_set_busy(True)
        self.v133_next_step()

    def v133_next_step(self):
        if not self.v133_queue:
            return
        program, args = self.v133_queue.pop(0)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        self.v133_process.setProcessEnvironment(env)

        # llama.cpp doit être exécuté depuis son dossier lors de la conversion.
        work = mk._tool_root()
        try:
            if any("convert_hf_to_gguf.py" in str(arg) for arg in args):
                from src.backend import storage
                llama = storage.conversions() / "llama.cpp-master"
                if llama.is_dir():
                    work = llama
        except Exception:
            pass

        self.v133_process.setWorkingDirectory(str(work))
        self.v133_process.start(program, args)

    def v133_read_output(self):
        text = bytes(self.v133_process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)

    def v133_finished(self, code, exit_status):
        self.v133_read_output()
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit

        if ok and self.v133_queue:
            self.v133_next_step()
            return

        local_jobs.release(self.v133_resource_token)
        self.v133_resource_token = None

        if ok:
            self.v133_ready_name = self.v133_name.text().strip().lower()
            AIManager.invalidate_model_cache()
            self.v133_status.setText(
                f"✅ « {self.v133_ready_name} » ajouté à Ollama. "
                "Vous pouvez maintenant l’ouvrir dans le Chat."
            )
        else:
            self.v133_status.setText(
                f"❌ Conversion/import interrompu ou en échec (code {code}). "
                "Consultez le journal."
            )

        self.v133_queue.clear()
        self.v133_set_busy(False)

    def v133_failed(self, _error):
        local_jobs.release(self.v133_resource_token)
        self.v133_resource_token = None
        self.v133_queue.clear()
        self.v133_status.setText(
            "Démarrage impossible : " + self.v133_process.errorString()
        )
        self.v133_set_busy(False)

    def v133_stop_run(self):
        self.v133_queue.clear()
        if self.v133_process.state() != QProcess.ProcessState.NotRunning:
            self.v133_process.terminate()
            self.v133_status.setText("Arrêt demandé…")

    def v133_open_chat(self):
        name = self.v133_ready_name
        if not name:
            return
        chat = getattr(window, "chat_tab", None)
        if chat is None:
            return
        chat.refresh_models()
        if chat.select_ref(name):
            window.tabs.setCurrentWidget(chat)
            self.v133_status.setText(
                f"✅ Modèle « {name} » ouvert dans le Chat."
            )
        else:
            self.v133_status.setText(
                f"Le modèle « {name} » n’apparaît pas encore dans Ollama. "
                "Actualisez les modèles puis réessayez."
            )

    tab.v133_set_busy = MethodType(v133_set_busy, tab)
    tab.v133_use_last_merge = MethodType(v133_use_last, tab)
    tab.v133_start = MethodType(v133_start, tab)
    tab.v133_next_step = MethodType(v133_next_step, tab)
    tab.v133_read_output = MethodType(v133_read_output, tab)
    tab.v133_finished = MethodType(v133_finished, tab)
    tab.v133_failed = MethodType(v133_failed, tab)
    tab.v133_stop_run = MethodType(v133_stop_run, tab)
    tab.v133_open_chat = MethodType(v133_open_chat, tab)

    tab.v133_use_last.clicked.connect(tab.v133_use_last_merge)
    tab.v133_convert.clicked.connect(tab.v133_start)
    tab.v133_stop.clicked.connect(tab.v133_stop_run)
    tab.v133_chat.clicked.connect(tab.v133_open_chat)

    # Après une fusion réussie, préremplir automatiquement la section d’export.
    old_finished = tab.finished

    def finished(self, code, exit_status):
        mode_before = self.mode
        old_finished(code, exit_status)
        if (
            code == 0
            and mode_before == "merge"
            and self.last_output
            and Path(self.last_output).is_dir()
        ):
            self.v133_source.setText(self.last_output)
            name = mk._safe_name(Path(self.last_output).name.lower())
            self.v133_name.setText(name)
            self.v133_status.setText(
                "✅ Fusion terminée et prête à être convertie en GGUF / Ollama."
            )

    tab.finished = MethodType(finished, tab)
    try:
        tab.process.finished.disconnect()
    except (TypeError, RuntimeError):
        pass
    tab.process.finished.connect(tab.finished)

    old_shutdown = tab.shutdown

    def shutdown(self):
        self.v133_queue.clear()
        local_jobs.release(self.v133_resource_token)
        self.v133_resource_token = None
        if self.v133_process.state() != QProcess.ProcessState.NotRunning:
            self.v133_process.terminate()
            if not self.v133_process.waitForFinished(1500):
                self.v133_process.kill()
                self.v133_process.waitForFinished(1500)
        old_shutdown()

    tab.shutdown = MethodType(shutdown, tab)

    tab.v133_set_busy(False)
    window._v133_mergekit = True
