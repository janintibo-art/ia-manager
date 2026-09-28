"""Catalogue musique, sons, vidéo et 3D, avec accès aux outils externes."""
import html
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QLineEdit, QListWidget, QListWidgetItem, QTextBrowser, QPlainTextEdit,
    QPushButton, QFileDialog, QSplitter)
from src.backend import media_catalog as catalog, settings
from src.backend.local_creation import validate_engine_url, LOCAL_HELP


class MediaStudioTab(QWidget):
    open_tools = pyqtSignal()
    def __init__(self):
        super().__init__()
        saved = settings.get('media_studio_profiles')
        self.profiles = dict(saved) if isinstance(saved, dict) else {}
        self.current_model = None
        self.loading = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.flush)
        root = QVBoxLayout(self)
        intro = QLabel('Choisissez une spécialité, préparez votre création et ouvrez son outil.\n'
                       'Tous ces modèles disposent d’une exécution sur PC. Téléchargement initial nécessaire ; génération dans leur moteur installé.')
        intro.setWordWrap(True)
        root.addWidget(intro)
        tools_button = QPushButton("Installer / démarrer les outils locaux")
        tools_button.clicked.connect(self.open_tools.emit)
        root.addWidget(tools_button)
        self.local_only = QCheckBox('100 % local — ouvrir uniquement les moteurs sur ce PC')
        self.local_only.setChecked(settings.get('media_local_only') is not False)
        self.local_only.toggled.connect(lambda value: settings.set('media_local_only', value))
        self.local_only.setToolTip(LOCAL_HELP)
        root.addWidget(self.local_only)
        help_button = QPushButton('Comment créer sans Internet ?')
        help_button.clicked.connect(self.show_local_help)
        root.addWidget(help_button)
        filters = QHBoxLayout()
        self.category = QComboBox(); self.category.addItems(catalog.CATEGORIES)
        self.search = QLineEdit(); self.search.setPlaceholderText('Rechercher un modèle ou une spécialité…')
        filters.addWidget(self.category); filters.addWidget(self.search, 1)
        root.addLayout(filters)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.models = QListWidget(); self.models.setMinimumWidth(210)
        split.addWidget(self.models)
        self.panel = QWidget(); form = QVBoxLayout(self.panel)
        self.details = QTextBrowser(); self.details.setMinimumHeight(190)
        form.addWidget(self.details, 2)
        links = QHBoxLayout()
        self.model_link = QPushButton('Modèle et téléchargements')
        self.guide_link = QPushButton('Guide d’installation officiel')
        self.model_link.clicked.connect(lambda: self.open_link('model_url'))
        self.guide_link.clicked.connect(lambda: self.open_link('guide_url'))
        links.addWidget(self.model_link); links.addWidget(self.guide_link)
        form.addLayout(links)
        form.addWidget(QLabel('Adresse de votre interface web déjà lancée (facultatif) :'))
        address = QHBoxLayout()
        self.address = QLineEdit(); self.address.setPlaceholderText('Copier l’adresse affichée par le moteur installé sur votre PC')
        self.open_btn = QPushButton('Ouvrir l’interface')
        self.open_btn.clicked.connect(self.open_engine)
        address.addWidget(self.address, 1); address.addWidget(self.open_btn)
        form.addLayout(address)
        self.prompt_label = QLabel(); form.addWidget(self.prompt_label)
        self.prompt = QPlainTextEdit(); self.prompt.setMinimumHeight(85)
        form.addWidget(self.prompt, 1)
        actions = QHBoxLayout()
        self.example_btn = QPushButton('Charger un exemple')
        self.example_btn.clicked.connect(self.load_example)
        copy = QPushButton('Copier le texte'); copy.clicked.connect(self.copy_prompt)
        actions.addWidget(self.example_btn); actions.addWidget(copy)
        form.addLayout(actions)
        form.addWidget(QLabel('Dossier de résultats à retrouver (ne configure pas le moteur externe) :'))
        folders = QHBoxLayout()
        self.folder = QLineEdit(); self.folder.setReadOnly(True)
        browse = QPushButton('Parcourir…'); browse.clicked.connect(self.choose_folder)
        open_folder = QPushButton('Ouvrir'); open_folder.clicked.connect(self.open_folder)
        folders.addWidget(self.folder, 1); folders.addWidget(browse); folders.addWidget(open_folder)
        form.addLayout(folders)
        split.addWidget(self.panel); split.setStretchFactor(1, 1); split.setSizes([250, 750])
        root.addWidget(split, 1)
        self.status = QLabel('Les poids ne sont pas inclus dans la mise à jour. Consultez la fiche avant l’installation.')
        self.status.setWordWrap(True); root.addWidget(self.status)
        self.category.currentIndexChanged.connect(self.refresh)
        self.search.textChanged.connect(self.refresh)
        self.models.currentItemChanged.connect(self.select_model)
        self.address.textChanged.connect(self.remember)
        self.prompt.textChanged.connect(self.remember)
        self.folder.textChanged.connect(self.remember)
        self.refresh()

    def show_local_help(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, 'Création sur votre PC', LOCAL_HELP)

    def refresh(self):
        previous = self.current_model['id'] if self.current_model else None
        self.models.blockSignals(True)
        self.models.clear()
        selected = 0
        for i, model in enumerate(catalog.filter_models(self.category.currentText(), self.search.text())):
            item = QListWidgetItem(model['name'] + '\n' + model['input'])
            item.setData(Qt.ItemDataRole.UserRole, model)
            item.setToolTip(model['specialty'])
            self.models.addItem(item)
            if model['id'] == previous: selected = i
        self.models.blockSignals(False)
        if self.models.count(): self.models.setCurrentRow(selected)
        else: self.select_model(None, None)

    def select_model(self, item, previous):
        self.current_model = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.panel.setEnabled(bool(item))
        self.loading = True
        if not item:
            self.details.setPlainText('Aucun modèle ne correspond à cette recherche.')
            self.address.clear(); self.prompt.clear(); self.folder.clear()
            self.loading = False
            return
        model = self.current_model
        saved = self.profiles.get(model['id'], {})
        if not isinstance(saved, dict): saved = {}
        self.details.setHtml('<h2>' + html.escape(model['name']) + '</h2>' + ''.join(
            '<p><b>' + label + '</b> ' + html.escape(model[key]) + '</p>'
            for label, key in (('Spécialité :', 'specialty'), ('Entrée :', 'input'),
                ('Outil :', 'engine'), ('Matériel :', 'hardware'), ('Pour commencer :', 'instructions'), ('Conseil :', 'tip'))))
        self.prompt_label.setText('Notes pour préparer votre image de référence :' if model['category']==catalog.CATEGORIES[2] else 'Description à copier dans le moteur :')
        self.address.setText(str(saved.get('url') or ''))
        self.prompt.setPlainText(str(saved.get('prompt') or ''))
        self.folder.setText(str(saved.get('folder') or ''))
        self.loading = False

    def remember(self):
        if self.loading or not self.current_model: return
        self.profiles[self.current_model['id']] = dict(url=self.address.text(), prompt=self.prompt.toPlainText(), folder=self.folder.text())
        self.timer.start(600)

    def flush(self):
        self.timer.stop()
        try: settings.set('media_studio_profiles', self.profiles)
        except Exception as exc: self.status.setText('Enregistrement des préférences impossible : ' + str(exc))

    def open_url(self, url):
        if not QDesktopServices.openUrl(QUrl(url)):
            self.status.setText('Impossible d’ouvrir le navigateur.')
            return False
        return True

    def open_link(self, key):
        if self.current_model: self.open_url(self.current_model[key])

    def open_engine(self):
        try: url = validate_engine_url(self.address.text(), self.local_only.isChecked())
        except ValueError as exc:
            self.status.setText(str(exc)); return
        self.flush()
        if not self.open_url(url): return
        self.status.setText('Ouverture demandée. Collez votre description ou importez votre référence dans l’outil ; aucun travail n’a été envoyé automatiquement.')

    def load_example(self):
        if self.current_model:
            if self.prompt.toPlainText().strip():
                # Ne pas remplacer un brouillon : ajouter l’exemple après le texte existant.
                self.prompt.appendPlainText('\n' + self.current_model['example'])
            else: self.prompt.setPlainText(self.current_model['example'])

    def copy_prompt(self):
        text = self.prompt.toPlainText().strip()
        if not text:
            self.status.setText('Saisissez un texte ou chargez un exemple.'); return
        QApplication.clipboard().setText(text)
        self.status.setText('Texte copié. Collez-le dans le moteur adapté ; pour la 3D, ces notes servent à préparer l’image.')

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choisir le dossier de résultats', self.folder.text() or str(Path.home()))
        if folder: self.folder.setText(folder)

    def open_folder(self):
        path = Path(self.folder.text()) if self.folder.text() else None
        if path is None or not path.is_dir():
            self.status.setText('Choisissez un dossier existant avec Parcourir.'); return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            self.status.setText('Impossible d’ouvrir ce dossier.')

    def shutdown(self):
        self.flush()
