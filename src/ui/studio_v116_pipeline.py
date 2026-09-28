
from pathlib import Path
from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,
    QCheckBox,QDoubleSpinBox,QSpinBox,QProgressBar,QListWidget,QListWidgetItem,
    QPlainTextEdit,QMessageBox,QGroupBox,QGridLayout
)
from src.backend import character_pipeline, blender_animation, blender_rig_mapping

class CharacterPipelinePage(QWidget):
    def __init__(self, blender_page, mapping_page):
        super().__init__()
        self.blender_page=blender_page
        self.mapping_page=mapping_page
        self.plan={}
        self.current_info=None
        self.proc=None
        self.auto_mode=False

        root=QVBoxLayout(self)
        title=QLabel("Pipeline personnage complet"); title.setObjectName("Title"); root.addWidget(title)
        intro=QLabel(
            "Enchaînez automatiquement les étapes Blender pour transformer un modèle 3D en asset de jeu. "
            "Chaque étape crée un nouveau fichier et la progression est enregistrée dans le dossier de sortie."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        io=QGridLayout()
        self.source=QLineEdit(); self.source.setPlaceholderText("GLB / GLTF / FBX / OBJ / STL / PLY / BLEND")
        sb=QPushButton("Source…"); sb.clicked.connect(self.choose_source)
        self.output=QLineEdit(str(Path.home()/"IA Manager"/"Pipeline personnages"))
        ob=QPushButton("Sortie…"); ob.clicked.connect(self.choose_output)
        self.name=QLineEdit("personnage")
        io.addWidget(QLabel("Source"),0,0); io.addWidget(self.source,0,1); io.addWidget(sb,0,2)
        io.addWidget(QLabel("Sortie"),1,0); io.addWidget(self.output,1,1); io.addWidget(ob,1,2)
        io.addWidget(QLabel("Nom"),2,0); io.addWidget(self.name,2,1)
        root.addLayout(io)

        box=QGroupBox("Étapes")
        grid=QGridLayout(box)
        self.clean=QCheckBox("Nettoyage"); self.clean.setChecked(True)
        self.decimate=QCheckBox("Low poly"); self.decimate.setChecked(True)
        self.uv=QCheckBox("UV"); self.uv.setChecked(True)
        self.rig=QCheckBox("Auto-rig"); self.rig.setChecked(True)
        self.animation=QCheckBox("Animation de base")
        self.retarget=QCheckBox("Retargeting")
        self.lod=QCheckBox("LOD"); self.lod.setChecked(True)
        self.collision=QCheckBox("Collisions"); self.collision.setChecked(True)
        for i,w in enumerate((self.clean,self.decimate,self.uv,self.rig,self.animation,self.retarget,self.lod,self.collision)):
            grid.addWidget(w,i//4,i%4)
        root.addWidget(box)

        opts=QHBoxLayout()
        self.ratio=QDoubleSpinBox(); self.ratio.setRange(0.05,1.0); self.ratio.setValue(0.5); self.ratio.setSingleStep(0.05)
        self.anim=QComboBox()
        for key,data in blender_animation.ANIMATIONS.items(): self.anim.addItem(data["name"],key)
        self.engine=QComboBox(); self.engine.addItem("Godot","godot"); self.engine.addItem("Unity","unity"); self.engine.addItem("Unreal","unreal")
        self.collision_mode=QComboBox(); self.collision_mode.addItem("Convexe","convex"); self.collision_mode.addItem("Boîte","box")
        opts.addWidget(QLabel("Low poly")); opts.addWidget(self.ratio)
        opts.addWidget(QLabel("Animation")); opts.addWidget(self.anim)
        opts.addWidget(QLabel("Collision")); opts.addWidget(self.collision_mode)
        opts.addWidget(QLabel("Moteur")); opts.addWidget(self.engine)
        root.addLayout(opts)

        ret=QHBoxLayout()
        self.anim_source=QLineEdit(); self.anim_source.setPlaceholderText("Source retarget .blend facultative")
        ab=QPushButton("Animation source…"); ab.clicked.connect(self.choose_anim_source)
        self.start=QSpinBox(); self.start.setRange(1,100000); self.start.setValue(1)
        self.end=QSpinBox(); self.end.setRange(1,100000); self.end.setValue(120)
        ret.addWidget(self.anim_source,1); ret.addWidget(ab); ret.addWidget(QLabel("Frames")); ret.addWidget(self.start); ret.addWidget(self.end)
        root.addLayout(ret)

        actions=QHBoxLayout()
        prepare=QPushButton("Préparer"); prepare.clicked.connect(self.prepare)
        resume=QPushButton("Reprendre un pipeline…"); resume.clicked.connect(self.resume)
        run=QPushButton("Tout lancer"); run.clicked.connect(self.run_all)
        one=QPushButton("Étape suivante"); one.clicked.connect(self.run_next)
        skip=QPushButton("Ignorer étape"); skip.clicked.connect(self.skip)
        stop=QPushButton("Arrêter après cette étape"); stop.clicked.connect(self.stop_after)
        for b in (prepare,resume,run,one,skip,stop): actions.addWidget(b)
        actions.addStretch(1); root.addLayout(actions)

        self.progress=QProgressBar(); self.progress.setRange(0,100); root.addWidget(self.progress)
        self.status=QLabel("Prêt."); self.status.setWordWrap(True); root.addWidget(self.status)
        self.steps=QListWidget(); root.addWidget(self.steps,1)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(5000); root.addWidget(self.log,1)

    def executable(self): return self.blender_page.current_executable()

    def choose_source(self):
        p,_=QFileDialog.getOpenFileName(self,"Modèle 3D",str(Path.home()),"3D (*.blend *.glb *.gltf *.fbx *.obj *.stl *.ply)")
        if p:self.source.setText(p); self.name.setText(Path(p).stem)

    def choose_output(self):
        p=QFileDialog.getExistingDirectory(self,"Dossier de sortie",self.output.text())
        if p:self.output.setText(p)

    def choose_anim_source(self):
        p,_=QFileDialog.getOpenFileName(self,"Animation source Blender",str(Path.home()),"Blender (*.blend)")
        if p:self.anim_source.setText(p)

    def options(self):
        return {
            "name":self.name.text(),
            "clean":self.clean.isChecked(),
            "decimate":self.decimate.isChecked(),
            "uv":self.uv.isChecked(),
            "rig":self.rig.isChecked(),
            "animation":self.animation.isChecked(),
            "retarget":self.retarget.isChecked(),
            "lod":self.lod.isChecked(),
            "collision":self.collision.isChecked(),
            "export":True,
            "decimate_ratio":self.ratio.value(),
            "animation_name":self.anim.currentData(),
            "animation_source":self.anim_source.text().strip(),
            "retarget_mapping":self.mapping_page.mapping() if self.retarget.isChecked() else {},
            "retarget_start":self.start.value(),
            "retarget_end":self.end.value(),
            "collision_mode":self.collision_mode.currentData(),
            "engine":self.engine.currentData(),
        }

    def prepare(self):
        if self.proc:
            return
        try:
            self.plan=character_pipeline.new_plan(self.source.text(),self.output.text(),self.options())
            self.auto_mode=False
            self.refresh()
        except Exception as exc: QMessageBox.warning(self,"Pipeline personnage",str(exc))

    def resume(self):
        folder=QFileDialog.getExistingDirectory(self,"Dossier du pipeline",self.output.text())
        if not folder:return
        plan=character_pipeline.sanitize(character_pipeline.load_manifest(folder))
        if not plan:
            QMessageBox.warning(self,"Pipeline personnage","Aucun manifest v116 valide dans ce dossier."); return
        self.plan=plan
        self.source.setText(plan["source"]); self.name.setText(plan["name"]); self.output.setText(str(Path(plan["output_dir"]).parent))
        self.refresh()

    def refresh(self):
        self.steps.clear()
        if not self.plan:
            self.progress.setValue(0); return
        done=self.plan["index"]
        active=character_pipeline.current_step(self.plan)
        for i,step in enumerate(self.plan["enabled"]):
            icon="✅" if i<done else ("➡" if step==active else "⚪")
            self.steps.addItem(QListWidgetItem(f"{icon} {character_pipeline.STEP_LABELS[step]}"))
        p=character_pipeline.progress(self.plan); self.progress.setValue(p["percent"])
        text=f"{p['done']}/{p['total']} étapes · état : {self.plan['state']}"
        if self.plan.get("last_error"): text+=" · "+self.plan["last_error"]
        self.status.setText(text)

    def run_all(self):
        if not self.plan:self.prepare()
        if not self.plan:return
        self.auto_mode=True; self.run_next()

    def run_next(self):
        if self.proc:return
        if not self.plan:
            self.prepare()
            if not self.plan:return
        if not character_pipeline.current_step(self.plan):
            self.status.setText("✅ Pipeline terminé."); self.auto_mode=False; return
        try:
            info=character_pipeline.prepare_step(self.plan,self.executable())
            self.current_info=info
            self.plan=character_pipeline.mark_started(self.plan,info)
            cmd=info["command"]
            p=QProcess(self); self.proc=p
            p.setWorkingDirectory(cmd["cwd"]); p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            p.readyReadStandardOutput.connect(self.read_output)
            p.finished.connect(lambda code,status:self.finished(p,code,info))
            p.errorOccurred.connect(lambda _e:self.process_error(p,info))
            self.log.appendPlainText("\n> "+info["label"])
            self.refresh(); p.start(cmd["program"],cmd["args"])
        except Exception as exc:
            self.plan=character_pipeline.mark_error(self.plan,str(exc))
            self.auto_mode=False; self.refresh()

    def read_output(self):
        if self.proc:self.log.insertPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8",errors="replace"))

    def finished(self,p,code,info):
        if self.proc is not p:return
        self.read_output(); self.proc=None; p.deleteLater()
        if code==0:
            try:self.plan=character_pipeline.mark_success(self.plan,info)
            except Exception as exc:self.plan=character_pipeline.mark_error(self.plan,str(exc)); self.auto_mode=False
        else:
            self.plan=character_pipeline.mark_error(self.plan,f"{info['label']} a échoué (code {code}).")
            self.auto_mode=False
        self.refresh()
        if self.auto_mode and self.plan.get("state")!="erreur" and character_pipeline.current_step(self.plan):
            QTimer.singleShot(600,self.run_next)
        elif self.plan.get("state")=="terminé":
            self.auto_mode=False; QMessageBox.information(self,"Pipeline personnage","Pipeline terminé.\n\nSortie : "+self.plan["output_dir"])

    def process_error(self,p,info):
        if self.proc is p:self.status.setText("❌ "+p.errorString())

    def skip(self):
        if self.proc or not self.plan:return
        self.plan=character_pipeline.skip_step(self.plan); self.refresh()

    def stop_after(self):
        self.auto_mode=False
        self.status.setText("La chaîne s'arrêtera après l'étape en cours.")

    def shutdown(self):
        self.auto_mode=False
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
