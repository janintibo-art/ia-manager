
"""Catalogue musique, sons, vidéo et 3D avec démarrage guidé."""
import html
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem, QTextBrowser, QPlainTextEdit,
    QPushButton, QFileDialog, QSplitter, QGroupBox
)
from src.backend import media_catalog as catalog, settings, media_setup
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
        intro = QLabel(
            'Choisissez ce que vous voulez créer. IA Manager vous indique ensuite quoi installer et dans quel ordre.'
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        guide_box = QGroupBox("Démarrage rapide")
        gl = QVBoxLayout(guide_box)
        self.quick_title = QLabel("Sélectionnez un modèle.")
        self.quick_title.setObjectName("Title")
        gl.addWidget(self.quick_title)
        self.quick_state = QLabel()
        self.quick_state.setWordWrap(True)
        gl.addWidget(self.quick_state)
        self.quick_steps = QLabel()
        self.quick_steps.setWordWrap(True)
        gl.addWidget(self.quick_steps)
        qa = QHBoxLayout()
        self.quick_install = QPushButton("1 · Installer le moteur recommandé")
        self.quick_install.setObjectName("Primary")
        self.quick_install.clicked.connect(self.open_recommended_tool)
        self.quick_start = QPushButton("2 · Aller à Démarrer")
        self.quick_start.clicked.connect(self.open_recommended_tool)
        self.quick_open = QPushButton("3 · Ouvrir l'interface")
        self.quick_open.clicked.connect(self.open_engine)
        qa.addWidget(self.quick_install)
        qa.addWidget(self.quick_start)
        qa.addWidget(self.quick_open)
        gl.addLayout(qa)
        root.addWidget(guide_box)

        self.local_only = QCheckBox('100 % local — ouvrir uniquement les moteurs sur ce PC')
        self.local_only.setChecked(settings.get('media_local_only') is not False)
        self.local_only.toggled.connect(lambda value: settings.set('media_local_only', value))
        self.local_only.setToolTip(LOCAL_HELP)
        root.addWidget(self.local_only)

        help_button = QPushButton('Comment créer sans Internet ?')
        help_button.clicked.connect(self.show_local_help)
        root.addWidget(help_button)

        filters = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItems(catalog.CATEGORIES)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Rechercher un modèle ou une spécialité…')
        filters.addWidget(self.category)
        filters.addWidget(self.search, 1)
        root.addLayout(filters)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.models = QListWidget()
        self.models.setMinimumWidth(210)
        split.addWidget(self.models)

        self.panel = QWidget()
        form = QVBoxLayout(self.panel)
        self.details = QTextBrowser()
        self.details.setMinimumHeight(190)
        form.addWidget(self.details, 2)

        links = QHBoxLayout()
        self.model_link = QPushButton('Voir le modèle')
        self.guide_link = QPushButton('Guide officiel')
        self.model_link.clicked.connect(lambda: self.open_link('model_url'))
        self.guide_link.clicked.connect(lambda: self.open_link('guide_url'))
        links.addWidget(self.model_link)
        links.addWidget(self.guide_link)
        form.addLayout(links)

        form.addWidget(QLabel('Adresse de l’interface locale :'))
        address = QHBoxLayout()
        self.address = QLineEdit()
        self.address.setPlaceholderText('Elle sera remplie automatiquement après le démarrage du moteur')
        self.open_btn = QPushButton('Ouvrir l’interface')
        self.open_btn.clicked.connect(self.open_engine)
        address.addWidget(self.address, 1)
        address.addWidget(self.open_btn)
        form.addLayout(address)

        self.prompt_label = QLabel()
        form.addWidget(self.prompt_label)
        self.prompt = QPlainTextEdit()
        self.prompt.setMinimumHeight(85)
        form.addWidget(self.prompt, 1)

        actions = QHBoxLayout()
        self.example_btn = QPushButton('Charger un exemple')
        self.example_btn.clicked.connect(self.load_example)
        copy = QPushButton('Copier le texte')
        copy.clicked.connect(self.copy_prompt)
        actions.addWidget(self.example_btn)
        actions.addWidget(copy)
        form.addLayout(actions)

        form.addWidget(QLabel('Dossier où retrouver vos résultats :'))
        folders = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        browse = QPushButton('Parcourir…')
        browse.clicked.connect(self.choose_folder)
        open_folder = QPushButton('Ouvrir')
        open_folder.clicked.connect(self.open_folder)
        folders.addWidget(self.folder, 1)
        folders.addWidget(browse)
        folders.addWidget(open_folder)
        form.addLayout(folders)

        split.addWidget(self.panel)
        split.setStretchFactor(1, 1)
        split.setSizes([250, 750])
        root.addWidget(split, 1)

        self.status = QLabel('Choisissez un modèle : le bloc Démarrage rapide vous guidera.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)

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
            if model['id'] == previous:
                selected = i
        self.models.blockSignals(False)
        if self.models.count():
            self.models.setCurrentRow(selected)
        else:
            self.select_model(None, None)

    def update_quick_guide(self):
        guide = media_setup.quick_guide(self.current_model)
        key = guide["tool"]
        self.quick_title.setText("À installer : " + guide["title"])
        state = media_setup.tool_state(key)
        if key:
            if state["installed"]:
                self.quick_state.setText("✅ Moteur installé par IA Manager · état : " + state["state"])
                self.quick_install.setText("✅ Moteur installé")
                self.quick_install.setEnabled(False)
                self.quick_start.setEnabled(True)
            else:
                self.quick_state.setText("⚠️ Moteur non installé · commencez par le bouton 1.")
                self.quick_install.setText("1 · Installer " + guide["title"])
                self.quick_install.setEnabled(True)
                self.quick_start.setEnabled(False)
        else:
            self.quick_state.setText("ℹ️ Ce modèle n’a pas encore d’installation automatique dédiée.")
            self.quick_install.setText("Ouvrir Outils locaux")
            self.quick_install.setEnabled(True)
            self.quick_start.setEnabled(False)

        self.quick_steps.setText(
            "\n".join(f"{i+1}. {step}" for i, step in enumerate(guide["steps"]))
        )
        self.quick_open.setEnabled(bool(self.address.text().strip()))

    def select_model(self, item, previous):
        self.current_model = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.panel.setEnabled(bool(item))
        self.loading = True
        if not item:
            self.details.setPlainText('Aucun modèle ne correspond à cette recherche.')
            self.address.clear()
            self.prompt.clear()
            self.folder.clear()
            self.loading = False
            self.update_quick_guide()
            return

        model = self.current_model
        saved = self.profiles.get(model['id'], {})
        if not isinstance(saved, dict):
            saved = {}

        self.details.setHtml(
            '<h2>' + html.escape(model['name']) + '</h2>' +
            '<p><b>Ce modèle sert à :</b> ' + html.escape(model['specialty']) + '</p>' +
            '<p><b>Vous fournissez :</b> ' + html.escape(model['input']) + '</p>' +
            '<p><b>Moteur utilisé :</b> ' + html.escape(model['engine']) + '</p>' +
            '<p><b>Matériel :</b> ' + html.escape(model['hardware']) + '</p>' +
            '<p><b>Quand tout est installé :</b> ' + html.escape(model['instructions']) + '</p>'
        )

        self.prompt_label.setText(
            'Préparation de l’image de référence :'
            if model['category'] == catalog.CATEGORIES[2]
            else 'Description à utiliser dans le moteur :'
        )
        self.address.setText(str(saved.get('url') or ''))
        self.prompt.setPlainText(str(saved.get('prompt') or ''))
        self.folder.setText(str(saved.get('folder') or ''))
        self.loading = False
        self.update_quick_guide()

    def open_recommended_tool(self):
        key = media_setup.tool_for_model(self.current_model)
        if key:
            settings.set('creative_tools_requested', key)
        self.open_tools.emit()
        self.status.setText(
            'Outils locaux ouvert sur le moteur recommandé. '
            'Utilisez Installer / reprendre, puis Démarrer une fois l’installation terminée.'
        )

    def remember(self):
        if self.loading or not self.current_model:
            return
        self.profiles[self.current_model['id']] = dict(
            url=self.address.text(),
            prompt=self.prompt.toPlainText(),
            folder=self.folder.text(),
        )
        self.timer.start(600)
        self.quick_open.setEnabled(bool(self.address.text().strip()))

    def flush(self):
        self.timer.stop()
        try:
            settings.set('media_studio_profiles', self.profiles)
        except Exception as exc:
            self.status.setText('Enregistrement des préférences impossible : ' + str(exc))

    def open_url(self, url):
        if not QDesktopServices.openUrl(QUrl(url)):
            self.status.setText('Impossible d’ouvrir le navigateur.')
            return False
        return True

    def open_link(self, key):
        if self.current_model:
            self.open_url(self.current_model[key])

    def open_engine(self):
        try:
            url = validate_engine_url(self.address.text(), self.local_only.isChecked())
        except ValueError:
            self.open_recommended_tool()
            self.status.setText(
                "L’interface n’est pas encore connue. Démarrez d’abord le moteur dans Outils locaux ; "
                "l’adresse sera ensuite remplie automatiquement."
            )
            return
        self.flush()
        if not self.open_url(url):
            return
        self.status.setText('Interface locale ouverte.')

    def load_example(self):
        if self.current_model:
            if self.prompt.toPlainText().strip():
                self.prompt.appendPlainText('\n' + self.current_model['example'])
            else:
                self.prompt.setPlainText(self.current_model['example'])

    def copy_prompt(self):
        text = self.prompt.toPlainText().strip()
        if not text:
            self.status.setText('Saisissez un texte ou chargez un exemple.')
            return
        QApplication.clipboard().setText(text)
        self.status.setText('Texte copié.')

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Choisir le dossier de résultats',
            self.folder.text() or str(Path.home())
        )
        if folder:
            self.folder.setText(folder)

    def open_folder(self):
        path = Path(self.folder.text()) if self.folder.text() else None
        if path is None or not path.is_dir():
            self.status.setText('Choisissez un dossier existant avec Parcourir.')
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            self.status.setText('Impossible d’ouvrir ce dossier.')

    def shutdown(self):
        self.flush()
