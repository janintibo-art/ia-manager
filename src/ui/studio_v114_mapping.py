
from pathlib import Path
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,
    QSpinBox,QPlainTextEdit,QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView
)
from src.backend import blender_rig_mapping

class RigMappingClipsPage(QWidget):
    def __init__(self, blender_page):
        super().__init__()
        self.blender_page=blender_page
        self.proc=None
        root=QVBoxLayout(self)
        t=QLabel("Rig Mapping & Clips"); t.setObjectName("Title"); root.addWidget(t)
        intro=QLabel("Profils de squelette, mapping d'os éditable, import FBX/BVH, retargeting précis, clips et prévisualisation.")
        intro.setWordWrap(True); root.addWidget(intro)

        row=QHBoxLayout()
        self.target=QLineEdit(); self.target.setPlaceholderText("Cible .blend")
        b=QPushButton("Cible…"); b.clicked.connect(self.choose_target)
        self.source=QLineEdit(); self.source.setPlaceholderText("Source animée .blend / FBX / BVH")
        s=QPushButton("Source…"); s.clicked.connect(self.choose_source)
        row.addWidget(self.target,1); row.addWidget(b); row.addWidget(self.source,1); row.addWidget(s); root.addLayout(row)

        prow=QHBoxLayout()
        self.profile=QComboBox()
        for key,p in blender_rig_mapping.PROFILES.items(): self.profile.addItem(p["name"],key)
        load=QPushButton("Charger profil"); load.clicked.connect(self.load_profile)
        save=QPushButton("Sauver mapping…"); save.clicked.connect(self.save_mapping)
        openm=QPushButton("Charger mapping…"); openm.clicked.connect(self.open_mapping)
        prow.addWidget(self.profile); prow.addWidget(load); prow.addWidget(save); prow.addWidget(openm); prow.addStretch(1)
        root.addLayout(prow)

        self.table=QTableWidget(7,2)
        self.table.setHorizontalHeaderLabels(("Os cible IA Manager","Os source"))
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table,1)
        self.load_profile()

        r=QHBoxLayout()
        self.start=QSpinBox(); self.start.setRange(1,100000); self.start.setValue(1)
        self.end=QSpinBox(); self.end.setRange(1,100000); self.end.setValue(120)
        imp=QPushButton("Importer FBX/BVH"); imp.clicked.connect(self.import_anim)
        ret=QPushButton("Retarget avec mapping"); ret.clicked.connect(self.retarget)
        r.addWidget(QLabel("Début")); r.addWidget(self.start); r.addWidget(QLabel("Fin")); r.addWidget(self.end); r.addWidget(imp); r.addWidget(ret)
        root.addLayout(r)

        c=QHBoxLayout()
        self.clip_name=QLineEdit("clip_01")
        clip=QPushButton("Créer clip"); clip.clicked.connect(self.create_clip)
        preview=QPushButton("Prévisualiser MP4"); preview.clicked.connect(self.preview)
        stop=QPushButton("Arrêter"); stop.clicked.connect(self.stop)
        c.addWidget(self.clip_name,1); c.addWidget(clip); c.addWidget(preview); c.addWidget(stop); root.addLayout(c)

        self.status=QLabel("Prêt."); root.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(4000); root.addWidget(self.log,1)

    def executable(self): return self.blender_page.current_executable()

    def choose_target(self):
        p,_=QFileDialog.getOpenFileName(self,"Cible",str(Path.home()),"Blender (*.blend)")
        if p:self.target.setText(p)

    def choose_source(self):
        p,_=QFileDialog.getOpenFileName(self,"Source",str(Path.home()),"Animation (*.blend *.fbx *.bvh)")
        if p:self.source.setText(p)

    def load_profile(self):
        profile=blender_rig_mapping.PROFILES[self.profile.currentData()]
        bones=profile["bones"]
        for i,(target,source) in enumerate(bones.items()):
            self.table.setItem(i,0,QTableWidgetItem(target))
            self.table.setItem(i,1,QTableWidgetItem(source))

    def mapping(self):
        out={}
        for i in range(self.table.rowCount()):
            a=self.table.item(i,0); b=self.table.item(i,1)
            if a and b and a.text().strip() and b.text().strip(): out[a.text().strip()]=b.text().strip()
        return out

    def save_mapping(self):
        p,_=QFileDialog.getSaveFileName(self,"Sauver mapping",str(Path.home()/"mapping_rig.json"),"JSON (*.json)")
        if p: blender_rig_mapping.save_mapping(p,self.mapping())

    def open_mapping(self):
        p,_=QFileDialog.getOpenFileName(self,"Charger mapping",str(Path.home()),"JSON (*.json)")
        if not p:return
        data=blender_rig_mapping.load_mapping(p)
        for i,(a,b) in enumerate(data.items()):
            if i>=self.table.rowCount(): break
            self.table.setItem(i,0,QTableWidgetItem(a)); self.table.setItem(i,1,QTableWidgetItem(b))

    def run_script(self,script,label,blend):
        if self.proc is not None:
            QMessageBox.information(self,"Rig Mapping","Une opération est déjà en cours."); return
        cmd=blender_rig_mapping.command(self.executable(),script,blend)
        p=QProcess(self); self.proc=p
        p.setWorkingDirectory(cmd["cwd"]); p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(lambda code,status:self.finished(p,code,label))
        self.status.setText("⏳ "+label+"…"); p.start(cmd["program"],cmd["args"])

    def read_output(self):
        if self.proc:self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8",errors="replace"))

    def finished(self,p,code,label):
        if self.proc is not p:return
        self.read_output(); self.proc=None; p.deleteLater()
        self.status.setText(("✅ " if code==0 else "❌ ")+label+f" · code {code}")

    def import_anim(self):
        try:
            target=Path(self.target.text()); source=Path(self.source.text())
            if not target.is_file(): raise ValueError("Choisissez la cible .blend.")
            dst=target.with_name(target.stem+"_import_anim.blend")
            script=blender_rig_mapping.import_animation_script(str(target),str(source),str(dst))
            self.run_script(script,"Import animation",str(target))
        except Exception as exc: QMessageBox.warning(self,"Import",str(exc))

    def retarget(self):
        try:
            target=Path(self.target.text()); source=Path(self.source.text())
            if source.suffix.lower()!=".blend": raise ValueError("Pour retargeter, importez d'abord FBX/BVH en .blend.")
            dst=target.with_name(target.stem+"_mapped_retarget.blend")
            script=blender_rig_mapping.mapped_retarget_script(str(target),str(source),str(dst),self.mapping(),self.start.value(),self.end.value())
            self.run_script(script,"Retarget mapping",str(target))
        except Exception as exc: QMessageBox.warning(self,"Retarget",str(exc))

    def create_clip(self):
        try:
            target=Path(self.target.text())
            dst=target.with_name(target.stem+"_"+self.clip_name.text()+".blend")
            script=blender_rig_mapping.clip_script(str(target),str(dst),self.clip_name.text(),self.start.value(),self.end.value())
            self.run_script(script,"Création clip",str(target))
        except Exception as exc: QMessageBox.warning(self,"Clip",str(exc))

    def preview(self):
        try:
            target=Path(self.target.text())
            dst=target.with_name(target.stem+"_preview.mp4")
            script=blender_rig_mapping.preview_script(str(target),str(dst),self.start.value(),self.end.value())
            self.run_script(script,"Prévisualisation MP4",str(target))
        except Exception as exc: QMessageBox.warning(self,"Preview",str(exc))

    def stop(self):
        if self.proc:self.proc.kill(); self.status.setText("⏹ Arrêt demandé.")

    def shutdown(self):
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
