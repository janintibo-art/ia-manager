"""Extension v136 : installation autonome d'Unsloth pour l'atelier Entraîner / Fusionner."""
import os
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from src.backend import settings
from src.backend import obliteratus as ob


def _root() -> Path:
    path = Path.home() / ".ia_manager" / "tools" / "unsloth"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _venv_python() -> Path:
    root = _root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _candidate_python(tab):
    values = [
        tab.python.text().strip() if hasattr(tab, "python") else "",
        str(settings.get("training_python") or ""),
        str(settings.get("obliteratus_python") or ""),
        ob.default_python(),
    ]
    for value in values:
        if not value:
            continue
        path = Path(value).expanduser()
        if path.is_file():
            return str(path)
    return ""


def install_v136(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(window, "_v136_unsloth", False):
        return

    box = QGroupBox("🦥 Unsloth autonome")
    layout = QVBoxLayout(box)

    hint = QLabel(
        "Installe Unsloth dans un environnement Python isolé, séparé de l’EXE IA Manager. "
        "L’atelier d’entraînement utilisera ensuite automatiquement ce moteur."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    form = QFormLayout()
    tab.v136_base_python = QLineEdit(_candidate_python(tab))
    tab.v136_base_python.setPlaceholderText("Python 3.10+ ou Python 3.13 recommandé")
    form.addRow("Python de base", tab.v136_base_python)
    layout.addLayout(form)

    row = QHBoxLayout()
    tab.v136_install = QPushButton("Installer / réparer Unsloth")
    row.addWidget(tab.v136_install)
    tab.v136_use = QPushButton("Utiliser cet environnement")
    row.addWidget(tab.v136_use)
    tab.v136_diag = QPushButton("Diagnostic Unsloth / CUDA")
    row.addWidget(tab.v136_diag)
    tab.v136_stop = QPushButton("■ Arrêter")
    row.addWidget(tab.v136_stop)
    row.addStretch()
    layout.addLayout(row)

    tab.v136_status = QLabel()
    tab.v136_status.setWordWrap(True)
    layout.addWidget(tab.v136_status)

    # Placement avant le sélecteur d'environnement manuel existant.
    tab.layout().insertWidget(3, box)

    tab.v136_process = QProcess(tab)
    tab.v136_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v136_process.readyReadStandardOutput.connect(lambda: tab.v136_read_output())
    tab.v136_process.finished.connect(lambda c, s: tab.v136_finished(c, s))
    tab.v136_process.errorOccurred.connect(lambda e: tab.v136_failed(e))
    tab.v136_queue = []
    tab.v136_mode = ""

    def v136_ready(self):
        py = _venv_python()
        if not py.is_file():
            return False
        # On ne charge pas torch dans l'UI ; la présence du venv suffit ici.
        return True

    def v136_refresh(self):
        if self.v136_ready():
            self.v136_status.setText(
                "✅ Environnement Unsloth présent : " + str(_venv_python())
            )
        else:
            self.v136_status.setText(
                "Unsloth n’est pas encore installé dans l’environnement isolé IA Manager."
            )
        self.v136_update_buttons()

    def v136_update_buttons(self):
        busy = self.v136_process.state() != QProcess.ProcessState.NotRunning
        self.v136_install.setEnabled(not busy)
        self.v136_use.setEnabled(not busy and self.v136_ready())
        self.v136_diag.setEnabled(not busy and self.v136_ready())
        self.v136_stop.setEnabled(busy)
        self.v136_base_python.setEnabled(not busy)

    def v136_start_queue(self, steps, mode):
        if self.v136_process.state() != QProcess.ProcessState.NotRunning:
            return
        self.v136_queue = list(steps)
        self.v136_mode = mode
        self.v136_update_buttons()
        self.v136_next()

    def v136_next(self):
        if not self.v136_queue:
            return
        program, args = self.v136_queue.pop(0)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        self.v136_process.setProcessEnvironment(env)
        self.v136_process.setWorkingDirectory(str(_root()))
        self.v136_process.start(program, args)

    def v136_install_unsloth(self):
        base = Path(self.v136_base_python.text().strip()).expanduser()
        if not base.is_file():
            self.v136_status.setText(
                "Choisissez un véritable exécutable Python. "
                "Sous Windows, Python 3.13 est recommandé par la documentation actuelle d’Unsloth."
            )
            return

        venv = _root() / ".venv"
        vp = _venv_python()

        # L'installation officielle Core actuelle utilise uv et
        # `uv pip install unsloth --torch-backend=auto`.
        steps = [
            (str(base), ["-c", "import sys; assert sys.version_info >= (3,10), 'Python 3.10 minimum'"]),
            (str(base), ["-m", "pip", "install", "--upgrade", "pip", "uv"]),
        ]

        if not vp.is_file():
            steps.append(
                (str(base), ["-m", "uv", "venv", str(venv), "--python", str(base)])
            )

        # Utilise l'interpréteur de base pour piloter uv, mais installe dans le venv cible.
        steps += [
            (
                str(base),
                [
                    "-m", "uv", "pip", "install",
                    "--python", str(vp),
                    "unsloth", "trl", "datasets", "psutil",
                    "--torch-backend=auto",
                ],
            ),
            (
                str(vp),
                [
                    "-c",
                    "import torch, unsloth, trl, datasets; "
                    "print('Unsloth OK'); "
                    "print('Torch', torch.__version__); "
                    "print('CUDA disponible', torch.cuda.is_available()); "
                    "print('GPU', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun')",
                ],
            ),
        ]

        self.log.clear()
        self.v136_status.setText(
            "Installation / réparation d’Unsloth en cours. "
            "Le téléchargement de PyTorch peut être volumineux."
        )
        self.v136_start_queue(steps, "install")

    def v136_use_env(self):
        py = _venv_python()
        if not py.is_file():
            self.v136_status.setText("L’environnement Unsloth n’est pas installé.")
            return
        self.python.setText(str(py))
        settings.set("training_python", str(py))
        self.v136_status.setText(
            "✅ L’atelier Entraîner / Fusionner utilise maintenant l’environnement Unsloth isolé."
        )

    def v136_diagnostic(self):
        py = _venv_python()
        if not py.is_file():
            return
        code = (
            "import sys, importlib.metadata as md; "
            "print('Python', sys.version); "
            "mods=['torch','unsloth','trl','datasets','bitsandbytes']; "
            "[print(m, md.version(m) if (lambda: True)() else '') for m in []]; "
            "import torch; "
            "print('Torch', torch.__version__); "
            "print('CUDA', torch.cuda.is_available()); "
            "print('GPU', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun'); "
            "print('VRAM Go', round(torch.cuda.get_device_properties(0).total_memory/2**30,1) if torch.cuda.is_available() else 0)"
        )
        self.log.clear()
        self.v136_status.setText("Diagnostic Unsloth / CUDA en cours…")
        self.v136_start_queue([(str(py), ["-c", code])], "diag")

    def v136_read_output(self):
        text = bytes(self.v136_process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)

    def v136_finished(self, code, exit_status):
        self.v136_read_output()
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if ok and self.v136_queue:
            self.v136_next()
            return

        mode = self.v136_mode
        self.v136_mode = ""
        self.v136_queue.clear()

        if ok and mode == "install":
            self.v136_use_env()
            self.v136_status.setText(
                "✅ Unsloth installé / réparé et sélectionné comme moteur d’entraînement."
            )
        elif ok and mode == "diag":
            self.v136_status.setText(
                "✅ Diagnostic terminé. Consultez le journal pour CUDA, GPU et versions."
            )
        elif not ok:
            self.v136_status.setText(
                f"❌ Échec Unsloth (code {code}). Consultez le journal."
            )

        self.v136_refresh()

    def v136_failed(self, _error):
        self.v136_queue.clear()
        self.v136_mode = ""
        self.v136_status.setText(
            "Démarrage impossible : " + self.v136_process.errorString()
        )
        self.v136_update_buttons()

    def v136_stop_run(self):
        self.v136_queue.clear()
        if self.v136_process.state() != QProcess.ProcessState.NotRunning:
            self.v136_process.terminate()
            self.v136_status.setText("Arrêt demandé…")

    tab.v136_ready = MethodType(v136_ready, tab)
    tab.v136_refresh = MethodType(v136_refresh, tab)
    tab.v136_update_buttons = MethodType(v136_update_buttons, tab)
    tab.v136_start_queue = MethodType(v136_start_queue, tab)
    tab.v136_next = MethodType(v136_next, tab)
    tab.v136_install_unsloth = MethodType(v136_install_unsloth, tab)
    tab.v136_use_env = MethodType(v136_use_env, tab)
    tab.v136_diagnostic = MethodType(v136_diagnostic, tab)
    tab.v136_read_output = MethodType(v136_read_output, tab)
    tab.v136_finished = MethodType(v136_finished, tab)
    tab.v136_failed = MethodType(v136_failed, tab)
    tab.v136_stop_run = MethodType(v136_stop_run, tab)

    tab.v136_install.clicked.connect(tab.v136_install_unsloth)
    tab.v136_use.clicked.connect(tab.v136_use_env)
    tab.v136_diag.clicked.connect(tab.v136_diagnostic)
    tab.v136_stop.clicked.connect(tab.v136_stop_run)

    old_shutdown = tab.shutdown

    def shutdown(self):
        if self.v136_process.state() != QProcess.ProcessState.NotRunning:
            self.v136_process.terminate()
            if not self.v136_process.waitForFinished(1500):
                self.v136_process.kill()
                self.v136_process.waitForFinished(1500)
        old_shutdown()

    tab.shutdown = MethodType(shutdown, tab)

    tab.v136_refresh()
    window._v136_unsloth = True
