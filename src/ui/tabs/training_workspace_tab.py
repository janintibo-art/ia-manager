"""Préparation des exemples et consultation des expériences locales."""
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QPlainTextEdit,
    QFileDialog, QFormLayout, QSplitter)
from src.backend import training_lab as lab, training_workspace as ws


class ExamplesEditor(QWidget):
    dataset_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self)
        text=QLabel('Préparez des questions et des réponses relues. Enregistrez une nouvelle copie pour l’entraînement. '
                   'Les doublons exacts sont retirés ; les réponses différentes à une même question restent à vérifier.')
        text.setWordWrap(True); layout.addWidget(text)
        row=QHBoxLayout()
        for label, slot in (('Importer JSONL…',self.import_file),('Nouvel exemple',self.new_example),
                            ('Supprimer la sélection',self.remove_example)):
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        layout.addLayout(row)
        self.table=QTableWidget(0,2)
        self.table.setHorizontalHeaderLabels(['Question / consigne','Réponse'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.load_selected)
        layout.addWidget(self.table,1)
        form=QFormLayout()
        self.question=QPlainTextEdit(); self.context=QPlainTextEdit(); self.answer=QPlainTextEdit()
        for label,widget in (('Question',self.question),('Contexte facultatif',self.context),('Réponse attendue',self.answer)):
            widget.setMaximumHeight(85); form.addRow(label,widget)
        layout.addLayout(form)
        self.current=-1
        self.rows=[]
        for widget in (self.question,self.context,self.answer):widget.textChanged.connect(self.update_current)
        button=QPushButton('Enregistrer une copie et utiliser pour l’entraînement')
        button.clicked.connect(self.save); layout.addWidget(button)
        self.status=QLabel('0 exemple — ajoutez une première question. Minimum 10 exemples distincts pour entraîner.')
        self.status.setWordWrap(True); layout.addWidget(self.status)

    def refresh(self, selected=-1):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.rows))
        for i,row in enumerate(self.rows):
            self.table.setItem(i,0,QTableWidgetItem(row['instruction'][:160]))
            self.table.setItem(i,1,QTableWidgetItem(row['output'][:160]))
        self.table.blockSignals(False)
        self.current=-1
        if 0<=selected<len(self.rows):
            self.table.selectRow(selected)
            self.load_selected()
        else:
            self.table.clearSelection(); self.load_selected()
        self.status.setText(f'{len(self.rows)} exemple(s). Minimum 10 exemples distincts pour entraîner.')

    def load_selected(self):
        self.current=self.table.currentRow() if self.table.selectedItems() else -1
        row=self.rows[self.current] if 0<=self.current<len(self.rows) else {}
        for key,widget in (('instruction',self.question),('input',self.context),('output',self.answer)):
            widget.blockSignals(True); widget.setPlainText(row.get(key,'')); widget.blockSignals(False)
            widget.setEnabled(self.current>=0)

    def update_current(self):
        if not 0<=self.current<len(self.rows):return
        row=dict(instruction=self.question.toPlainText(),input=self.context.toPlainText(),output=self.answer.toPlainText())
        self.rows[self.current]=row
        self.table.item(self.current,0).setText(row['instruction'][:160])
        self.table.item(self.current,1).setText(row['output'][:160])
        self.status.setText(f'{len(self.rows)} exemple(s) — modifications en mémoire, cliquez sur Enregistrer.')

    def new_example(self):
        if len(self.rows) >= 2000:
            self.status.setText('Éditeur limité à 2000 exemples.');return
        self.rows.append(dict(instruction='',input='',output=''))
        self.refresh(len(self.rows)-1)
        self.question.setFocus()

    def remove_example(self):
        if 0<=self.current<len(self.rows):
            i=self.current; self.rows.pop(i); self.refresh(min(i,len(self.rows)-1))

    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Ajouter des exemples JSONL','','JSONL (*.jsonl)')
        if not path:return
        try:
            imported=lab.read_dataset(path,minimum=1)
            if len(self.rows)+len(imported)>2000:
                raise ValueError('Éditeur limité à 2000 exemples. Les grands JSONL restent utilisables dans Entraînement.')
            self.rows.extend(imported)
            self.refresh(len(self.rows)-len(imported))
        except Exception as exc:self.status.setText(str(exc))

    def save(self):
        try:
            path,count=ws.save_examples(self.rows)
            self.status.setText(f'{count} exemples distincts enregistrés : {path.name}. '+
                ('Prêt pour un essai.' if count>=10 else 'Brouillon enregistré ; ajouter des exemples avant un essai.'))
            self.dataset_ready.emit(str(path))
        except Exception as exc:self.status.setText(str(exc))


