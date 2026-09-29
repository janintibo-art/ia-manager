"""Extension v142 : intégration native de Heretic dans IA Manager."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.backend import local_jobs, settings, storage
from src.backend import obliteratus as ob
from src.backend import obliteratus_export as oe


HERETIC_REV = "3521f8648a0dccf6e12a92666862632235fac7e6"
HERETIC_ARCHIVE = (
    "https://github.com/p-e-w/heretic/archive/" + HERETIC_REV + ".zip"
)


def _tool_root():
    path = Path.home() / ".ia_manager" / "tools" / "heretic"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _venv_python():
    root = _tool_root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _heretic_exe():
    root = _tool_root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "heretic.exe"
    return root / "bin" / "heretic"


def _default_python():
    for value in (
        settings.get("training_python"),
        settings.get("obliteratus_python"),
        ob.default_python(),
    ):
        if not value:
            continue
        path = Path(str(value)).expanduser()
        if path.is_file():
            return str(path)
    return ""


def _safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    value = value.strip(".-")
    return value[:96] or "modele-heretic"


def _registry_file():
    path = Path.home() / ".ia_manager" / "heretic_versions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_registry():
    try:
        value = json.loads(_registry_file().read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save_registry(rows):
    _registry_file().write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class HereticTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.queue = []
        self.mode = ""
        self.token = None
        self.last_output = ""
        self.last_export = ""
        self.build_ui()
        self.refresh_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🔥 Heretic · chirurgie automatique des poids")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Heretic automatise une variante d’abliteration directionnelle et optimise "
            "ses paramètres avec Optuna. IA Manager l’exécute dans un environnement Python "
            "isolé. Conservez toujours le modèle original pour pouvoir comparer."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        install_box = QGroupBox("1 · Moteur Heretic")
        il = QVBoxLayout(install_box)
        form = QFormLayout()
        self.python = QLineEdit(_default_python())
        self.python.setPlaceholderText("Python 3.10 à 3.12 recommandé")
        form.addRow("Python de base", self.python)
        il.addLayout(form)

        row = QHBoxLayout()
        self.install_btn = QPushButton("Installer / réparer Heretic")
        row.addWidget(self.install_btn)
        self.diag_btn = QPushButton("Diagnostic")
        row.addWidget(self.diag_btn)
        self.open_tool_btn = QPushButton("📁 Dossier moteur")
        row.addWidget(self.open_tool_btn)
        row.addStretch()
        il.addLayout(row)

        self.engine_status = QLabel()
        self.engine_status.setWordWrap(True)
        il.addWidget(self.engine_status)
        root.addWidget(install_box)

        source_box = QGroupBox("2 · Modèle source")
        sl = QVBoxLayout(source_box)
        form = QFormLayout()
        self.model = QLineEdit()
        self.model.setPlaceholderText(
            "Identifiant Hugging Face ou dossier local, ex. Qwen/Qwen3-4B-Instruct-2507"
        )
        form.addRow("Modèle", self.model)
        sl.addLayout(form)

        row = QHBoxLayout()
        self.pick_model = QPushButton("Dossier local…")
        row.addWidget(self.pick_model)
        row.addStretch()
        sl.addLayout(row)
        root.addWidget(source_box)

        settings_box = QGroupBox("3 · Réglages guidés")
        gl = QVBoxLayout(settings_box)
        form = QFormLayout()

        self.profile = QComboBox()
        self.profile.addItem("Rapide · 20 essais", 20)
        self.profile.addItem("Équilibré · 60 essais", 60)
        self.profile.addItem("Approfondi · 200 essais", 200)
        self.profile.addItem("Personnalisé", -1)
        self.profile.setCurrentIndex(1)
        form.addRow("Profil", self.profile)

        self.trials = QSpinBox()
        self.trials.setRange(5, 1000)
        self.trials.setValue(60)
        form.addRow("Essais Optuna", self.trials)

        self.seed = QSpinBox()
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(42)
        form.addRow("Seed", self.seed)

        self.quant = QCheckBox("Quantification bitsandbytes 4 bits")
        self.quant.setChecked(True)
        form.addRow(self.quant)

        self.export = QComboBox()
        self.export.addItem("Adaptateur LoRA · plus léger", "adapter")
        self.export.addItem("Modèle fusionné · pour GGUF / Ollama", "merge")
        form.addRow("Sortie", self.export)

        self.checkpoint = QComboBox()
        self.checkpoint.addItem("Recommencer depuis zéro", "restart")
        self.checkpoint.addItem("Reprendre un calcul interrompu", "continue")
        form.addRow("Checkpoint", self.checkpoint)

        self.output_name = QLineEdit("modele-heretic")
        form.addRow("Nom de sortie", self.output_name)

        gl.addLayout(form)

        note = QLabel(
            "Le profil Équilibré est un bon point de départ. Le mode 4 bits réduit fortement "
            "la VRAM nécessaire. Un export fusionné peut demander beaucoup plus de RAM que "
            "l’optimisation elle-même."
        )
        note.setWordWrap(True)
        gl.addWidget(note)
        root.addWidget(settings_box)

        actions = QHBoxLayout()
        self.run_btn = QPushButton("▶ Lancer Heretic")
        self.run_btn.setObjectName("Primary")
        actions.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ Arrêter")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        actions.addWidget(self.stop_btn)

        self.open_output_btn = QPushButton("📁 Ouvrir la sortie")
        self.open_output_btn.setEnabled(False)
        actions.addWidget(self.open_output_btn)

        self.pipeline_btn = QPushButton("➡ GGUF / Ollama")
        self.pipeline_btn.setEnabled(False)
        actions.addWidget(self.pipeline_btn)

        actions.addStretch()
        root.addLayout(actions)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        root.addWidget(self.log, 1)

        self.install_btn.clicked.connect(self.install_heretic)
        self.diag_btn.clicked.connect(self.diagnostic)
        self.open_tool_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(_tool_root())))
        )
        self.pick_model.clicked.connect(self.choose_model)
        self.profile.currentIndexChanged.connect(self.apply_profile)
        self.run_btn.clicked.connect(self.run_heretic)
        self.stop_btn.clicked.connect(self.stop)
        self.open_output_btn.clicked.connect(self.open_output)
        self.pipeline_btn.clicked.connect(self.send_to_pipeline)

    def refresh_state(self):
        ready = _venv_python().is_file() and _heretic_exe().is_file()
        if ready:
            self.engine_status.setText(
                "✅ Heretic installé dans : " + str(_tool_root() / ".venv")
            )
        else:
            self.engine_status.setText(
                "Heretic n’est pas encore installé dans l’environnement isolé IA Manager."
            )
        self.diag_btn.setEnabled(ready and not self.busy())
        self.run_btn.setEnabled(ready and not self.busy())

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def set_busy(self, busy):
        for widget in (
            self.install_btn, self.diag_btn, self.python, self.model,
            self.pick_model, self.profile, self.trials, self.seed, self.quant,
            self.export, self.checkpoint, self.output_name,
        ):
            widget.setEnabled(not busy)
        self.run_btn.setEnabled(not busy and _heretic_exe().is_file())
        self.stop_btn.setEnabled(busy)
        self.open_output_btn.setEnabled(
            not busy and bool(self.last_output) and Path(self.last_output).exists()
        )
        self.pipeline_btn.setEnabled(
            not busy
            and self.last_export == "merge"
            and bool(self.last_output)
            and oe.valid_checkpoint(Path(self.last_output))
        )

    def apply_profile(self):
        value = self.profile.currentData()
        if value != -1:
            self.trials.setValue(int(value))

    def choose_model(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir un modèle local")
        if path:
            self.model.setText(path)
            if not self.output_name.text().strip() or self.output_name.text() == "modele-heretic":
                self.output_name.setText(_safe_name(Path(path).name + "-heretic"))

    def start_queue(self, steps, mode):
        if self.busy():
            return
        self.queue = list(steps)
        self.mode = mode
        self.set_busy(True)
        self.next_step()

    def next_step(self):
        if not self.queue:
            return
        program, args = self.queue.pop(0)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        env.insert("PYTORCH_ALLOC_CONF", "expandable_segments:True")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(_tool_root()))
        self.process.start(str(program), list(args))

    def install_heretic(self):
        base = Path(self.python.text().strip()).expanduser()
        if not base.is_file():
            self.status.setText("Choisissez un véritable exécutable Python 3.10+.")
            return

        vp = _venv_python()
        venv = _tool_root() / ".venv"
        steps = [
            (
                str(base),
                ["-c", "import sys; assert sys.version_info >= (3,10), 'Python 3.10 minimum'"],
            ),
        ]
        if not vp.is_file():
            steps.append((str(base), ["-m", "venv", str(venv)]))

        steps += [
            (str(vp), ["-m", "pip", "install", "--upgrade", "pip", "wheel"]),
            (str(vp), ["-m", "pip", "install", "--upgrade", HERETIC_ARCHIVE]),
            (
                str(vp),
                [
                    "-c",
                    "import torch, heretic, importlib.metadata as md; "
                    "print('Heretic', md.version('heretic-llm')); "
                    "print('Torch', torch.__version__); "
                    "print('CUDA', torch.cuda.is_available()); "
                    "print('GPU', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun')",
                ],
            ),
        ]

        self.log.clear()
        self.status.setText(
            "Installation / réparation de Heretic en cours. PyTorch et les dépendances ML "
            "peuvent représenter un téléchargement important."
        )
        self.start_queue(steps, "install")

    def diagnostic(self):
        if not _venv_python().is_file():
            return
        code = (
            "import torch, importlib.metadata as md, psutil; "
            "print('Heretic', md.version('heretic-llm')); "
            "print('Torch', torch.__version__); "
            "print('CUDA', torch.cuda.is_available()); "
            "print('GPU', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun'); "
            "print('VRAM Go', round(torch.cuda.get_device_properties(0).total_memory/2**30,1) if torch.cuda.is_available() else 0); "
            "print('RAM Go', round(psutil.virtual_memory().total/2**30,1))"
        )
        self.log.clear()
        self.status.setText("Diagnostic Heretic / CUDA en cours…")
        self.start_queue([(str(_venv_python()), ["-c", code])], "diag")

    def run_heretic(self):
        model = self.model.text().strip()
        if not model:
            self.status.setText("Indiquez un modèle Hugging Face ou un dossier local.")
            return
        if not _heretic_exe().is_file():
            self.status.setText("Installez d’abord Heretic.")
            return

        name = _safe_name(self.output_name.text())
        output = storage.app_models() / "Heretic" / name
        export_strategy = self.export.currentData()

        if output.exists() and any(output.iterdir()) and self.checkpoint.currentData() == "restart":
            self.status.setText(
                "Le dossier de sortie existe déjà et n’est pas vide. Changez le nom de sortie "
                "ou choisissez une reprise."
            )
            return

        output.mkdir(parents=True, exist_ok=True)

        trials = int(self.trials.value())
        startup = min(max(4, trials // 3), max(4, trials - 1))

        args = [
            "--model", model,
            "--n-trials", str(trials),
            "--n-startup-trials", str(startup),
            "--seed", str(self.seed.value()),
            "--checkpoint-action", self.checkpoint.currentData(),
            "--trial-index", "0",
            "--model-action", "save",
            "--save-directory", str(output),
            "--export-strategy", export_strategy,
        ]
        if self.quant.isChecked():
            args += ["--quantization", "bnb_4bit"]
        else:
            args += ["--quantization", "none"]

        if local_jobs.enabled():
            self.token = local_jobs.reserve("Heretic")
            if self.token is None:
                self.status.setText(
                    "Un autre travail local utilise déjà les ressources. Attendez sa fin."
                )
                return

        self.last_output = str(output)
        self.last_export = str(export_strategy)
        self.log.clear()
        self.status.setText(
            f"Heretic en cours · {trials} essais · sortie {export_strategy}. "
            "Le premier chargement du modèle peut être long."
        )
        self.start_queue([(str(_heretic_exe()), args)], "run")

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )

    def finished(self, code, status):
        self.read_output()
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit

        if ok and self.queue:
            self.next_step()
            return

        mode = self.mode
        self.mode = ""
        self.queue.clear()

        if mode == "run":
            local_jobs.release(self.token)
            self.token = None

        if ok and mode == "install":
            self.status.setText("✅ Heretic installé / réparé.")
        elif ok and mode == "diag":
            self.status.setText("✅ Diagnostic terminé. Consultez le journal.")
        elif ok and mode == "run":
            self.status.setText(
                "✅ Heretic terminé · sortie : " + self.last_output
            )
            self.register_version()
        elif not ok:
            self.status.setText(
                f"❌ Heretic interrompu ou en échec (code {code}). Consultez le journal."
            )

        self.refresh_state()
        self.set_busy(False)

    def failed(self, _error):
        self.queue.clear()
        if self.mode == "run":
            local_jobs.release(self.token)
            self.token = None
        self.mode = ""
        self.status.setText(
            "Démarrage impossible : " + self.process.errorString()
        )
        self.refresh_state()
        self.set_busy(False)

    def stop(self):
        self.queue.clear()
        if self.busy():
            self.process.terminate()
            self.status.setText("Arrêt demandé…")

    def open_output(self):
        if self.last_output and Path(self.last_output).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output))

    def register_version(self):
        rows = _load_registry()
        item = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "source_model": self.model.text().strip(),
            "output": self.last_output,
            "export_strategy": self.last_export,
            "quantization": "bnb_4bit" if self.quant.isChecked() else "none",
            "n_trials": self.trials.value(),
            "seed": self.seed.value(),
        }
        rows.append(item)
        _save_registry(rows[-200:])

    def send_to_pipeline(self):
        if self.last_export != "merge":
            self.status.setText(
                "Le pipeline GGUF/Ollama nécessite un modèle fusionné, pas seulement l’adaptateur."
            )
            return
        output = Path(self.last_output)
        if not oe.valid_checkpoint(output):
            self.status.setText(
                "La sortie ne ressemble pas encore à un checkpoint Hugging Face complet."
            )
            return

        mergekit = getattr(self.window, "mergekit_tab", None)
        if mergekit is None or not hasattr(mergekit, "v133_source"):
            self.status.setText("Pipeline GGUF/Ollama indisponible.")
            return

        mergekit.v133_source.setText(str(output))
        mergekit.v133_name.setText(_safe_name(output.name.lower()))
        mergekit.v133_status.setText(
            "✅ Sortie Heretic prête pour conversion GGUF / Ollama."
        )
        self.window.tabs.setCurrentWidget(mergekit)

    def shutdown(self):
        self.queue.clear()
        local_jobs.release(self.token)
        self.token = None
        if self.busy():
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)


def install_v142(window):
    if getattr(window, "_v142_heretic", False):
        return

    tab = HereticTab(window)
    window.heretic_tab = tab

    obl = getattr(window, "obliteratus_tab", None)
    idx = window.tabs.indexOf(obl)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "🔥 Heretic")

    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(tab.shutdown)
    except Exception:
        pass

    window._v142_heretic = True
