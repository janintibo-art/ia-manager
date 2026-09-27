"""Installation isolée et lancement de l'interface officielle Obliteratus."""
from pathlib import Path
from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QComboBox, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from src.backend import obliteratus as ob, settings, local_jobs
from src.backend import python_detection as pd
from src.backend import obliteratus_export as oe


class ObliteratusTab(QWidget):
    open_model_chat = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.resource_token = None
        self.queue = []
        self.mode = ""
        self.cancelled = False
        self.chat_ready_name = ""
        self.active_port = 7860
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self.process.kill)
        self.detecting = False
        self.install_after_detection = False
        self.probe = QProcess(self)
        self.probe.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.probe.finished.connect(self.probe_finished)
        self.probe.errorOccurred.connect(self.probe_failed)
        self.probe_timer = QTimer(self)
        self.probe_timer.setSingleShot(True)
        self.probe_timer.timeout.connect(self.probe.kill)
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
        title = QLabel("1 · Vérifier Python")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-top: 12px;")
        root.addWidget(title)
        help_text = QLabel("Cliquez sur Détecter Python : la commande est intégrée à l’application. "
                           "Le bon chemin sera renseigné automatiquement, sans ouvrir de terminal.")
        help_text.setWordWrap(True)
        root.addWidget(help_text)
        form = QFormLayout()
        self.python = QLineEdit(settings.get("obliteratus_python") or ob.default_python())
        row = QHBoxLayout()
        row.addWidget(self.python)
        self.browse = QPushButton("Choisir Python…")
        self.browse.clicked.connect(self.choose_python)
        row.addWidget(self.browse)
        form.addRow("Python du PC", row)
        self.detect = QPushButton("Détecter Python automatiquement")
        self.detect.clicked.connect(lambda: self.detect_python(False))
        form.addRow(self.detect)
        self.python_hint = QLabel("Python non vérifié · utilisez la détection avant l’installation.")
        self.python_hint.setWordWrap(True)
        form.addRow(self.python_hint)
        get_python = QPushButton("Télécharger Python — site officiel")
        get_python.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.python.org/downloads/windows/")))
        form.addRow(get_python)
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
            "utilisez la section Ajouter à mes IA pour convertir un checkpoint sauvegardé et l’importer dans Ollama.")
        note.setWordWrap(True)
        root.addWidget(note)
        title = QLabel("2 · Installer, puis lancer l’atelier")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-top: 12px;")
        root.addWidget(title)
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
        library_group = QGroupBox("3 · Mes modèles créés avec Obliteratus")
        library_layout = QVBoxLayout(library_group)
        library_hint = QLabel("Retrouvez vos sauvegardes et conversions GGUF. Sélectionnez un modèle pour préparer son ajout à Ollama.")
        library_hint.setWordWrap(True)
        library_layout.addWidget(library_hint)
        self.library_table = QTableWidget(0, 4)
        self.library_table.setHorizontalHeaderLabels(["Traitement", "Famille", "Poids", "GGUF disponible"])
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.library_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.library_table.verticalHeader().hide()
        self.library_table.horizontalHeader().setStretchLastSection(True)
        self.library_table.setMinimumHeight(150)
        self.library_table.itemSelectionChanged.connect(self.select_library_model)
        library_layout.addWidget(self.library_table)
        library_buttons = QHBoxLayout()
        self.library_refresh = QPushButton("Actualiser la bibliothèque")
        self.library_refresh.clicked.connect(self.reload_checkpoints)
        library_buttons.addWidget(self.library_refresh)
        self.library_open = QPushButton("Ouvrir le dossier du modèle")
        self.library_open.clicked.connect(self.open_library_model)
        library_buttons.addWidget(self.library_open)
        library_layout.addLayout(library_buttons)
        root.addWidget(library_group)
        export_group = QGroupBox("4 · Ajouter un modèle Obliteratus à mes IA")
        export_layout = QVBoxLayout(export_group)
        explanation = QLabel("Après la fin du traitement, arrêtez l’atelier avec Arrêter, puis actualisez les sauvegardes. "
                             "La conversion GGUF et l’import Ollama sont automatiques. "
                             "Premier usage : téléchargement des outils ; prévoir plusieurs Go libres.")
        explanation.setWordWrap(True)
        export_layout.addWidget(explanation)
        export_row = QHBoxLayout()
        self.checkpoints = QComboBox()
        self.checkpoints.setMinimumContentsLength(22)
        self.checkpoints.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        export_row.addWidget(self.checkpoints, 1)
        self.refresh_exports = QPushButton("Actualiser")
        self.refresh_exports.clicked.connect(self.reload_checkpoints)
        export_row.addWidget(self.refresh_exports)
        self.browse_export = QPushButton("Autre dossier…")
        self.browse_export.clicked.connect(self.choose_checkpoint)
        export_row.addWidget(self.browse_export)
        export_layout.addLayout(export_row)
        export_row = QHBoxLayout()
        self.export_name = QLineEdit("tinyllama-obliteratus")
        self.export_name.setPlaceholderText("Nom dans Ollama")
        export_row.addWidget(QLabel("Nom dans mes IA"))
        export_row.addWidget(self.export_name, 1)
        self.export_button = QPushButton("Convertir et ajouter à mes IA")
        self.export_button.clicked.connect(self.export_checkpoint)
        export_row.addWidget(self.export_button)
        export_layout.addLayout(export_row)
        self.chat_button = QPushButton("Discuter avec ce modèle dans Chat")
        self.chat_button.setEnabled(False)
        self.chat_button.clicked.connect(lambda: self.open_model_chat.emit(self.chat_ready_name))
        self.export_name.textChanged.connect(self.update_buttons)
        export_layout.addWidget(self.chat_button)
        root.addWidget(export_group)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        root.addWidget(QLabel("5 · Journal et diagnostic"))
        root.addWidget(self.log)
        self.reload_checkpoints()
        self.update_buttons()

    def reload_checkpoints(self):
        current = self.checkpoints.currentData()
        self.checkpoints.clear()
        try:
            models = oe.model_library()
            self.library_table.setRowCount(0)
            for model in models:
                path = model['path']
                self.checkpoints.addItem(model['run'], path)
                row = self.library_table.rowCount()
                self.library_table.insertRow(row)
                exports = model['exports']
                values = (model['run'], model['family'],
                          f"{model['size'] / (1024 ** 3):.2f} Go",
                          ', '.join(item['name'] for item in exports) if exports else 'À convertir')
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    self.library_table.setItem(row, col, item)
            self.library_table.resizeColumnsToContents()
        except OSError as error:
            self.status.setText("Lecture des sauvegardes impossible : " + str(error))
        index = self.checkpoints.findData(current)
        if index >= 0:
            self.checkpoints.setCurrentIndex(index)
        self.update_buttons()

    def select_library_model(self):
        row = self.library_table.currentRow()
        if row < 0 or not self.library_table.item(row, 0):
            return
        path = self.library_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        index = self.checkpoints.findData(path)
        if index >= 0:
            self.checkpoints.setCurrentIndex(index)
            self.export_name.setText('obliteratus-' + self.library_table.item(row, 0).text()[-12:].lower())
            self.chat_ready_name = ""
            self.chat_button.setEnabled(False)

    def open_library_model(self):
        row = self.library_table.currentRow()
        if row >= 0 and self.library_table.item(row, 0):
            QDesktopServices.openUrl(QUrl.fromLocalFile(
                self.library_table.item(row, 0).data(Qt.ItemDataRole.UserRole)))

    def choose_checkpoint(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier checkpoint contenant les Safetensors")
        if path:
            if not oe.valid_checkpoint(path):
                self.status.setText("Ce dossier ne contient pas un checkpoint Safetensors complet.")
                return
            self.checkpoints.addItem(path, path)
            self.checkpoints.setCurrentIndex(self.checkpoints.count() - 1)
            self.update_buttons()

    def export_checkpoint(self):
        if self.mode or self.detecting:
            return
        name = self.export_name.text().strip()
        answer = QMessageBox.question(self, "Ajouter à Ollama", "Importer sous le nom « " + name +
            " » ? Si ce nom existe déjà dans Ollama, il sera remplacé. "
            "Choisissez un autre nom pour conserver les deux versions.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.chat_ready_name = ""
            self.chat_button.setEnabled(False)
            steps = oe.make_steps(self.checkpoints.currentData() or "", name, ob.environment_python())
            self.status.setText("Conversion puis import en cours · progression dans le journal.")
            self.run_steps(steps, "export")
        except Exception as error:
            self.status.setText(str(error))

    def choose_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir python.exe ou python3")
        if path:
            self.python.setText(path)

    def update_buttons(self):
        busy = bool(self.mode) or self.detecting
        for widget in (self.install, self.python, self.browse, self.port, self.detect):
            widget.setEnabled(not busy)
        self.start.setEnabled(not busy and ob.environment_python().is_file())
        self.stop.setEnabled(busy)
        self.open.setEnabled(self.mode == "server" and not self.cancelled)
        for widget in (self.checkpoints, self.refresh_exports, self.browse_export, self.export_name,
                       self.library_refresh, self.library_table, self.library_open):
            widget.setEnabled(not busy)
        self.export_button.setEnabled(not busy and self.checkpoints.count() > 0 and ob.environment_python().is_file())
        self.chat_button.setEnabled(not busy and bool(self.chat_ready_name)
                                    and self.export_name.text().strip() == self.chat_ready_name)

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
        if self.mode == "export":
            source = Path.home() / "ia-conversion/llama.cpp-master"
            if source.is_dir():
                self.process.setWorkingDirectory(str(source))
        env = QProcessEnvironment.systemEnvironment()
        for key, value in {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",
                           "OBLITERATUS_TELEMETRY": "0", "GRADIO_ANALYTICS_ENABLED": "False"}.items():
            env.insert(key, value)
        self.process.setProcessEnvironment(env)
        self.process.start(program, args)

    def detect_python(self, install_after=False):
        if self.mode or self.detecting:
            return
        self.detecting = True
        self.install_after_detection = install_after
        self.probe_candidates = list(pd.candidates(self.python.text()))
        self.python_hint.setText("Recherche d’un Python compatible en cours…")
        self.status.setText("Vérification automatique · aucune commande à saisir.")
        self.update_buttons()
        self.next_probe()

    def next_probe(self):
        if not self.detecting:
            return
        if not self.probe_candidates:
            self.detecting = False
            self.install_after_detection = False
            self.python_hint.setText("Aucun Python 3.10+ utilisable détecté.")
            self.status.setText("Cliquez sur Télécharger Python, terminez son installation, puis relancez Détecter Python. "
                                "Si Python est installé dans un dossier personnalisé, utilisez Choisir Python.")
            self.update_buttons()
            return
        program, args = self.probe_candidates.pop(0)
        if self.probe.isOpen():
            self.probe.readAllStandardOutput()
        self.probe.start(program, args + ["-c", pd.PROBE])
        self.probe_timer.start(5000)

    def probe_failed(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.detecting:
            self.probe_timer.stop()
            QTimer.singleShot(0, self.next_probe)

    def probe_finished(self, code, exit_status):
        self.probe_timer.stop()
        if not self.detecting:
            return
        try:
            if code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
                raise ValueError("Python indisponible")
            path, version = pd.parse_probe(bytes(self.probe.readAllStandardOutput()).decode("utf-8", errors="replace"))
        except (ValueError, KeyError, IndexError, TypeError, OSError):
            QTimer.singleShot(0, self.next_probe)
            return
        self.detecting = False
        self.python.setText(path)
        settings.set("obliteratus_python", path)
        self.python_hint.setText("Python " + version + " vérifié · prêt à installer Obliteratus.")
        self.status.setText("Python détecté. Cliquez sur Installer / réparer, puis Lancer en local.")
        self.update_buttons()
        if self.install_after_detection:
            self.install_after_detection = False
            self.install_verified()

    def install_local(self):
        self.detect_python(True)

    def install_verified(self):
        try:
            steps = ob.install_steps(self.python.text().strip())
            settings.set("obliteratus_python", self.python.text().strip())
            self.status.setText("Installation en cours · les dépendances peuvent prendre plusieurs minutes.")
            self.run_steps(steps, "install")
        except Exception as error:
            self.status.setText(str(error))

    def launch(self):
        if self.mode:
            return
        if local_jobs.enabled():
            self.resource_token = local_jobs.reserve("Atelier Obliteratus")
            if self.resource_token is None:
                self.status.setText("Un travail local est actif ou en attente. Attendez sa fin avant de lancer l’atelier.")
                return
        try:
            self.active_port = self.port.value()
            settings.set("obliteratus_port", self.active_port)
            self.status.setText("Démarrage local · attendez l'adresse du serveur dans le journal avant d'ouvrir l'interface.")
            self.run_steps([ob.launch_command(self.active_port)], "server")
        except Exception as error:
            local_jobs.release(self.resource_token)
            self.resource_token = None
            self.status.setText(str(error))

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)

    def finished(self, code, exit_status):
        if self.mode == "server":
            local_jobs.release(self.resource_token)
            self.resource_token = None
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
        elif self.mode == "export":
            message = "Modèle ajouté à Ollama. Cliquez sur « Discuter avec ce modèle dans Chat »."
            self.chat_ready_name = self.export_name.text().strip()
        else:
            message = "Serveur local arrêté."
        self.queue.clear()
        self.mode = ""
        self.status.setText(message)
        if ok and self.mode == "":
            self.reload_checkpoints()
        self.update_buttons()

    def failed(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            local_jobs.release(self.resource_token)
            self.resource_token = None
            self.queue.clear()
            self.mode = ""
            self.status.setText("Démarrage impossible : " + self.process.errorString())
            self.update_buttons()

    def stop_process(self):
        if self.detecting:
            self.detecting = False
            self.install_after_detection = False
            self.probe_timer.stop()
            self.probe.kill()
            self.probe.waitForFinished(1000)
            self.python_hint.setText("Détection interrompue.")
            self.status.setText("Détection arrêtée. Vous pouvez la relancer.")
            self.update_buttons()
            return
        self.cancelled = True
        self.queue.clear()
        self.process.terminate()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.kill_timer.start(3000)
        self.update_buttons()

    def shutdown(self):
        self.detecting = False
        self.probe_timer.stop()
        self.probe.kill()
        self.probe.waitForFinished(1000)
        local_jobs.release(self.resource_token)
        self.resource_token = None
        self.queue.clear()
        self.cancelled = True
        self.kill_timer.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)
