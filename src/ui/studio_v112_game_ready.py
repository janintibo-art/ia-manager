
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,
    QComboBox,QDoubleSpinBox,QSpinBox,QPlainTextEdit,QMessageBox
)
from PyQt6.QtCore import QProcess
from src.backend import blender_tools, blender_game_ready

class BlenderGameReadyPage(QWidget):
    def __init__(self, blender_page):
        super().__init__()
        self.blender_page=blender_page
        self.proc=None
        root=QVBoxLayout(self)
        title=QLabel("Blender Game Ready"); title.setObjectName("Title"); root.addWidget(title)
        intro=QLabel("Optimisez une scène .blend pour le jeu : rig de base, décimation, LOD, UV, collisions, baking préparatoire et export GLB.")
        intro.setWordWrap(True); root.addWidget(intro)

        srcrow=QHBoxLayout()
        self.source=QLineEdit()
        self.source.setPlaceholderText("Scène Blender source .blend")
        pick=QPushButton("Choisir…"); pick.clicked.connect(self.choose_source)
        srcrow.addWidget(self.source,1); srcrow.addWidget(pick); root.addLayout(srcrow)

        row=QHBoxLayout()
        self.ratio=QDoubleSpinBox(); self.ratio.setRange(0.05,1.0); self.ratio.setSingleStep(0.05); self.ratio.setValue(0.5)
        dec=QPushButton("Réduire les polygones"); dec.clicked.connect(self.decimate)
        lod=QPushButton("Générer LOD0-LOD3"); lod.clicked.connect(self.generate_lods)
        uv=QPushButton("UV automatique"); uv.clicked.connect(self.auto_uv)
        row.addWidget(QLabel("Ratio")); row.addWidget(self.ratio); row.addWidget(dec); row.addWidget(lod); row.addWidget(uv)
        root.addLayout(row)

        row2=QHBoxLayout()
        rig=QPushButton("Auto-rig de base"); rig.clicked.connect(self.auto_rig)
        self.collision=QComboBox(); self.collision.addItem("Convexe","convex"); self.collision.addItem("Boîte","box")
        coll=QPushButton("Créer collisions"); coll.clicked.connect(self.create_collisions)
        self.bake_size=QSpinBox(); self.bake_size.setRange(256,8192); self.bake_size.setSingleStep(256); self.bake_size.setValue(2048)
        bake=QPushButton("Préparer baking"); bake.clicked.connect(self.prepare_bake)
        row2.addWidget(rig); row2.addWidget(self.collision); row2.addWidget(coll); row2.addWidget(QLabel("Texture")); row2.addWidget(self.bake_size); row2.addWidget(bake)
        root.addLayout(row2)

        row3=QHBoxLayout()
        self.engine=QComboBox()
        self.engine.addItem("Godot","godot"); self.engine.addItem("Unity","unity"); self.engine.addItem("Unreal","unreal")
        export=QPushButton("Exporter pour le moteur"); export.clicked.connect(self.export_game)
        stop=QPushButton("Arrêter"); stop.clicked.connect(self.stop)
        row3.addWidget(QLabel("Moteur cible")); row3.addWidget(self.engine); row3.addWidget(export); row3.addWidget(stop); row3.addStretch(1)
        root.addLayout(row3)

        self.status=QLabel("Prêt."); self.status.setWordWrap(True); root.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(3000); root.addWidget(self.log,1)

    def choose_source(self):
        path,_=QFileDialog.getOpenFileName(self,"Scène Blender",str(Path.home()),"Blender (*.blend)")
        if path:self.source.setText(path)

    def executable(self):
        return self.blender_page.current_executable()

    def src(self):
        p=Path(self.source.text()).expanduser()
        if not p.is_file() or p.suffix.lower()!=".blend":
            raise ValueError("Choisissez une scène .blend valide.")
        return p.resolve()

    def run_script(self, script, label):
        if self.proc is not None:
            QMessageBox.information(self,"Blender","Une opération Game Ready est déjà en cours."); return
        cmd=blender_game_ready.command(self.executable(),script,str(self.src()))
        p=QProcess(self); self.proc=p
        p.setWorkingDirectory(cmd["cwd"])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(lambda code,status:self.finished(p,code,label))
        self.status.setText("⏳ "+label+"…"); self.log.appendPlainText("\n> "+label)
        p.start(cmd["program"],cmd["args"])

    def read_output(self):
        if self.proc:self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8",errors="replace"))

    def finished(self,p,code,label):
        if self.proc is not p:return
        self.read_output(); self.proc=None; p.deleteLater()
        self.status.setText(("✅ " if code==0 else "❌ ")+label+f" · code {code}")

    def decimate(self):
        try:
            src=self.src(); dst=src.with_name(src.stem+"_lowpoly.blend")
            self.run_script(blender_game_ready.decimate_script(str(src),str(dst),self.ratio.value()),"Réduction de polygones")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def generate_lods(self):
        try:
            src=self.src(); out=src.parent/(src.stem+"_LODs")
            self.run_script(blender_game_ready.lod_script(str(src),str(out)),"Génération des LOD")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def auto_uv(self):
        try:
            src=self.src(); dst=src.with_name(src.stem+"_uv.blend")
            self.run_script(blender_game_ready.uv_script(str(src),str(dst)),"UV automatique")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def auto_rig(self):
        try:
            src=self.src(); dst=src.with_name(src.stem+"_rig.blend")
            self.run_script(blender_game_ready.auto_rig_script(str(src),str(dst)),"Auto-rig de base")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def create_collisions(self):
        try:
            src=self.src(); dst=src.with_name(src.stem+"_collision.blend")
            self.run_script(blender_game_ready.collision_script(str(src),str(dst),self.collision.currentData()),"Création des collisions")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def prepare_bake(self):
        try:
            src=self.src(); out=src.parent/(src.stem+"_bake")
            self.run_script(blender_game_ready.bake_script(str(src),str(out),self.bake_size.value()),"Préparation baking")
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def export_game(self):
        try:
            src=self.src()
            engine=self.engine.currentData()
            dst=src.with_name(src.stem+"_"+engine+".glb")
            self.run_script(blender_game_ready.export_script(str(src),str(dst),engine),"Export "+engine)
        except Exception as exc: QMessageBox.warning(self,"Game Ready",str(exc))

    def stop(self):
        if self.proc:self.proc.kill(); self.status.setText("⏹ Arrêt demandé.")

    def shutdown(self):
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
