"""Pilotage de tâches ML dans un interpréteur externe, interface non bloquante."""
import codecs
import json
import os
from pathlib import Path
import shutil

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QDoubleSpinBox,
    QPlainTextEdit, QMessageBox, QTabWidget)
from src.backend import training_lab as lab, settings, local_jobs


class TrainingTab(QWidget):
    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.process = None
        self.token = None
        self.job = None
        self.logfile = None
        self.cancelled = False
        self.importing = False
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        layout = QVBoxLayout(self)
        intro = QLabel('Entraîner une spécialité, fusionner deux variantes compatibles, puis tester dans Ollama. '
                       'Les modèles originaux restent intacts. Fermez les modèles Ollama chargés avant un entraînement.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.python = QLineEdit(str(settings.get('training_python') or ''))
        self.python.setPlaceholderText('Python de votre environnement Unsloth / MergeKit (python.exe)')
        row = QHBoxLayout()
        row.addWidget(self.python)
        choose = QPushButton('Parcourir…')
        choose.clicked.connect(self.choose_python)
        row.addWidget(choose)
        form.addRow('Moteur Python externe', row)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        diagnostic = QPushButton('Diagnostic CUDA et outils')
        diagnostic.clicked.connect(lambda: self.launch('diagnostic'))
        help_button = QPushButton('Installer Unsloth sous Windows')
        help_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://unsloth.ai/docs/get-started/install/windows-installation')))
        merge_help = QPushButton('Installation MergeKit')
        merge_help.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://github.com/arcee-ai/mergekit#installation')))
        for b in (diagnostic, help_button, merge_help): buttons.addWidget(b)
        layout.addLayout(buttons)
        pages = QTabWidget()
        layout.addWidget(pages)
        train = QWidget()
        f = QFormLayout(train)
        self.model = QLineEdit('Qwen/Qwen2.5-3B-Instruct')
        f.addRow('Modèle Hugging Face / dossier', self.model)
        self.dataset = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.dataset)
        pick = QPushButton('Choisir JSONL…')
        pick.clicked.connect(self.choose_dataset)
        row.addWidget(pick)
        f.addRow('Exemples validés', row)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 3)
        f.addRow('Passages sur les exemples', self.epochs)
        text = QLabel('Profil prudent : QLoRA 4 bits, rang 8, contexte 1024, lot 1. '
                      '20 % des exemples réservés à l’évaluation. Minimum 10 exemples distincts ; '
                      'plusieurs centaines de bons exemples sont préférables. La RAM ne remplace pas la VRAM pour l’entraînement.')
        text.setWordWrap(True)
        f.addRow(text)
        start = QPushButton('Entraîner et exporter')
        start.clicked.connect(lambda: self.launch('train'))
        f.addRow(start)
        pages.addTab(train, 'Entraînement')
        merge = QWidget()
        f = QFormLayout(merge)
        self.model_a = QLineEdit()
        self.model_b = QLineEdit()
        f.addRow('Modèle A — Hugging Face / dossier', self.model_a)
        f.addRow('Modèle B — même base', self.model_b)
        self.weight = QDoubleSpinBox()
        self.weight.setRange(.05, .95)
        self.weight.setSingleStep(.05)
        self.weight.setValue(.5)
        f.addRow('Part du modèle B (0,5 = moitié)', self.weight)
        text = QLabel('Fusion linéaire sur CPU/RAM avec MergeKit. Deux variantes issues du même modèle de base, '
                      'poids Safetensors non quantifiés. Architectures et vocabulaires vérifiés avant fusion ; '
                      'cette vérification ne garantit pas la qualité. Ne fusionne pas directement les modèles GGUF d’Ollama. '
                      'Prévoir plusieurs dizaines de Go libres sur disque.')
        text.setWordWrap(True)
        f.addRow(text)
        start_merge = QPushButton('Vérifier et fusionner')
        start_merge.clicked.connect(lambda: self.launch('merge'))
        f.addRow(start_merge)
        pages.addTab(merge, 'Fusion')
        export = QWidget()
        f = QFormLayout(export)
        self.export_folder = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.export_folder)
        pick_export = QPushButton('Dossier model…')
        pick_export.clicked.connect(self.choose_export)
        row.addWidget(pick_export)
        f.addRow('Résultat Safetensors', row)
        self.export_name = QLineEdit('mon-ia-personnelle')
        f.addRow('Nouveau nom Ollama', self.export_name)
        text = QLabel('Import local quantifié Q4_K_M. Ollama doit être installé et accepter cette architecture. '
                      'Un modèle de même nom sera remplacé : choisissez un nouveau nom pour comparer les versions. '
                      'Utilisez ensuite le Comparateur d’IA Manager avec des questions absentes de l’entraînement.')
        text.setWordWrap(True)
        f.addRow(text)
        imp = QPushButton('Importer dans Ollama')
        imp.clicked.connect(self.import_model)
        f.addRow(imp)
        pages.addTab(export, 'Ollama')
        guide = QPlainTextEdit()
        guide.setReadOnly(True)
        guide.setPlainText('DÉMARRAGE\n1. Installer un environnement Unsloth Windows selon le guide officiel (bouton ci-dessus). '
            'Sélectionner son python.exe, pas ia_manager.exe. Pour la fusion, sélectionner un environnement avec MergeKit installé. '
            'Ces bibliothèques ne sont pas incluses dans IA Manager.\n'
            '2. Lancer le diagnostic : CUDA doit être disponible pour entraîner.\n'
            '3. Préparer un fichier JSONL : un objet par ligne, avec instruction, output et éventuellement input.\n'
            'Exemple de ligne :\n'+json.dumps({'instruction':'Comment nommer mes archives ?', 'input':'', 'output':'Utilise le nom du programme suivi du numéro de version.'}, ensure_ascii=False)+
            '\n4. Préférer un modèle 3B pour commencer ; un 7B/8B peut demander des réglages supplémentaires. '
            'Les noms Ollama comme qwen3:14b ne sont pas des identifiants Hugging Face.\n'
            '5. Entraîner ; les journaux, adaptateur, évaluations et modèle complet sont conservés dans le dossier de la tâche. '
            'Si l’export échoue après sauvegarde, l’adaptateur reste disponible.\n'
            '6. Importer le dossier model dans Ollama. En cas d’architecture non prise en charge, une conversion GGUF externe est nécessaire.\n'
            '7. Comparer avant/après. Une loss plus basse ne prouve pas que toutes les réponses sont meilleures.\n\n'
            'FUSION\nChoisir deux variantes entraînées à partir de la même base. Une moyenne de poids n’additionne pas simplement les connaissances. '
            'Le modèle peut perdre des capacités. Conserver les originaux.\n\n'
            'Cette version ne collecte pas automatiquement les conversations et ne réentraîne pas en permanence. '
            'Seuls les exemples du fichier choisi sont utilisés. Les téléchargements initiaux nécessitent Internet ; '
            'les exemples ne sont pas téléversés par cet atelier.\n'
            'La fermeture de l’application arrête la tâche. Une tâche interrompue reste marquée incomplète ; '
            'il n’y a pas de reprise automatique dans cette version.')
        pages.addTab(guide, 'Guide')
        self.status = QLabel('Prêt — commencez par le moteur Python et le diagnostic.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        layout.addWidget(self.log, 1)
        row = QHBoxLayout()
        self.stop = QPushButton('Arrêter la tâche')
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self.shutdown)
        open_folder = QPushButton('Ouvrir les résultats')
        open_folder.clicked.connect(self.open_results)
        row.addWidget(self.stop)
        row.addWidget(open_folder)
        layout.addLayout(row)

    def choose_python(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Python de l’environnement ML')
        if path: self.python.setText(path)

    def choose_dataset(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Exemples validés', '', 'JSONL (*.jsonl)')
        if path: self.dataset.setText(path)

    def choose_export(self):
        path = QFileDialog.getExistingDirectory(self, 'Dossier model exporté')
        if path: self.export_folder.setText(path)

    def open_results(self):
        root = self.job or lab.lab_root()
        root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def launch(self, action):
        if self.process is not None: return
        try:
            python = Path(self.python.text().strip())
            if not python.is_file() or 'ia_manager' in python.name.lower():
                raise ValueError('Sélectionnez le vrai python.exe de l’environnement ML.')
            settings.set('training_python', str(python))
            job = lab.create_job(action, self.model.text() if action == 'train' else self.model_a.text(),
                self.model_b.text(), self.dataset.text(), self.epochs.value(), self.weight.value())
            self.start_process(str(python), ['-u', str(job/'runner.py'), str(job)], job)
        except Exception as exc:
            self.status.setText(str(exc))

    def import_model(self):
        if self.process is not None: return
        try:
            name = self.export_name.text().strip()
            mf = lab.import_modelfile(self.export_folder.text(), name)
            ollama = shutil.which('ollama')
            if not ollama: raise ValueError('Ollama introuvable dans le PATH.')
            if QMessageBox.question(self, 'Import Ollama',
                    f'Créer {name} ? Si ce nom existe déjà dans Ollama, il sera remplacé.',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            self.start_process(ollama, ['create', name, '-f', str(mf), '--quantize', 'q4_K_M'], mf.parent, True)
        except Exception as exc:
            self.status.setText(str(exc))

    def start_process(self, program, args, job, importing=False):
        token = local_jobs.reserve('Entraînement / fusion / import')
        if token is None:
            raise ValueError('Une génération locale est en cours ou en attente. Réessayez après sa fin.')
        self.token = token
        self.job = job
        self.importing = importing
        self.cancelled = False
        self.log.clear()
        self.decoder.reset()
        self.logfile = job/'execution.log'
        self.status.setText('En cours — résultats : '+str(job))
        self.stop.setEnabled(True)
        p = QProcess(self)
        self.process = p
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('HF_HUB_DISABLE_TELEMETRY', '1')
        env.insert('WANDB_DISABLED', 'true')
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(self.finished)
        p.errorOccurred.connect(self.process_error)
        p.start(program, args)

    def read_output(self):
        if self.process is None: return
        data = bytes(self.process.readAllStandardOutput())
        text = self.decoder.decode(data)
        self.log.insertPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())
        try:
            with self.logfile.open('ab') as stream: stream.write(data)
        except OSError:
            self.status.setText('Attention : journal disque inaccessible ; sortie visible ci-dessous.')

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText(self.process.errorString())
            self.finished(-1, QProcess.ExitStatus.CrashExit)

    def finished(self, code, status):
        if self.process is None: return
        self.read_output()
        success = not self.cancelled and code == 0 and status == QProcess.ExitStatus.NormalExit
        self.status.setText('Terminé.' if success else 'Arrêté ou en échec — consultez le journal. Les fichiers partiels sont conservés.')
        if success and (self.job/'model').is_dir():
            self.export_folder.setText(str(self.job/'model'))
        if success and self.importing: self.models_changed.emit()
        self.process.deleteLater()
        self.process = None
        self.stop.setEnabled(False)
        local_jobs.release(self.token)
        self.token = None

    def shutdown(self):
        if self.process is None: return
        self.cancelled = True
        # Arrêter aussi les sous-processus (MergeKit, téléchargement, etc.).
        import psutil
        pid = int(self.process.processId())
        if pid:
            try:
                children = psutil.Process(pid).children(recursive=True)
                for child in children:
                    try: child.kill()
                    except psutil.Error: pass
            except psutil.Error: pass
        process = self.process
        process.kill()
        process.waitForFinished(3000)
