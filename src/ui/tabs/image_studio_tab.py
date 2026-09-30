"""Création d'images : catalogue, installation de checkpoints et génération avec ComfyUI."""
import html
import secrets
import threading
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QImage, QPixmap
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QTextBrowser, QPlainTextEdit, QLineEdit, QFileDialog, QSpinBox,
    QDoubleSpinBox, QMessageBox, QScrollArea, QProgressBar)
from src.backend import image_studio as engine, settings
from src.backend.local_creation import LOCAL_HELP


class ImageStudioTab(QWidget):
    open_tools = pyqtSignal()
    result_ready = pyqtSignal(str, object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)
    download_progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.busy = False
        self.image = QImage()
        self.manual_checkpoints_dir = str(settings.get('image_checkpoints_dir') or '')
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        root = QVBoxLayout(body)
        intro = QLabel("Des modèles pour créer des images à partir d'une description.\n"
                       "ComfyUI doit être installé et lancé sur le PC. IA Manager peut maintenant installer directement les checkpoints compatibles.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        tools_button = QPushButton("Installer / démarrer les outils locaux")
        tools_button.clicked.connect(self.open_tools.emit)
        root.addWidget(tools_button)
        self.local_only = QCheckBox('100 % local — utiliser uniquement un moteur sur ce PC')
        self.local_only.setChecked(settings.get('image_local_only') is not False)
        self.local_only.setToolTip(LOCAL_HELP)
        self.local_only.toggled.connect(lambda value: settings.set('image_local_only', value))
        root.addWidget(self.local_only)
        self.catalog = QComboBox()
        for model in engine.MODELS:
            self.catalog.addItem(model['name'] + ' — ' + model['specialty'])
        root.addWidget(self.catalog)
        self.details = QTextBrowser()
        self.details.setMaximumHeight(145)
        root.addWidget(self.details)

        links = QHBoxLayout()
        self.install_model_btn = QPushButton("⬇ Télécharger et installer ce modèle")
        self.install_model_btn.setObjectName('Primary')
        self.install_model_btn.clicked.connect(self.install_model)
        links.addWidget(self.install_model_btn)
        fiche = QPushButton("Voir la fiche")
        fiche.clicked.connect(self.open_model)
        links.addWidget(fiche)
        comfy = QPushButton("Installer ComfyUI")
        comfy.clicked.connect(lambda: self.open_url('https://www.comfy.org/download'))
        links.addWidget(comfy)
        root.addLayout(links)

        self.download_bar = QProgressBar()
        self.download_bar.setRange(0, 100)
        self.download_bar.setValue(0)
        self.download_bar.setVisible(False)
        root.addWidget(self.download_bar)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_label.setWordWrap(True)
        folder_row.addWidget(self.folder_label, 1)
        choose_folder = QPushButton('Choisir le dossier checkpoints…')
        choose_folder.clicked.connect(self.choose_checkpoints_dir)
        folder_row.addWidget(choose_folder)
        root.addLayout(folder_row)

        row = QHBoxLayout()
        self.url = QLineEdit(settings.get('image_comfy_url') or 'http://127.0.0.1:8188')
        self.url.setPlaceholderText('Adresse de ComfyUI')
        self.connect_btn = QPushButton('Connecter / actualiser les modèles')
        self.connect_btn.clicked.connect(self.connect_engine)
        browser = QPushButton('Ouvrir ComfyUI')
        browser.clicked.connect(self.open_engine)
        row.addWidget(self.url, 1)
        row.addWidget(self.connect_btn)
        row.addWidget(browser)
        root.addLayout(row)
        root.addWidget(QLabel('Checkpoint installé dans ComfyUI (SDXL et dérivés) :'))
        self.checkpoint = QComboBox()
        root.addWidget(self.checkpoint)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText('Décrivez votre image : sujet, style, couleurs, composition…')
        self.prompt.setMaximumHeight(100)
        root.addWidget(self.prompt)
        self.negative = QLineEdit()
        self.negative.setPlaceholderText('À éviter (facultatif) : texte, flou…')
        root.addWidget(self.negative)
        params = QHBoxLayout()
        self.size = QComboBox()
        for n in (512, 768, 1024): self.size.addItem(f'{n} × {n}', n)
        self.steps = QSpinBox(); self.steps.setRange(1, 60)
        self.cfg = QDoubleSpinBox(); self.cfg.setRange(1, 15); self.cfg.setSingleStep(0.5)
        for label, widget in (('Format', self.size), ('Étapes', self.steps), ('Guidage', self.cfg)):
            params.addWidget(QLabel(label)); params.addWidget(widget)
        root.addLayout(params)
        self.generate_btn = QPushButton('🎨 Générer une image')
        self.generate_btn.clicked.connect(self.generate)
        root.addWidget(self.generate_btn)
        self.status = QLabel('Choisissez un modèle puis cliquez sur « Télécharger et installer ce modèle ».')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.preview = QLabel('Votre image apparaîtra ici')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(200)
        root.addWidget(self.preview)
        self.save_btn = QPushButton('Enregistrer en PNG…')
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_image)
        root.addWidget(self.save_btn)
        self.result_ready.connect(self.on_result)
        self.failed.connect(self.on_error)
        self.progress.connect(self.on_progress)
        self.download_progress.connect(self.download_bar.setValue)
        self.catalog.currentIndexChanged.connect(self.show_model)
        self.refresh_folder_label()
        self.show_model()

    def open_url(self, url):
        if not QDesktopServices.openUrl(QUrl(url)):
            self.status.setText("Impossible d'ouvrir le navigateur.")

    def open_model(self):
        self.open_url('https://huggingface.co/' + engine.MODELS[self.catalog.currentIndex()]['repo'])

    def open_engine(self):
        try: self.open_url(engine.base_url(self.url.text(), self.local_only.isChecked()))
        except ValueError as exc: self.on_error(str(exc))

    def current_checkpoints_dir(self):
        managed = engine.managed_checkpoints_dir()
        if managed is not None:
            return managed
        if self.manual_checkpoints_dir:
            return engine.validate_checkpoints_dir(self.manual_checkpoints_dir)
        return None

    def refresh_folder_label(self):
        try:
            folder = self.current_checkpoints_dir()
        except Exception:
            folder = None
        if folder:
            self.folder_label.setText('Installation automatique dans : ' + str(folder))
        else:
            self.folder_label.setText('Dossier ComfyUI non détecté automatiquement. Utilisez « Choisir le dossier checkpoints… » une seule fois.')

    def choose_checkpoints_dir(self):
        start = self.manual_checkpoints_dir or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, 'Choisir ComfyUI ou son dossier models/checkpoints', start)
        if not path:
            return
        try:
            folder = engine.validate_checkpoints_dir(path)
        except Exception as exc:
            self.on_error(str(exc)); return
        self.manual_checkpoints_dir = str(folder)
        settings.set('image_checkpoints_dir', self.manual_checkpoints_dir)
        self.refresh_folder_label()
        self.status.setText('Dossier checkpoints enregistré : ' + self.manual_checkpoints_dir)

    def show_model(self):
        model = engine.MODELS[self.catalog.currentIndex()]
        info = ('Génération depuis cet onglet avec le checkpoint installé.' if model['direct'] else 'Disponible dans le catalogue ; génération dans l’interface ComfyUI uniquement.')
        self.details.setHtml('<b>' + html.escape(model['name']) + '</b><p>' + html.escape(model['note']) + '</p><p>' + info + '</p>')
        self.size.setCurrentIndex(self.size.findData(model['size']))
        self.steps.setValue(model['steps'])
        self.cfg.setValue(model['cfg'])
        self.install_model_btn.setEnabled(not self.busy and bool(model.get('download_url')))
        self.install_model_btn.setText('⬇ Télécharger et installer ce modèle' if model.get('download_url') else 'Téléchargement manuel via la fiche')
        self.generate_btn.setEnabled(not self.busy and model['direct'] and self.checkpoint.count() > 0)

    def set_busy(self, busy):
        self.busy = busy
        for widget in (self.catalog, self.url, self.connect_btn, self.checkpoint, self.prompt, self.negative, self.size, self.steps, self.cfg, self.local_only):
            widget.setEnabled(not busy)
        model = engine.MODELS[self.catalog.currentIndex()]
        self.install_model_btn.setEnabled(not busy and bool(model.get('download_url')))
        self.generate_btn.setEnabled(not busy and model['direct'] and self.checkpoint.count() > 0)

    def run_job(self, kind, function):
        self.set_busy(True)
        def run():
            try:
                result = function()
                self.result_ready.emit(kind, result)
            except Exception as exc:
                try: self.failed.emit(str(exc))
                except RuntimeError: pass
        threading.Thread(target=run, daemon=True).start()

    def install_model(self):
        model = engine.MODELS[self.catalog.currentIndex()]
        folder = self.current_checkpoints_dir()
        if folder is None:
            self.choose_checkpoints_dir()
            folder = self.current_checkpoints_dir()
        if folder is None:
            return
        self.download_bar.setVisible(True)
        self.download_bar.setValue(0)
        self.status.setText('Préparation du téléchargement de ' + model['name'] + '…')
        def report(message):
            self.progress.emit(message)
            if '%' in message:
                try:
                    percent = int(message.split('%', 1)[0].rsplit(' ', 1)[-1])
                    self.download_progress.emit(max(0, min(100, percent)))
                except Exception:
                    pass
        self.run_job('install', lambda: engine.download_checkpoint(model, folder, report))

    def connect_engine(self):
        try:
            url = engine.base_url(self.url.text(), self.local_only.isChecked())
            settings.set('image_comfy_url', url)
        except Exception as exc:
            self.on_error(str(exc)); return
        self.checkpoint.clear()
        self.status.setText('Connexion à ComfyUI…')
        local_only = self.local_only.isChecked()
        self.run_job('models', lambda: engine.checkpoints(url, local_only))

    def generate(self):
        try:
            url = engine.base_url(self.url.text(), self.local_only.isChecked())
            graph = engine.workflow(self.checkpoint.currentText(), self.prompt.toPlainText(), self.negative.text(), self.size.currentData(), self.steps.value(), self.cfg.value(), secrets.randbelow(2**32))
        except Exception as exc:
            self.on_error(str(exc)); return
        self.status.setText('Envoi à ComfyUI…')
        local_only = self.local_only.isChecked()
        self.run_job('image', lambda: engine.generate(url, graph, self.progress.emit, local_only))

    def on_progress(self, message):
        self.status.setText(message)

    def on_result(self, kind, result):
        self.set_busy(False)
        if kind == 'install':
            self.download_bar.setValue(100)
            self.status.setText('✅ Modèle installé. Actualisation de ComfyUI…\n' + str(result))
            self.connect_engine()
            return
        if kind == 'models':
            self.checkpoint.addItems(result)
            model = engine.MODELS[self.catalog.currentIndex()]
            wanted = model.get('filename')
            if wanted:
                for i in range(self.checkpoint.count()):
                    if self.checkpoint.itemText(i).endswith(wanted):
                        self.checkpoint.setCurrentIndex(i)
                        break
            self.generate_btn.setEnabled(bool(result) and model['direct'])
            self.status.setText(f'✅ {len(result)} checkpoint(s) trouvé(s). Le modèle peut maintenant être utilisé.' if result else 'Aucun checkpoint détecté. Installez le modèle avec le bouton au-dessus puis actualisez.')
        else:
            image = QImage.fromData(result)
            if image.isNull():
                self.on_error('ComfyUI a renvoyé une image illisible.'); return
            self.image = image
            self.preview.setPixmap(QPixmap.fromImage(image).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.save_btn.setEnabled(True)
            self.status.setText('✅ Image créée. Copie conservée dans les sorties ComfyUI ; vous pouvez aussi enregistrer un PNG ici.')

    def on_error(self, message):
        self.set_busy(False)
        self.status.setText('Erreur : ' + message + '\nSi ComfyUI est lancé, utilisez « Connecter / actualiser les modèles » puis réessayez.')

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Enregistrer l’image', str(Path.home() / 'image_ia.png'), 'Image PNG (*.png)')
        if path:
            if not path.lower().endswith('.png'): path += '.png'
            if not self.image.save(path, 'PNG'):
                QMessageBox.warning(self, 'Enregistrement', 'Impossible d’enregistrer à cet emplacement.')
            else: self.status.setText('Image enregistrée : ' + path)