class TrainingHistory(QWidget):
    result_selected = pyqtSignal(str, str)

    def __init__(self, active_job):
        super().__init__()
        self.active_job=active_job
        self.items=[]
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(['Expérience','Action','Statut','Modèle'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_details)
        layout.addWidget(self.table,2)
        self.details=QPlainTextEdit(); self.details.setReadOnly(True); layout.addWidget(self.details,1)
        row=QHBoxLayout()
        for label,slot in (('Actualiser',self.refresh),('Ouvrir le dossier',self.open_folder),
                           ('Préparer import Ollama',lambda:self.select_result('ollama')),
                           ('Utiliser pour fusion A',lambda:self.select_result('a')),
                           ('Utiliser pour fusion B',lambda:self.select_result('b'))):
            if label == 'Utiliser pour fusion A':
                layout.addLayout(row); row=QHBoxLayout()
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        layout.addLayout(row)
        hint=QLabel('200 expériences récentes. Une baisse de loss ne garantit pas de meilleures réponses. '
                    'Les essais courts ne produisent pas de modèle final.')
        hint.setWordWrap(True);layout.addWidget(hint)
        self.refresh()

    def selected(self):
        row=self.table.currentRow()
        return self.items[row] if 0<=row<len(self.items) else None

    def refresh(self):
        previous=self.selected()
        try:self.items=ws.history(self.active_job())
        except OSError as exc:self.details.setPlainText(str(exc));return
        self.table.blockSignals(True);self.table.setRowCount(len(self.items))
        statuses=dict(success='Terminé',failed='Échec',cancelled='Arrêté',running='En cours',incomplete='Incomplet')
        actions=dict(train='Entraînement',merge='Fusion',trial='Essai court',diagnostic='Diagnostic')
        for i,item in enumerate(self.items):
            cfg=item['config']
            for j,value in enumerate((item['path'].name,actions.get(cfg.get('action'),'?'),
                                      statuses.get(item['status'],'Inconnu'),cfg.get('model',''))):
                self.table.setItem(i,j,QTableWidgetItem(str(value)))
        self.table.blockSignals(False)
        if self.items:
            index=next((i for i,x in enumerate(self.items) if previous and x['path']==previous['path']),0)
            self.table.selectRow(index)
        self.show_details()

    def show_details(self):
        item=self.selected()
        if not item:self.details.setPlainText('Aucune expérience sélectionnée.');return
        cfg=item['config'];ev=item['evaluation'];trial=item['trial']
        lines=[str(item['path']), 'Modèle : '+cfg.get('model',''), 'Action : '+cfg.get('action','')]
        if cfg.get('action')=='merge':
            lines.extend(['Modèle B : '+cfg.get('other',''), 'Méthode : '+cfg.get('merge_method','linear'),
                          'Part B : '+str(cfg.get('weight','.5'))])
        else:lines.append('Réglages : '+str(cfg.get('tuning',{})))
        before=ev.get('before',{});after=ev.get('after',{})
        if isinstance(before,dict) and isinstance(after,dict) and ev:
            lines.append('Loss validation avant / après : '+ws.metric(before.get('eval_loss'))+' / '+ws.metric(after.get('eval_loss')))
        if trial:lines.append('Pic VRAM PyTorch alloué : '+ws.metric(trial.get('peak_allocated_gb'))+' Go')
        lines.append('Modèle final disponible : '+('oui' if item['model_ready'] else 'non'))
        self.details.setPlainText('\n'.join(lines))

    def open_folder(self):
        item=self.selected()
        if item:QDesktopServices.openUrl(QUrl.fromLocalFile(str(item['path'])))

    def select_result(self,target):
        item=self.selected()
        if not item or not item['model_ready']:
            self.details.appendPlainText('Sélectionnez une tâche réussie avec un modèle complet.');return
        self.result_selected.emit(target,str(item['path']/'model'))
