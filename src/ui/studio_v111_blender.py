from pathlib import Path
import shutil
from PyQt6.QtCore import QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,QPlainTextEdit,QMessageBox,QFormLayout,QGroupBox
from src.backend import blender_tools, blender_installer

class BlenderStudioPage(QWidget):
    def __init__(self):
        super().__init__()
        self.proc=None; self.install_proc=None
        root=QVBoxLayout(self)
        title=QLabel('Blender Studio'); title.setObjectName('Title'); root.addWidget(title)
        intro=QLabel("Blender devient la station de finition 3D d'IA Manager. Vous pouvez maintenant l'installer directement depuis cette page sous Windows.")
        intro.setWordWrap(True); root.addWidget(intro)

        box=QGroupBox("Installation Blender"); bl=QVBoxLayout(box)
        self.install_state=QLabel(); self.install_state.setWordWrap(True); bl.addWidget(self.install_state)
        ar=QHBoxLayout()
        self.install_btn=QPushButton("Installer Blender"); self.install_btn.setObjectName("Primary"); self.install_btn.clicked.connect(self.install_blender)
        self.upgrade_btn=QPushButton("Mettre à jour Blender"); self.upgrade_btn.clicked.connect(self.upgrade_blender)
        official=QPushButton("Page officielle"); official.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(blender_installer.BLENDER_DOWNLOAD_URL)))
        ar.addWidget(self.install_btn); ar.addWidget(self.upgrade_btn); ar.addWidget(official); ar.addStretch(1); bl.addLayout(ar)
        root.addWidget(box)

        form=QFormLayout()
        er=QHBoxLayout(); self.executable=QLineEdit(blender_tools.detect_blender())
        browse=QPushButton('Blender…'); browse.clicked.connect(self.choose_executable)
        detect=QPushButton('Détecter'); detect.clicked.connect(self.detect)
        er.addWidget(self.executable,1); er.addWidget(browse); er.addWidget(detect); form.addRow('Exécutable Blender',er)
        pr=QHBoxLayout(); self.projects=QLineEdit(str(blender_tools.project_root()))
        pb=QPushButton('Dossier…'); pb.clicked.connect(self.choose_projects)
        ps=QPushButton('Utiliser'); ps.clicked.connect(self.save_projects)
        pr.addWidget(self.projects,1); pr.addWidget(pb); pr.addWidget(ps); form.addRow('Projets Blender',pr)
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
        pick=QPushButton('Source…'); pick.clicked.connect(self.choose_source); self.output_format=QComboBox()
        for fmt in blender_tools.SUPPORTED_EXPORTS: self.output_format.addItem(fmt.upper(),fmt)
        cv=QPushButton('Convertir'); cv.clicked.connect(self.convert)
        conv.addWidget(self.source,1); conv.addWidget(pick); conv.addWidget(self.output_format); conv.addWidget(cv); root.addLayout(conv)

        root.addWidget(QLabel('Nettoyer / consolider une scène .blend'))
        cr=QHBoxLayout(); self.clean_source=QLineEdit()
        cb=QPushButton('Fichier .blend…'); cb.clicked.connect(self.choose_blend)
        clean=QPushButton('Créer une copie nettoyée'); clean.clicked.connect(self.clean_blend)
        cr.addWidget(self.clean_source,1); cr.addWidget(cb); cr.addWidget(clean); root.addLayout(cr)

        act=QHBoxLayout(); stop=QPushButton("Arrêter l'action Blender"); stop.clicked.connect(self.stop)
        op=QPushButton('Ouvrir le dossier projets'); op.clicked.connect(self.open_projects)
        act.addWidget(stop); act.addWidget(op); act.addStretch(1); root.addLayout(act)
        self.status=QLabel('Prêt.'); self.status.setWordWrap(True); root.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(3000); root.addWidget(self.log,1)
        self.refresh_install_state()

    def refresh_install_state(self):
        path=blender_tools.detect_blender()
        if path and not self.executable.text().strip(): self.executable.setText(path)
        self.install_state.setText(blender_installer.status_text(path))
        self.install_btn.setEnabled(not bool(path) and blender_installer.can_auto_install() and self.install_proc is None)
        self.upgrade_btn.setEnabled(bool(path) and blender_installer.can_auto_install() and self.install_proc is None)

    def start_install_process(self,command,label):
        if self.install_proc is not None: return
        p=QProcess(self); self.install_proc=p; p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_install_output)
        p.finished.connect(lambda code,status:self.install_finished(p,code,label))
        p.errorOccurred.connect(lambda _e:self.install_process_error(p,label))
        self.status.setText('⏳ '+label+'…'); self.log.appendPlainText('\n> '+label)
        self.install_btn.setEnabled(False); self.upgrade_btn.setEnabled(False)
        p.start(command['program'],command['args'])

    def install_blender(self):
        if blender_tools.detect_blender():
            self.status.setText('✅ Blender est déjà installé.'); self.refresh_install_state(); return
        if not blender_installer.can_auto_install():
            if QMessageBox.question(self,'Installer Blender',"WinGet n'est pas disponible. Ouvrir la page officielle de Blender ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(blender_installer.BLENDER_DOWNLOAD_URL))
            return
        if QMessageBox.question(self,'Installer Blender',"IA Manager va demander à Windows d'installer Blender avec WinGet.\n\nContinuer ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.start_install_process(blender_installer.install_command(),'Installation Blender')

    def upgrade_blender(self):
        if not blender_installer.can_auto_install(): QDesktopServices.openUrl(QUrl(blender_installer.BLENDER_DOWNLOAD_URL)); return
        self.start_install_process(blender_installer.upgrade_command(),'Mise à jour Blender')

    def read_install_output(self):
        if self.install_proc: self.log.insertPlainText(bytes(self.install_proc.readAllStandardOutput()).decode('utf-8',errors='replace'))

    def install_finished(self,p,code,label):
        if self.install_proc is not p:return
        self.read_install_output(); self.install_proc=None; p.deleteLater()
        path=blender_tools.detect_blender()
        if code==0 and path:
            try: path=blender_tools.set_executable(path); self.executable.setText(path)
            except Exception: pass
            self.status.setText('✅ Blender installé et détecté automatiquement.')
        elif code==0: self.status.setText('✅ WinGet a terminé. Utilisez Détecter si nécessaire.')
        else: self.status.setText(f'❌ {label} a échoué (code {code}).')
        self.refresh_install_state()
    def install_process_error(self,p,label):
        if self.install_proc is not p:return
        self.status.setText('❌ '+label+' : '+p.errorString())
        if p.state()==QProcess.ProcessState.NotRunning:
            self.install_proc=None
            p.deleteLater()
            self.refresh_install_state()

    def detect(self):
        path=blender_tools.detect_blender()
        if path:
            self.executable.setText(path)
            try: blender_tools.set_executable(path)
            except Exception: pass
            self.status.setText('✅ Blender détecté : '+path)
        else:self.status.setText('Blender non détecté. Utilisez Installer Blender.')
        self.refresh_install_state()

    def choose_executable(self):
        path,_=QFileDialog.getOpenFileName(self,'Choisir Blender',str(Path.home()),'Blender (blender.exe);;Tous les fichiers (*)')
        if path:
            try:self.executable.setText(blender_tools.set_executable(path)); self.status.setText('✅ Blender enregistré.'); self.refresh_install_state()
            except Exception as exc: QMessageBox.warning(self,'Blender',str(exc))

    def choose_projects(self):
        path=QFileDialog.getExistingDirectory(self,'Dossier des projets Blender',self.projects.text())
        if path:self.projects.setText(path)
    def save_projects(self):
        try:self.projects.setText(blender_tools.set_project_root(self.projects.text())); self.status.setText('✅ Dossier des projets enregistré.')
        except Exception as exc:QMessageBox.warning(self,'Blender',str(exc))
    def current_executable(self):
        value=self.executable.text().strip() or blender_tools.detect_blender(); self.executable.setText(value)
        if not value: raise ValueError("Blender n'est pas configuré. Utilisez Installer Blender ou Détecter.")
        return blender_tools.set_executable(value)
    def run(self,command,label):
        if self.proc is not None:return
        p=QProcess(self); self.proc=p
        if command.get('cwd'):p.setWorkingDirectory(command['cwd'])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output); p.finished.connect(lambda code,status:self.finished(p,code,label))
        p.errorOccurred.connect(lambda _e:self.process_error(p,label))
        self.status.setText('⏳ '+label+'…'); self.log.appendPlainText('\n> '+label); p.start(command['program'],command['args'])
    def read_output(self):
        if self.proc:self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode('utf-8',errors='replace'))
    def finished(self,p,code,label):
        if self.proc is not p:return
        self.read_output(); self.proc=None; p.deleteLater(); self.status.setText(('✅ ' if code==0 else '❌ ')+label+f' · code {code}')
        if label=='Diagnostic Blender' and code==0:
            for line in reversed(self.log.toPlainText().splitlines()):
                if line.lower().startswith('blender '): self.version.setText(line); break
    def process_error(self,p,label):
        if self.proc is not p:return
        self.status.setText('❌ '+label+' : '+p.errorString())
        if p.state()==QProcess.ProcessState.NotRunning:
            self.proc=None
            p.deleteLater()
    def test_blender(self):
        try:self.run(blender_tools.version_command(self.current_executable()),'Diagnostic Blender')
        except Exception as exc:QMessageBox.warning(self,'Blender',str(exc))
    def launch_blender(self):
        try:
            cmd=blender_tools.launch_command(self.current_executable()); QProcess.startDetached(cmd['program'],cmd['args'],cmd['cwd']); self.status.setText('✅ Blender lancé.')
        except Exception as exc:QMessageBox.warning(self,'Blender',str(exc))
    def create_template(self):
        try:
            blender_tools.set_project_root(self.projects.text()); folder=blender_tools.create_project_directory(self.project_name.text())
            script=blender_tools.template_script(folder,self.template.currentData()); self.run(blender_tools.headless_script_command(self.current_executable(),script),'Création du projet Blender')
        except Exception as exc:QMessageBox.warning(self,'Blender',str(exc))
    def choose_source(self):
        path,_=QFileDialog.getOpenFileName(self,'Asset 3D',str(Path.home()),'3D (*.glb *.gltf *.fbx *.obj *.stl *.ply)')
        if path:self.source.setText(path)
    def convert(self):
        try:
            src=Path(self.source.text()).expanduser()
            if not src.is_file():raise ValueError('Choisissez un asset 3D source.')
            fmt=self.output_format.currentData(); default=src.with_name(src.stem+'_converti.'+fmt); dst,_=QFileDialog.getSaveFileName(self,'Fichier converti',str(default))
            if not dst:return
            if not Path(dst).suffix:dst+='.'+fmt
            script=blender_tools.conversion_script(str(src),dst); self.run(blender_tools.headless_script_command(self.current_executable(),script),'Conversion 3D')
        except Exception as exc:QMessageBox.warning(self,'Conversion 3D',str(exc))
    def choose_blend(self):
        path,_=QFileDialog.getOpenFileName(self,'Scène Blender',str(Path.home()),'Blender (*.blend)')
        if path:self.clean_source.setText(path)
    def clean_blend(self):
        try:
            src=Path(self.clean_source.text()).expanduser()
            if not src.is_file():raise ValueError('Choisissez une scène .blend.')
            dst=src.with_name(src.stem+'_nettoye.blend'); script=blender_tools.clean_script(str(src),str(dst))
            self.run(blender_tools.headless_script_command(self.current_executable(),script,str(src)),'Nettoyage Blender')
        except Exception as exc:QMessageBox.warning(self,'Blender',str(exc))
    def open_projects(self):
        folder=Path(self.projects.text()).expanduser(); folder.mkdir(parents=True,exist_ok=True)
        if shutil.which('explorer'):QProcess.startDetached('explorer',[str(folder)])
        else:self.status.setText('Dossier projets : '+str(folder))
    def stop(self):
        if self.proc:self.proc.kill(); self.status.setText('⏹ Arrêt demandé.')
    def shutdown(self):
        for p in (self.proc,self.install_proc):
            if p:p.kill(); p.waitForFinished(1000)
        self.proc=None; self.install_proc=None
