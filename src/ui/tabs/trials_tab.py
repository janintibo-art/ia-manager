"""Carnet manuel des essais Obliteratus ; comparaison via les moteurs configurés."""
import uuid
from datetime import datetime
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QListWidget,QListWidgetItem,
    QLineEdit,QPlainTextEdit,QPushButton,QFileDialog,QDoubleSpinBox)
from PyQt6.QtCore import Qt
from src.backend import settings, obliteratus


class TrialsTab(QWidget):
    compare_models=pyqtSignal(str,str)

    def __init__(self):
        super().__init__()
        self.current_id=None
        lay=QVBoxLayout(self)
        note=QLabel("Carnet des essais : renseignez les paramètres et résultats obtenus dans Obliteratus. "
                    "Les champs ne sont pas récupérés automatiquement depuis son interface. "
                    "Pour comparer dans IA Manager, importez d’abord les deux modèles dans un moteur configuré.")
        note.setWordWrap(True);lay.addWidget(note)
        self.saved=QListWidget();self.saved.setMaximumHeight(100);self.saved.currentItemChanged.connect(self.load);lay.addWidget(self.saved)
        form=QFormLayout()
        self.title=QLineEdit();self.source=QLineEdit();self.result=QLineEdit();self.method=QLineEdit();self.output=QLineEdit();self.revision=QLineEdit(obliteratus.REVISION)
        self.source.setPlaceholderText('ollama::modele-original')
        self.result.setPlaceholderText('ollama::modele-modifie')
        for label,field in (("Nom de l’essai",self.title),("Modèle source",self.source),("Modèle résultat",self.result),
                            ("Méthode et paramètres",self.method),("Dossier exporté",self.output),("Version utilisée (à vérifier)",self.revision)):form.addRow(label,field)
        self.before=QDoubleSpinBox();self.after=QDoubleSpinBox()
        for field in (self.before,self.after):field.setRange(0,100000);field.setSuffix(' tokens/s')
        form.addRow('Vitesse avant (mesurée)',self.before);form.addRow('Vitesse après (mesurée)',self.after)
        lay.addLayout(form)
        row=QHBoxLayout()
        self.before_text=QPlainTextEdit();self.before_text.setPlaceholderText('Question identique et réponse avant traitement')
        self.after_text=QPlainTextEdit();self.after_text.setPlaceholderText('Réponse après traitement et observations')
        row.addWidget(self.before_text);row.addWidget(self.after_text);lay.addLayout(row)
        row=QHBoxLayout()
        for label,slot in (("Nouvel essai",self.new),("Choisir le dossier",self.choose_folder),
                           ("Enregistrer",self.save),("Comparer les modèles",self.compare)):
            b=QPushButton(label);b.clicked.connect(slot);row.addWidget(b)
        lay.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);lay.addWidget(self.status)
        self.refresh()

    def refresh(self,selected=None):
        self.saved.blockSignals(True);self.saved.clear()
        for record in settings.get('obliteratus_trials') or []:
            item=QListWidgetItem(record['title']+' · '+record['date']);item.setData(Qt.ItemDataRole.UserRole,record)
            self.saved.addItem(item)
            if record['id']==selected:self.saved.setCurrentItem(item)
        self.saved.blockSignals(False)

    def new(self):
        self.current_id=None
        for field in (self.title,self.source,self.result,self.method,self.output):field.clear()
        self.revision.setText(obliteratus.REVISION)
        self.before_text.clear();self.after_text.clear();self.before.setValue(0);self.after.setValue(0)
        self.status.setText('Nouvel essai.')

    def load(self,item,*_):
        if not item:return
        r=item.data(Qt.ItemDataRole.UserRole);self.current_id=r['id']
        for key,field in (('title',self.title),('source',self.source),('result',self.result),('method',self.method),('output',self.output),('revision',self.revision)):
            field.setText(r.get(key,''))
        self.before.setValue(r.get('before',0));self.after.setValue(r.get('after',0))
        self.before_text.setPlainText(r.get('before_text',''));self.after_text.setPlainText(r.get('after_text',''))
        self.status.setText('Révision outil enregistrée : '+r.get('revision','inconnue'))

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Dossier du modèle exporté')
        if folder:self.output.setText(folder)

    def save(self):
        if not self.title.text().strip():self.status.setText('Indiquez un nom pour cet essai.');return
        record={'id':self.current_id or uuid.uuid4().hex,'date':datetime.now().isoformat(timespec='seconds'),
                'title':self.title.text().strip(),'source':self.source.text(),'result':self.result.text(),
                'method':self.method.text(),'output':self.output.text(),'revision':self.revision.text().strip(),
                'before':self.before.value(),'after':self.after.value(),'before_text':self.before_text.toPlainText(),
                'after_text':self.after_text.toPlainText()}
        rows=[r for r in settings.get('obliteratus_trials') or [] if r['id']!=record['id']]
        if len(rows)>=100:self.status.setText('Limite de 100 essais : modifiez un essai existant.');return
        rows.append(record);settings.set('obliteratus_trials',rows);self.current_id=record['id'];self.refresh(self.current_id)
        delta=(self.after.value()/self.before.value()-1)*100 if self.before.value() else None
        self.status.setText('Essai enregistré.'+(f' Variation de vitesse : {delta:+.1f} % (mesures renseignées).' if delta is not None else ''))

    def compare(self):
        self.compare_models.emit(self.source.text().strip(),self.result.text().strip())
