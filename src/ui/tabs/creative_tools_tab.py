"""Installation et démarrage explicites des moteurs locaux, sans shell."""
import codecs
import os
from pathlib import Path
import shutil
from PyQt6.QtCore import QLockFile, QProcess, QProcessEnvironment, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QCheckBox, QPlainTextEdit, QFileDialog)
from src.backend import creative_tools as tools, settings


class CreativeToolsTab(QWidget):
    engine_started = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.process=None;self.steps=[];self.lock=None;self.logfile=None
        self.stopping=False;self.active=None;self.mode='';self.decoder=None
        root=QVBoxLayout(self)
        intro=QLabel('Installez chaque moteur dans son environnement séparé, puis démarrez-le sur ce PC.\n'
                     'L’installation télécharge du code et des dépendances (plusieurs Go). Les modèles restent à préparer dans le moteur.')
        intro.setWordWrap(True);root.addWidget(intro)
        form=QFormLayout()
        self.choice=QComboBox()
        for key,tool in tools.TOOLS.items():self.choice.addItem(tool['name'],key)
        form.addRow('Outil',self.choice)
        self.info=QLabel();self.info.setWordWrap(True);form.addRow(self.info)
        self.directory=QLineEdit(str(settings.get('creative_tools_root') or Path.home()/'IA Manager'/'Outils'))
        self.pick_root=QPushButton('Parcourir…');self.pick_root.clicked.connect(self.choose_root)
        row=QHBoxLayout();row.addWidget(self.directory);row.addWidget(self.pick_root);form.addRow('Dossier des outils',row)
        self.python=QLineEdit();self.python.setPlaceholderText('Sélectionner python.exe, pas IA Manager.exe')
        self.pick_python=QPushButton('Parcourir…');self.pick_python.clicked.connect(self.choose_python)
        row=QHBoxLayout();row.addWidget(self.python);row.addWidget(self.pick_python);form.addRow('Python de départ',row)
        self.hardware=QComboBox();self.hardware.addItem('NVIDIA — CUDA (pilote compatible requis)','nvidia');self.hardware.addItem('CPU — lent, texture 3D non prise en charge','cpu')
        form.addRow('Profil PyTorch',self.hardware)
        self.offline=QCheckBox('Démarrer hors ligne : utiliser les poids déjà téléchargés')
        self.offline.setChecked(True);form.addRow(self.offline)
        hint=QLabel('Premier essai : décocher le mode hors ligne pour télécharger les poids manquants. Ensuite arrêter et relancer hors ligne.\n'
                    'AMD/Intel/Apple : utiliser l’installation officielle adaptée ; les recettes automatiques ci-dessous ciblent CPU et NVIDIA.')
        hint.setWordWrap(True);form.addRow(hint);root.addLayout(form)
        prereqs=QHBoxLayout()
        for title,url in (('Installer Python','https://www.python.org/downloads/'),('Installer Git','https://git-scm.com/downloads'),
                          ('Outils C++ Windows','https://visualstudio.microsoft.com/visual-cpp-build-tools/'),('CUDA Toolkit','https://developer.nvidia.com/cuda-downloads')):
            b=QPushButton(title);b.clicked.connect(lambda checked=False,u=url:QDesktopServices.openUrl(QUrl(u)));prereqs.addWidget(b)
        root.addLayout(prereqs)
        actions=QHBoxLayout()
        self.install=QPushButton('Installer / reprendre');self.install.clicked.connect(self.install_tool)
        self.diagnose=QPushButton('Diagnostic');self.diagnose.clicked.connect(self.diagnostic)
        self.start=QPushButton('Démarrer');self.start.clicked.connect(self.start_tool)
        self.stop=QPushButton('Arrêter');self.stop.clicked.connect(self.stop_process);self.stop.setEnabled(False)
        for b in (self.install,self.diagnose,self.start,self.stop):actions.addWidget(b)
        root.addLayout(actions)
        links=QHBoxLayout()
        for title,handler in (('Ouvrir l’interface',self.open_interface),('Dossier du moteur',self.open_folder),('Guide officiel',self.open_guide)):
            b=QPushButton(title);b.clicked.connect(handler);links.addWidget(b)
        root.addLayout(links)
        self.status=QLabel();self.status.setWordWrap(True);root.addWidget(self.status)
        self.log=QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(1600);root.addWidget(self.log,1)
        self.choice.currentIndexChanged.connect(self.load_profile)
        self.load_profile()

    def load_profile(self):
        key=self.choice.currentData();tool=tools.TOOLS[key]
        self.info.setText(tool['python']+' · '+tool['note'])
        values=settings.get('creative_tools_profiles') or {}
        value=values.get(key,{}) if isinstance(values,dict) else {}
        self.python.setText(str(value.get('python') or ''))
        self.hardware.setCurrentIndex(max(0,self.hardware.findData(value.get('hardware','nvidia'))))
        self.refresh_status()

    def refresh_status(self):
        try:
            record=tools.read_manifest(self.directory.text(),self.choice.currentData())
            self.status.setText('État : '+record.get('state','non installé par ce gestionnaire')+' · Git : '+('détecté' if shutil.which('git') else 'à installer'))
        except Exception as exc:self.status.setText(str(exc))

    def choose_root(self):
        path=QFileDialog.getExistingDirectory(self,'Dossier des moteurs',self.directory.text())
        if path:self.directory.setText(path);self.refresh_status()

    def choose_python(self):
        path,_=QFileDialog.getOpenFileName(self,'Python externe — python.exe sous Windows',str(Path.home()))
        if path:self.python.setText(path)

    def config(self):
        root=self.directory.text().strip();key=self.choice.currentData();python=self.python.text().strip();hardware=self.hardware.currentData()
        if not root:raise ValueError('Choisissez un dossier pour les moteurs.')
        values=settings.get('creative_tools_profiles') or {}
        values=dict(values) if isinstance(values,dict) else {}
        values[key]=dict(python=python,hardware=hardware)
        settings.set('creative_tools_root',root);settings.set('creative_tools_profiles',values)
        return root,key,python,hardware

    def acquire(self,root,key):
        Path(root).expanduser().mkdir(parents=True,exist_ok=True)
        lock=QLockFile(str(Path(root).expanduser()/('.ia_manager_'+key+'.lock')))
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):raise ValueError('Cet outil est déjà utilisé par une autre instance de IA Manager.')
        self.lock=lock

    def install_tool(self):
        if self.active:return
        try:
            root,key,python,hardware=self.config()
            if not Path(python).is_file() or 'ia_manager' in Path(python).name.lower():
                raise ValueError('Sélectionnez un vrai interpréteur Python externe avec Parcourir.')
            git=shutil.which('git')
            if not git:raise ValueError('Installez Git avec le bouton ci-dessus, puis redémarrez IA Manager.')
            self.acquire(root,key)
            tools.prepare(root,key,hardware)
            steps=tools.install_plan(root,key,python,git,hardware)
            self.begin(root,key,hardware,'install',steps,False)
        except Exception as exc:self.fail_setup(exc)

    def installed_config(self):
        root,key,_,hardware=self.config();p=tools.paths(root,key)
        if not p['python'].is_file() or not p['source'].is_dir():raise ValueError('Installez d’abord le moteur dans ce dossier.')
        record=tools.read_manifest(root,key)
        return root,key,record.get('hardware',hardware)

    def diagnostic(self):
        if self.active:return
        try:
            root,key,hardware=self.installed_config();self.acquire(root,key)
            self.begin(root,key,hardware,'diagnostic',[tools.diagnostic_command(root,key)],True)
        except Exception as exc:self.fail_setup(exc)

    def start_tool(self):
        if self.active:return
        try:
            root,key,hardware=self.installed_config()
            if tools.read_manifest(root,key).get('state')!='installé — poids à préparer':
                raise ValueError('L’installation n’est pas terminée. Consultez le journal puis reprenez-la.')
            self.acquire(root,key)
            self.begin(root,key,hardware,'run',[tools.launch_command(root,key,hardware)],self.offline.isChecked())
        except Exception as exc:self.fail_setup(exc)

    def fail_setup(self,exc):
        if self.active:
            self.finish(False, 'Action impossible : '+str(exc))
            return
        if self.lock:self.lock.unlock();self.lock=None
        self.status.setText('Action impossible : '+str(exc))

    def begin(self,root,key,hardware,mode,steps,offline):
        self.active=(root,key,hardware);self.mode=mode;self.steps=list(steps);self.stopping=False
        self.env_values=tools.environment(root,key,offline)
        self.logfile=open(tools.paths(root,key)['base']/'journal.log','a',encoding='utf-8')
        self.set_busy(True);self.write_log('\n=== '+mode+' : '+tools.TOOLS[key]['name']+' ===\n')
        self.next_step()

    def set_busy(self,busy):
        for w in (self.choice,self.directory,self.python,self.pick_root,self.pick_python,self.hardware,self.offline,self.install,self.diagnose,self.start):w.setEnabled(not busy)
        self.stop.setEnabled(busy)

    def write_log(self,text):
        self.log.moveCursor(self.log.textCursor().MoveOperation.End);self.log.insertPlainText(text)
        if self.logfile:self.logfile.write(text);self.logfile.flush()

    def next_step(self):
        if self.stopping:return
        if not self.steps:
            self.finish(True);return
        step=self.steps.pop(0)
        self.status.setText(step['label'])
        self.write_log('\n> '+step['label']+'\n')
        p=QProcess(self);self.process=p
        self.decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
        env=QProcessEnvironment.systemEnvironment()
        for key,value in self.env_values.items():env.insert(key,value)
        p.setProcessEnvironment(env);p.setWorkingDirectory(step['cwd'])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda:self.read_output(p))
        p.finished.connect(lambda code,status:self.exited(p,code,status))
        p.errorOccurred.connect(lambda error:self.process_error(p,error))
        p.started.connect(lambda:self.on_started(p))
        p.start(step['program'],step['args'])

    def on_started(self,p):
        if self.process is p and self.mode=='run':
            key=self.active[1];url='http://127.0.0.1:'+str(tools.TOOLS[key]['port'])
            self.engine_started.emit(key,url)
            self.status.setText('Processus démarré. Attendez l’adresse du serveur dans le journal avant d’ouvrir l’interface.')

    def read_output(self,p):
        if self.process is p:self.write_log(self.decoder.decode(bytes(p.readAllStandardOutput())))

    def process_error(self,p,error):
        if self.process is p and error==QProcess.ProcessError.FailedToStart:
            self.write_log(p.errorString()+'\n');self.exited(p,-1,QProcess.ExitStatus.CrashExit)

    def exited(self,p,code,status):
        if self.process is not p:return
        self.read_output(p);self.write_log(self.decoder.decode(b'',final=True))
        self.process=None;p.deleteLater()
        if self.stopping:self.finish(False,'Arrêt demandé.');return
        if code!=0 or status!=QProcess.ExitStatus.NormalExit:
            self.finish(False,'Échec de l’étape (code '+str(code)+'). Consultez le journal.');return
        if self.mode=='run':self.finish(True,'Moteur arrêté.');return
        self.next_step()

    def finish(self,success,message=''):
        if self.active and self.mode=='install':
            root,key,hardware=self.active
            try:tools.write_json(tools.paths(root,key)['manifest'],dict(managed_by='IA Manager',tool=key,hardware=hardware,state='installé — poids à préparer' if success else 'installation incomplète'))
            except Exception as exc:success=False;message='Enregistrement de l’état impossible : '+str(exc)
        if self.logfile:self.logfile.close();self.logfile=None
        if self.lock:self.lock.unlock();self.lock=None
        mode=self.mode;self.active=None;self.steps=[];self.set_busy(False)
        self.status.setText(message or ('Installation et imports vérifiés. Préparez les poids dans le moteur avant l’essai hors ligne.' if mode=='install' and success else 'Diagnostic terminé.' if success else 'Action incomplète.'))

    def stop_process(self):
        self.stopping=True;self.steps=[]
        p=self.process
        if p and p.state()!=QProcess.ProcessState.NotRunning:
            if os.name=='nt':
                # Uniquement l’arbre du processus lancé par ce gestionnaire.
                killer=QProcess(self);killer.start('taskkill',['/PID',str(p.processId()),'/T','/F']);killer.waitForFinished(3000);killer.deleteLater()
            else:p.terminate()
            QTimer.singleShot(2000,lambda:self.kill_if_current(p))
        elif self.active:self.finish(False,'Arrêt demandé.')

    def kill_if_current(self,p):
        if self.process is p and p.state()!=QProcess.ProcessState.NotRunning:p.kill()

    def shutdown(self):
        p=self.process
        if p:
            self.stop_process()
            if not p.waitForFinished(3000):p.kill();p.waitForFinished(1000)
        if self.active:self.finish(False,'Arrêt de IA Manager.')

    def open_interface(self):
        key=self.choice.currentData();QDesktopServices.openUrl(QUrl('http://127.0.0.1:'+str(tools.TOOLS[key]['port'])))

    def open_folder(self):
        try:
            p=tools.paths(self.directory.text(),self.choice.currentData())['base']
            if not p.is_dir():raise ValueError('Ce dossier n’existe pas encore.')
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        except Exception as exc:self.status.setText(str(exc))

    def open_guide(self):
        QDesktopServices.openUrl(QUrl(tools.TOOLS[self.choice.currentData()]['guide']))
