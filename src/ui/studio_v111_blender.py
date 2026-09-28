from pathlib import Path
import shutil
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,QPlainTextEdit,QMessageBox,QFormLayout
from src.backend import blender_tools

class BlenderStudioPage(QWidget):
    def __init__(self):
        super().__init__()
        self.proc=None
        root=QVBoxLayout(self)
        title=QLabel('Blender Studio'); title.setObjectName('Title'); root.addWidget(title)
        intro=QLabel("Blender devient la station de finition 3D d'IA Manager : scènes de départ, conversion d'assets et traitements headless.")
        intro.setWordWrap(True); root.addWidget(intro)
        form=QFormLayout()
        exe_row=QHBoxLayout(); self.executable=QLineEdit(blender_tools.detect_blender())
        browse=QPushButton('Blender…'); browse.clicked.connect(self.choose_executable)
        detect=QPushButton('Détecter'); detect.clicked.connect(self.detect)
        exe_row.addWidget(self.executable,1); exe_row.addWidget(browse); exe_row.addWidget(detect); form.addRow('Exécutable Blender',exe_row)
        project_row=QHBoxLayout(); self.projects=QLineEdit(str(blender_tools.project_root()))
        choose_project=QPushButton('Dossier…'); choose_project.clicked.connect(self.choose_projects)
        save_project=QPushButton('Utiliser'); save_project.clicked.connect(self.save_projects)
        project_row.addWidget(self.projects,1); project_row.addWidget(choose_project); project_row.addWidget(save_project); form.addRow('Projets Blender',project_row)
        root.addLayout(form)
        diag=QHBoxLayout(); self.version=QLabel('Version non testée.')
        test=QPushButton('Tester Blender'); test.clicked.connect(self.test_blender)
        launch=QPushButton('Ouvrir Blender'); launch.clicked.connect(self.launch_blender)
        diag.addWidget(self.version,1); diag.addWidget(test); diag.addWidget(launch); root.addLayout(diag)
        root.addWidget(QLabel('Créer une scène de départ'))
        row=QHBoxLayout(); self.project_name=QLineEdit('nouveau_projet_3d'); self.template=QComboBox()
        self.template.addItem('Personnage / rig','personnage'); self.template.addItem('Objet / prop','objet'); self.template.addItem('Environnement','environnement')
        create=QPushButton('Créer le projet .blend'); create.clicked.connect(self.create_template)
        row.addWidget(self.project_name,1); row.addWidget(self.template); row.addWidget(create); root.addLayout(row)
        root.addWidget(QLabel('Convertisseur 3D headless'))
        conv=QHBoxLayout(); self.source=QLineEdit(); self.source.setPlaceholderText('GLB / GLTF / FBX / OBJ / STL / PLY')
        pick_source=QPushButton('Source…'); pick_source.clicked.connect(self.choose_source); self.output_format=QComboBox()
        for fmt in blender_tools.SUPPORTED_EXPORTS: self.output_format.addItem(fmt.upper(),fmt)
        convert=QPushButton('Convertir'); convert.clicked.connect(self.convert)
        conv.addWidget(self.source,1); conv.addWidget(pick_source); conv.addWidget(self.output_format); conv.addWidget(convert); root.addLayout(conv)
        root.addWidget(QLabel('Nettoyer / consolider une scène .blend'))
        cleanrow=QHBoxLayout(); self.clean_source=QLineEdit(); pick_blend=QPushButton('Fichier .blend…'); pick_blend.clicked.connect(self.choose_blend)
        clean=QPushButton('Créer une copie nettoyée'); clean.clicked.connect(self.clean_blend)
        cleanrow.addWidget(self.clean_source,1); cleanrow.addWidget(pick_blend); cleanrow.addWidget(clean); root.addLayout(cleanrow)
        actions=QHBoxLayout(); stop=QPushButton("Arrêter l'action Blender"); stop.clicked.connect(self.stop)
        open_projects=QPushButton('Ouvrir le dossier projets'); open_projects.clicked.connect(self.open_projects)
        actions.addWidget(stop); actions.addWidget(open_projects); actions.addStretch(1); root.addLayout(actions)
        self.status=QLabel('Prêt.'); self.status.setWordWrap(True); root.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(3000); root.addWidget(self.log,1)

    def detect(self):
        path=blender_tools.detect_blender()
        if path: self.executable.setText(path); self.status.setText('✅ Blender détecté : '+path)
        else: self.status.setText('Blender non détecté automatiquement. Sélectionnez blender.exe.')

    def choose_executable(self):
        path,_=QFileDialog.getOpenFileName(self,'Choisir Blender',str(Path.home()),'Blender (blender.exe);;Tous les fichiers (*)')
        if path:
            try: self.executable.setText(blender_tools.set_executable(path)); self.status.setText('✅ Blender enregistré.')
            except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def choose_projects(self):
        path=QFileDialog.getExistingDirectory(self,'Dossier des projets Blender',self.projects.text())
        if path: self.projects.setText(path)

    def save_projects(self):
        try: self.projects.setText(blender_tools.set_project_root(self.projects.text())); self.status.setText('✅ Dossier des projets enregistré.')
        except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def current_executable(self):
        value=self.executable.text().strip() or blender_tools.detect_blender(); self.executable.setText(value)
        if not value: raise ValueError("Blender n'est pas configuré.")
        return blender_tools.set_executable(value)

    def run(self,command,label):
        if self.proc is not None: QMessageBox.information(self,'Blender','Une action Blender est déjà en cours.'); return
        p=QProcess(self); self.proc=p
        if command.get('cwd'): p.setWorkingDirectory(command['cwd'])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output); p.finished.connect(lambda code,status:self.finished(p,code,label))
        p.errorOccurred.connect(lambda _e:self.status.setText('❌ '+p.errorString()))
        self.status.setText('⏳ '+label+'…'); self.log.appendPlainText('\n> '+label); p.start(command['program'],command['args'])

    def read_output(self):
        if self.proc: self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode('utf-8',errors='replace'))

    def finished(self,process,code,label):
        if self.proc is not process:return
        self.read_output(); self.proc=None; process.deleteLater(); self.status.setText(('✅ ' if code==0 else '❌ ')+label+f' · code {code}')
        if label=='Diagnostic Blender' and code==0:
            for line in reversed(self.log.toPlainText().splitlines()):
                if line.lower().startswith('blender '): self.version.setText(line); break

    def test_blender(self):
        try: self.run(blender_tools.version_command(self.current_executable()),'Diagnostic Blender')
        except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def launch_blender(self):
        try:
            cmd=blender_tools.launch_command(self.current_executable()); QProcess.startDetached(cmd['program'],cmd['args'],cmd['cwd']); self.status.setText('✅ Blender lancé.')
        except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def create_template(self):
        try:
            blender_tools.set_project_root(self.projects.text()); folder=blender_tools.create_project_directory(self.project_name.text())
            script=blender_tools.template_script(folder,self.template.currentData()); self.run(blender_tools.headless_script_command(self.current_executable(),script),'Création du projet Blender')
        except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def choose_source(self):
        path,_=QFileDialog.getOpenFileName(self,'Asset 3D',str(Path.home()),'3D (*.glb *.gltf *.fbx *.obj *.stl *.ply)')
        if path:self.source.setText(path)

    def convert(self):
        try:
            src=Path(self.source.text()).expanduser()
            if not src.is_file(): raise ValueError('Choisissez un asset 3D source.')
            fmt=self.output_format.currentData(); default=src.with_name(src.stem+'_converti.'+fmt); dst,_=QFileDialog.getSaveFileName(self,'Fichier converti',str(default))
            if not dst:return
            if not Path(dst).suffix:dst+='.'+fmt
            script=blender_tools.conversion_script(str(src),dst); self.run(blender_tools.headless_script_command(self.current_executable(),script),'Conversion 3D')
        except Exception as exc: QMessageBox.warning(self,'Conversion 3D',str(exc))

    def choose_blend(self):
        path,_=QFileDialog.getOpenFileName(self,'Scène Blender',str(Path.home()),'Blender (*.blend)')
        if path:self.clean_source.setText(path)

    def clean_blend(self):
        try:
            src=Path(self.clean_source.text()).expanduser()
            if not src.is_file():raise ValueError('Choisissez une scène .blend.')
            dst=src.with_name(src.stem+'_nettoye.blend'); script=blender_tools.clean_script(str(src),str(dst))
            self.run(blender_tools.headless_script_command(self.current_executable(),script,str(src)),'Nettoyage Blender')
        except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def open_projects(self):
        folder=Path(self.projects.text()).expanduser(); folder.mkdir(parents=True,exist_ok=True)
        if shutil.which('explorer'): QProcess.startDetached('explorer',[str(folder)])
        else:self.status.setText('Dossier projets : '+str(folder))

    def stop(self):
        if self.proc:self.proc.kill(); self.status.setText('⏹ Arrêt demandé.')

    def shutdown(self):
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
