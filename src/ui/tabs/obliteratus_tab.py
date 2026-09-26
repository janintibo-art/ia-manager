"""Installation isolée et lancement de l'interface officielle Obliteratus."""
from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)
from src.backend import obliteratus as ob, settings


class ObliteratusTab(QWidget):
    def __init__(self):
        super().__init__()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.queue = []
        self.mode = ""
        self.cancelled = False
        self.active_port = 7860
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self.process.kill)
        root = QVBoxLayout(self)
        intro = QLabel(
            "Obliteratus — atelier de modèles locaux\n"
            "Analyse et modification des modèles Hugging Face, comparaison avant/après et export.\n"
            "Le mode local s'installe séparément : Python 3.10+ requis, téléchargements volumineux, "
            "mémoire et GPU adaptés au modèle. Android/Termux n'est pas un environnement pris en charge.\n"
            "La version web s'ouvre dans votre navigateur et utilise un service externe.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        links = QHBoxLayout()
        for label, url in (("Ouvrir la version web", ob.SPACE_URL),
                           ("Documentation officielle", ob.UPSTREAM + "#ways-to-use-obliteratus")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, target=url: QDesktopServices.openUrl(QUrl(target)))
            links.addWidget(button)
        root.addLayout(links)
        form = QFormLayout()
        self.python = QLineEdit(settings.get("obliteratus_python") or ob.default_python())
        row = QHBoxLayout()
        row.addWidget(self.python)
        self.browse = QPushButton("Choisir Python…")
        self.browse.clicked.connect(self.choose_python)
        row.addWidget(self.browse)
        form.addRow("Python du PC", row)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        try:
            self.port.setValue(int(settings.get("obliteratus_port") or 7860))
        except (TypeError, ValueError):
            self.port.setValue(7860)
        form.addRow("Port local", self.port)
        root.addLayout(form)
        note = QLabel(
            "Installer télécharge Obliteratus et ses dépendances dans un environnement dédié. "
            "Le Python choisi sert uniquement à créer cet environnement. "
            "Le serveur local écoute sur ce PC ; la télémétrie est désactivée pour ce lancement. "
            "Les modèles GGUF/Ollama ne se modifient pas directement ici : "
            "l'export et sa conversion éventuelle restent à effectuer dans les outils adaptés.")
        note.setWordWrap(True)
        root.addWidget(note)
        actions = QHBoxLayout()
        self.install = QPushButton("Installer / réparer")
        self.install.clicked.connect(self.install_local)
        self.start = QPushButton("Lancer en local")
        self.start.clicked.connect(self.launch)
        self.open = QPushButton("Ouvrir l'interface locale")
        self.open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ob.local_url(self.active_port))))
        self.stop = QPushButton("Arrêter")
        self.stop.clicked.connect(self.stop_process)
        for button in (self.install, self.start, self.open, self.stop):
            actions.addWidget(button)
        root.addLayout(actions)
        self.status = QLabel("Version locale indépendante · installation nécessaire avant le premier lancement.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        root.addWidget(self.log)
        self.update_buttons()

    def choose_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir python.exe ou python3")
        if path:
            self.python.setText(path)

    def update_buttons(self):
        busy = bool(self.mode)
        for widget in (self.install, self.python, self.browse, self.port):
            widget.setEnabled(not busy)
        self.start.setEnabled(not busy and ob.environment_python().is_file())
        self.stop.setEnabled(busy)
        self.open.setEnabled(self.mode == "server" and not self.cancelled)

    def run_steps(self, steps, mode):
        if self.mode:
            return
        self.queue = list(steps)
        self.mode = mode
        self.cancelled = False
        self.log.clear()
        self.update_buttons()
        self.next_step()

    def next_step(self):
        program, args = self.queue.pop(0)
        ob.tools_dir().mkdir(parents=True, exist_ok=True)
        self.process.setWorkingDirectory(str(ob.tools_dir()))
        env = QProcessEnvironment.systemEnvironment()
        for key, value in {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",
                           "OBLITERATUS_TELEMETRY": "0", "GRADIO_ANALYTICS_ENABLED": "False"}.items():
            env.insert(key, value)
        self.process.setProcessEnvironment(env)
        self.process.start(program, args)

    def install_local(self):
        try:
            steps = ob.install_steps(self.python.text().strip())
            settings.set("obliteratus_python", self.python.text().strip())
            self.status.setText("Installation en cours · les dépendances peuvent prendre plusieurs minutes.")
            self.run_steps(steps, "install")
        except Exception as error:
            self.status.setText(str(error))

    def launch(self):
        try:
            self.active_port = self.port.value()
            settings.set("obliteratus_port", self.active_port)
            self.status.setText("Démarrage local · attendez l'adresse du serveur dans le journal avant d'ouvrir l'interface.")
            self.run_steps([ob.launch_command(self.active_port)], "server")
        except Exception as error:
            self.status.setText(str(error))

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)

    def finished(self, code, exit_status):
        self.kill_timer.stop()
        self.read_output()
        if not self.cancelled and code == 0 and exit_status == QProcess.ExitStatus.NormalExit and self.queue:
            self.next_step()
            return
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if self.cancelled:
            message = "Arrêt demandé. Si l'installation a été interrompue, cliquez sur Installer / réparer."
        elif not ok:
            message = f"Échec (code {code}) · consultez le journal ci-dessous."
        elif self.mode == "install":
            message = "Installation terminée. Vous pouvez lancer Obliteratus en local."
        else:
            message = "Serveur local arrêté."
        self.queue.clear()
        self.mode = ""
        self.status.setText(message)
        self.update_buttons()

    def failed(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.queue.clear()
            self.mode = ""
            self.status.setText("Démarrage impossible : " + self.process.errorString())
            self.update_buttons()

    def stop_process(self):
        self.cancelled = True
        self.queue.clear()
        self.process.terminate()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.kill_timer.start(3000)
        self.update_buttons()

    def shutdown(self):
        self.queue.clear()
        self.cancelled = True
        self.kill_timer.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)
