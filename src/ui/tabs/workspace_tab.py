"""Documents par projet et profils réutilisables."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QLineEdit, QPlainTextEdit, QFormLayout, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTabWidget)
from PyQt6.QtCore import Qt
from src.backend import settings, attachments, project_memory, providers, model_options
from src.ui.workers import AttachmentWorker
from src.ui.tabs.resources_tab import ResourcesTab
from src.ui.tabs.trials_tab import TrialsTab
from src.ui.tabs.projects_tab import get_project_manager


class WorkspaceTab(QWidget):
    apply_profile = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.worker = None
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)
        docs = QWidget()
        lay = QVBoxLayout(docs)
        note = QLabel("Documents indexés localement par projet. Le chat retrouve les passages par mots-clés. "
                      "Si vous utilisez une IA distante, les extraits retenus lui seront transmis. "
                      "Un document de même nom remplace sa version indexée ; les fichiers originaux restent intacts.")
        note.setWordWrap(True)
        lay.addWidget(note)
        self.project = QComboBox()
        self.project.currentIndexChanged.connect(self.refresh_docs)
        lay.addWidget(self.project)
        self.doc_search = QLineEdit()
        self.doc_search.setPlaceholderText("Rechercher dans les documents de ce projet…")
        self.doc_search.textChanged.connect(self.search_docs)
        lay.addWidget(self.doc_search)
        self.docs = QListWidget()
        self.docs.currentItemChanged.connect(self.preview_doc)
        lay.addWidget(self.docs)
        self.doc_preview = QPlainTextEdit()
        self.doc_preview.setReadOnly(True)
        self.doc_preview.setPlaceholderText("Sélectionnez un document pour afficher un extrait.")
        self.doc_preview.setMaximumBlockCount(500)
        lay.addWidget(self.doc_preview)
        row = QHBoxLayout()
        self.import_btn = QPushButton("Ajouter des documents…")
        self.import_btn.clicked.connect(self.import_docs)
        row.addWidget(self.import_btn)
        self.cancel_btn = QPushButton("Arrêter après le fichier en cours")
        self.cancel_btn.clicked.connect(self.cancel_import)
        self.cancel_btn.setEnabled(False)
        row.addWidget(self.cancel_btn)
        self.delete_btn = QPushButton("Retirer le document sélectionné")
        self.delete_btn.clicked.connect(self.remove_doc)
        row.addWidget(self.delete_btn)
        lay.addLayout(row)
        self.doc_status = QLabel()
        self.doc_status.setWordWrap(True)
        lay.addWidget(self.doc_status)
        tabs.addTab(docs, "Mémoire documentaire")
        profiles = QWidget()
        lay = QVBoxLayout(profiles)
        self.profiles = QComboBox()
        self.profiles.currentIndexChanged.connect(self.load_profile)
        lay.addWidget(self.profiles)
        form = QFormLayout()
        self.name = QLineEdit()
        self.model = QComboBox()
        self.model.setEditable(True)
        self.instructions = QPlainTextEdit()
        self.mode = QComboBox()
        for key, label in model_options.MODES.items():
            self.mode.addItem(label, key)
        self.ctx = QSpinBox()
        self.ctx.setRange(512, 131072)
        self.ctx.setValue(8192)
        self.temp = QDoubleSpinBox()
        self.temp.setRange(0,2)
        self.temp.setSingleStep(.1)
        self.temp.setValue(.7)
        self.web = QCheckBox("Recherche web")
        self.code = QCheckBox("Réponses avec fichiers complets")
        for label, field in (("Nom",self.name),("Modèle (référence fournisseur::modèle)",self.model),
                             ("Consignes",self.instructions),("Mode Ollama",self.mode),
                             ("Contexte Ollama",self.ctx),("Température Ollama",self.temp)):
            form.addRow(label, field)
        form.addRow(self.web)
        form.addRow(self.code)
        lay.addLayout(form)
        row = QHBoxLayout()
        for label, slot in (("Enregistrer",self.save_profile),("Appliquer au chat",self.use_profile),
                            ("Supprimer",self.delete_profile)):
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        lay.addLayout(row)
        self.profile_status = QLabel("Les réglages de génération s'appliquent à Ollama ; les consignes et outils à tous les modèles.")
        self.profile_status.setWordWrap(True)
        lay.addWidget(self.profile_status)
        tabs.addTab(profiles,"Profils de travail")
        self.resources = ResourcesTab()
        self.trials = TrialsTab()
        tabs.addTab(self.resources, "Mémoire GPU / file")
        tabs.addTab(self.trials, "Carnet Obliteratus")
        self.refresh_projects()
        self.refresh_profiles()

    def folder(self):
        pid = self.project.currentData()
        return get_project_manager().project_folder(pid) if pid else None

    def refresh_projects(self):
        if self.worker is not None:
            return
        selected = self.project.currentData()
        self.project.blockSignals(True)
        self.project.clear()
        for p in get_project_manager().list_projects():
            self.project.addItem(p["name"],p["id"])
        index=self.project.findData(selected)
        if index>=0: self.project.setCurrentIndex(index)
        self.project.blockSignals(False)
        self.refresh_docs()

    def search_docs(self):
        query = self.doc_search.text().strip()
        if not query:
            self.refresh_docs()
            return
        self.docs.clear()
        folder = self.folder()
        if folder is None:
            return
        for row in project_memory.search(folder, query, 50):
            item = QListWidgetItem(f"{row['name']} · passage {row['passage']} · pertinence {row['score']}")
            item.setData(Qt.ItemDataRole.UserRole, row)
            self.docs.addItem(item)
        self.doc_status.setText(f"{self.docs.count()} passage(s) trouvé(s).")

    def preview_doc(self, current, _previous=None):
        row = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.doc_preview.setPlainText(row.get("text", "") if isinstance(row, dict) else "")

    def refresh_docs(self):
        self.docs.clear()
        self.doc_preview.clear()
        folder=self.folder()
        if folder is None: return
        try:
            for doc in project_memory.documents(folder):
                item=QListWidgetItem(f"{doc['name']} · {doc['chars']} caractères")
                item.setData(Qt.ItemDataRole.UserRole,doc['id']); self.docs.addItem(item)
        except Exception as e: self.doc_status.setText(str(e))

    def import_docs(self):
        folder=self.folder()
        if folder is None or self.worker is not None: return
        paths,_=QFileDialog.getOpenFileNames(self,"Documents du projet","","Documents (*.pdf *.docx *.txt *.md *.csv *.py *.js *.json *.zip);;Tous (*)")
        if not paths: return
        def loader(path):
            if not (folder / 'projet.json').is_file():
                raise ValueError('Ce projet a été supprimé ou déplacé.')
            doc=attachments.load_attachment(path)
            if doc['kind']!='text': raise ValueError("Seuls les documents textuels sont indexés.")
            project_memory.add(folder,doc['name'],doc['text'])
            return doc['name']
        self.worker=AttachmentWorker(paths,loader)
        self.worker.progress.connect(lambda i,n,name:self.doc_status.setText(f"Indexation {i}/{n} : {name}"))
        self.worker.loaded.connect(lambda results,errors:self.doc_status.setText(
            f"{len(results)} document(s) indexé(s). " + " · ".join(errors)))
        self.worker.finished.connect(self.import_finished)
        for widget in (self.project,self.import_btn,self.delete_btn): widget.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def cancel_import(self):
        if self.worker:
            self.worker.stop()
            self.doc_status.setText("Arrêt demandé après le fichier en cours ; les documents déjà indexés sont conservés.")

    def import_finished(self):
        self.worker=None
        for widget in (self.project,self.import_btn,self.delete_btn): widget.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.refresh_docs()

    def remove_doc(self):
        item=self.docs.currentItem()
        if not item or self.folder() is None: return
        try:
            project_memory.remove(self.folder(),item.data(Qt.ItemDataRole.UserRole)); self.refresh_docs()
        except Exception as e: self.doc_status.setText(str(e))

    def values(self):
        return {"name":self.name.text().strip(),"model":self.model.currentText().strip(),
                "instructions":self.instructions.toPlainText(),"mode":self.mode.currentData(),
                "num_ctx":self.ctx.value(),"temperature":self.temp.value(),
                "web":self.web.isChecked(),"code":self.code.isChecked()}

    def refresh_profiles(self, selected=""):
        self.profiles.clear()
        saved=settings.get("work_profiles")
        if saved is None:
            saved=[{"name":name,"instructions":instructions,"model":"","mode":"balanced","num_ctx":8192,
                    "temperature":.7,"code":code,"web":web} for name,instructions,code,web in (
                ("Développement","Réponds en français. Vérifie les cas limites et explique les changements.",True,False),
                ("Rédaction","Rédige en français clair, en conservant le ton demandé.",False,False),
                ("Recherche","Distingue les faits des hypothèses. Cite les sources disponibles.",False,True))]
        for profile in saved: self.profiles.addItem(profile['name'],profile)
        idx=self.profiles.findText(selected)
        if idx>=0:self.profiles.setCurrentIndex(idx)
        self.load_profile()

    def load_profile(self,*_):
        p=self.profiles.currentData() or {}
        self.name.setText(p.get('name',''))
        self.model.setCurrentText(p.get('model',''))
        self.instructions.setPlainText(p.get('instructions',''))
        self.mode.setCurrentIndex(max(0,self.mode.findData(p.get('mode','balanced'))))
        self.ctx.setValue(p.get('num_ctx',8192)); self.temp.setValue(p.get('temperature',.7))
        self.web.setChecked(p.get('web',False)); self.code.setChecked(p.get('code',False))

    def save_profile(self):
        p=self.values()
        if not p['name']:
            self.profile_status.setText("Indiquez un nom pour le profil."); return
        profiles=[self.profiles.itemData(i) for i in range(self.profiles.count()) if self.profiles.itemText(i)!=p['name']]
        profiles.append(p)
        settings.set('work_profiles',profiles); self.refresh_profiles(p['name'])
        self.profile_status.setText("Profil enregistré.")

    def delete_profile(self):
        name=self.profiles.currentText()
        profiles=[self.profiles.itemData(i) for i in range(self.profiles.count()) if self.profiles.itemText(i)!=name]
        settings.set('work_profiles',profiles); self.refresh_profiles()

    def use_profile(self):
        self.apply_profile.emit(self.values())

    def set_models(self, refs):
        selected=self.model.currentText()
        self.model.clear();self.model.addItems(refs);self.model.setCurrentText(selected)
