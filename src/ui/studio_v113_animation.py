
from pathlib import Path
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,
    QComboBox,QSpinBox,QPlainTextEdit,QMessageBox
)
from src.backend import blender_animation

class BlenderAnimationPage(QWidget):
    def __init__(self, blender_page):
        super().__init__()
        self.blender_page=blender_page
        self.proc=None
        root=QVBoxLayout(self)
        title=QLabel("Animation & Retargeting"); title.setObjectName("Title"); root.addWidget(title)
        intro=QLabel(
            "Ajoutez des animations de base à un rig IA Manager, retargetez une animation depuis une autre scène Blender "
            "et exportez le personnage animé en GLB ou FBX."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        srcrow=QHBoxLayout()
        self.target=QLineEdit(); self.target.setPlaceholderText("Personnage cible .blend")
        pick=QPushButton("Cible…"); pick.clicked.connect(self.choose_target)
        srcrow.addWidget(self.target,1); srcrow.addWidget(pick); root.addLayout(srcrow)

        animrow=QHBoxLayout()
        self.animation=QComboBox()
        for key,data in blender_animation.ANIMATIONS.items():
            self.animation.addItem(f"{data['name']} · {data['frames']} frames",key)
        create=QPushButton("Créer animation de base"); create.clicked.connect(self.create_animation)
        inspect=QPushButton("Analyser animations"); inspect.clicked.connect(self.inspect_animation)
        animrow.addWidget(self.animation,1); animrow.addWidget(create); animrow.addWidget(inspect); root.addLayout(animrow)

        root.addWidget(QLabel("Retargeting depuis une autre scène"))
        retrow=QHBoxLayout()
        self.source=QLineEdit(); self.source.setPlaceholderText("Scène source animée .blend")
        source_btn=QPushButton("Source…"); source_btn.clicked.connect(self.choose_source)
        self.start=QSpinBox(); self.start.setRange(1,100000); self.start.setValue(1)
        self.end=QSpinBox(); self.end.setRange(1,100000); self.end.setValue(120)
        ret=QPushButton("Retarget + bake"); ret.clicked.connect(self.retarget)
        retrow.addWidget(self.source,1); retrow.addWidget(source_btn)
        retrow.addWidget(QLabel("Début")); retrow.addWidget(self.start)
        retrow.addWidget(QLabel("Fin")); retrow.addWidget(self.end); retrow.addWidget(ret)
        root.addLayout(retrow)

        exrow=QHBoxLayout()
        self.format=QComboBox(); self.format.addItem("GLB animé","glb"); self.format.addItem("FBX animé","fbx")
        export=QPushButton("Exporter personnage animé"); export.clicked.connect(self.export_animated)
        stop=QPushButton("Arrêter"); stop.clicked.connect(self.stop)
        exrow.addWidget(self.format); exrow.addWidget(export); exrow.addWidget(stop); exrow.addStretch(1)
        root.addLayout(exrow)

        self.status=QLabel("Prêt."); self.status.setWordWrap(True); root.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(4000); root.addWidget(self.log,1)

    def executable(self):
        return self.blender_page.current_executable()

    def choose_target(self):
        path,_=QFileDialog.getOpenFileName(self,"Personnage cible",str(Path.home()),"Blender (*.blend)")
        if path:self.target.setText(path)

    def choose_source(self):
        path,_=QFileDialog.getOpenFileName(self,"Animation source",str(Path.home()),"Blender (*.blend)")
        if path:self.source.setText(path)

    def target_path(self):
        p=Path(self.target.text()).expanduser()
        if not p.is_file() or p.suffix.lower()!=".blend":
            raise ValueError("Choisissez un personnage cible .blend.")
        return p.resolve()

    def run_script(self,script,label,blend=None):
        if self.proc is not None:
            QMessageBox.information(self,"Animation","Une opération est déjà en cours."); return
        blend=str(blend or self.target_path())
        cmd=blender_animation.command(self.executable(),script,blend)
        p=QProcess(self); self.proc=p
        p.setWorkingDirectory(cmd["cwd"]); p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(lambda code,status:self.finished(p,code,label))
        p.errorOccurred.connect(lambda _e:self.status.setText("❌ "+p.errorString()))
        self.status.setText("⏳ "+label+"…"); self.log.appendPlainText("\n> "+label)
        p.start(cmd["program"],cmd["args"])

    def read_output(self):
        if self.proc:self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8",errors="replace"))

    def finished(self,p,code,label):
        if self.proc is not p:return
        self.read_output(); self.proc=None; p.deleteLater()
        self.status.setText(("✅ " if code==0 else "❌ ")+label+f" · code {code}")

    def create_animation(self):
        try:
            src=self.target_path(); key=self.animation.currentData()
            dst=src.with_name(src.stem+"_"+key+".blend")
            script=blender_animation.procedural_animation_script(str(src),str(dst),key)
            self.run_script(script,"Création "+blender_animation.ANIMATIONS[key]["name"],src)
        except Exception as exc: QMessageBox.warning(self,"Animation",str(exc))

    def inspect_animation(self):
        try:
            src=self.target_path()
            script=blender_animation.animation_info_script(str(src))
            self.run_script(script,"Analyse des animations",src)
        except Exception as exc: QMessageBox.warning(self,"Animation",str(exc))

    def retarget(self):
        try:
            target=self.target_path()
            source=Path(self.source.text()).expanduser()
            if not source.is_file() or source.suffix.lower()!=".blend":
                raise ValueError("Choisissez une scène source animée .blend.")
            dst=target.with_name(target.stem+"_retarget.blend")
            script=blender_animation.retarget_script(str(target),str(source),str(dst),self.start.value(),self.end.value())
            self.run_script(script,"Retargeting",target)
        except Exception as exc: QMessageBox.warning(self,"Retargeting",str(exc))

    def export_animated(self):
        try:
            src=self.target_path(); fmt=self.format.currentData()
            default=src.with_name(src.stem+"_anime."+fmt)
            dst,_=QFileDialog.getSaveFileName(self,"Export animé",str(default))
            if not dst:return
            script=blender_animation.export_animated_script(str(src),dst,fmt)
            self.run_script(script,"Export animé "+fmt.upper(),src)
        except Exception as exc: QMessageBox.warning(self,"Export animé",str(exc))

    def stop(self):
        if self.proc:self.proc.kill(); self.status.setText("⏹ Arrêt demandé.")

    def shutdown(self):
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
