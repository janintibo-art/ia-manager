
from pathlib import Path
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,
    QCheckBox,QListWidget,QListWidgetItem,QTextBrowser,QSplitter,QMessageBox,QInputDialog
)
from src.backend import animation_library, blender_rig_mapping

class AnimationLibraryPage(QWidget):
    def __init__(self, blender_page, mapping_page):
        super().__init__()
        self.blender_page=blender_page
        self.mapping_page=mapping_page
        self.items=[]
        self.visible=[]
        self.favorites=set(animation_library.saved_favorites())
        self.proc=None

        root=QVBoxLayout(self)
        t=QLabel("Bibliothèque d'animations"); t.setObjectName("Title"); root.addWidget(t)
        intro=QLabel(
            "Indexez vos packs FBX/BVH/BLEND, classez-les, marquez vos favoris puis envoyez une animation "
            "vers le retargeting ou générez une preview."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        roots=QHBoxLayout()
        self.root_combo=QComboBox()
        self.root_combo.setMinimumWidth(280)
        add=QPushButton("Ajouter un dossier…"); add.clicked.connect(self.add_root)
        remove=QPushButton("Retirer"); remove.clicked.connect(self.remove_root)
        scan=QPushButton("Réindexer"); scan.clicked.connect(self.rescan)
        roots.addWidget(QLabel("Dossiers :")); roots.addWidget(self.root_combo,1); roots.addWidget(add); roots.addWidget(remove); roots.addWidget(scan)
        root.addLayout(roots)

        filters=QHBoxLayout()
        self.search=QLineEdit(); self.search.setPlaceholderText("Rechercher walk, attack, dance, Mixamo…")
        self.search.textChanged.connect(self.refresh)
        self.category=QComboBox(); self.category.addItems(animation_library.CATEGORIES); self.category.currentIndexChanged.connect(self.refresh)
        self.only_fav=QCheckBox("★ Favoris"); self.only_fav.toggled.connect(self.refresh)
        filters.addWidget(self.search,1); filters.addWidget(self.category); filters.addWidget(self.only_fav)
        root.addLayout(filters)

        split=QSplitter()
        self.list=QListWidget(); self.list.currentItemChanged.connect(self.select)
        self.detail=QTextBrowser(); self.detail.setOpenExternalLinks(True)
        split.addWidget(self.list); split.addWidget(self.detail); split.setSizes([430,650])
        root.addWidget(split,1)

        actions=QHBoxLayout()
        self.fav_btn=QPushButton("☆ Ajouter aux favoris"); self.fav_btn.clicked.connect(self.toggle_favorite)
        self.category_btn=QPushButton("Changer catégorie"); self.category_btn.clicked.connect(self.change_category)
        self.send_btn=QPushButton("Envoyer vers Rig Mapping"); self.send_btn.clicked.connect(self.send_to_mapping)
        self.preview_btn=QPushButton("Preview MP4"); self.preview_btn.clicked.connect(self.preview)
        self.open_btn=QPushButton("Ouvrir le dossier"); self.open_btn.clicked.connect(self.open_folder)
        actions.addWidget(self.fav_btn); actions.addWidget(self.category_btn); actions.addWidget(self.send_btn); actions.addWidget(self.preview_btn); actions.addWidget(self.open_btn); actions.addStretch(1)
        root.addLayout(actions)

        self.status=QLabel("Prêt."); self.status.setWordWrap(True); root.addWidget(self.status)
        self.reload_roots()
        self.rescan()

    def reload_roots(self):
        current=self.root_combo.currentText()
        self.root_combo.clear()
        for p in animation_library.saved_roots(): self.root_combo.addItem(p)
        if current:
            i=self.root_combo.findText(current)
            if i>=0:self.root_combo.setCurrentIndex(i)

    def add_root(self):
        path=QFileDialog.getExistingDirectory(self,"Dossier d'animations",str(Path.home()))
        if not path:return
        roots=animation_library.saved_roots()
        roots.append(path)
        animation_library.save_roots(roots)
        self.reload_roots(); self.rescan()

    def remove_root(self):
        path=self.root_combo.currentText()
        if not path:return
        roots=[p for p in animation_library.saved_roots() if p!=path]
        animation_library.save_roots(roots)
        self.reload_roots(); self.rescan()

    def rescan(self):
        self.status.setText("⏳ Indexation…")
        self.items=animation_library.scan(animation_library.saved_roots())
        for item in self.items:
            item["category"]=animation_library.effective_category(item)
        self.refresh()
        self.status.setText(f"✅ {len(self.items)} animation(s) indexée(s) dans {len(animation_library.saved_roots())} dossier(s).")

    def refresh(self):
        self.visible=animation_library.filter_items(
            self.items,self.search.text(),self.category.currentText(),self.only_fav.isChecked(),self.favorites
        )
        self.list.clear()
        for item in self.visible:
            star="★ " if item["id"] in self.favorites else ""
            row=QListWidgetItem(f"{star}{item['name']}\n{item['category']} · {item['format']} · {animation_library.human_size(item['size'])}")
            row.setData(Qt.ItemDataRole.UserRole,item)
            row.setToolTip(item["path"])
            self.list.addItem(row)
        if self.list.count(): self.list.setCurrentRow(0)
        else: self.detail.setPlainText("Aucun résultat.")

    def current(self):
        item=self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select(self,current,previous):
        item=self.current()
        if not item:
            self.fav_btn.setEnabled(False); self.send_btn.setEnabled(False); self.preview_btn.setEnabled(False); return
        meta=animation_library.load_metadata(item["path"])
        tags=", ".join(meta.get("tags",[])) or "—"
        notes=meta.get("notes","") or "—"
        self.detail.setHtml(
            f"<h2>{item['name']}</h2><p><b>Catégorie :</b> {item['category']} · <b>Format :</b> {item['format']}</p>"
            f"<p><b>Taille :</b> {animation_library.human_size(item['size'])}</p>"
            f"<p><b>Tags :</b> {tags}</p><p><b>Notes :</b> {notes}</p><p>{item['path']}</p>"
        )
        self.fav_btn.setEnabled(True); self.send_btn.setEnabled(True); self.preview_btn.setEnabled(True)
        self.fav_btn.setText("★ Retirer des favoris" if item["id"] in self.favorites else "☆ Ajouter aux favoris")

    def toggle_favorite(self):
        item=self.current()
        if not item:return
        if item["id"] in self.favorites:self.favorites.remove(item["id"])
        else:self.favorites.add(item["id"])
        animation_library.save_favorites(self.favorites); self.refresh()

    def change_category(self):
        item=self.current()
        if not item:return
        cats=[c for c in animation_library.CATEGORIES if c!="Tous"]
        value,ok=QInputDialog.getItem(self,"Catégorie","Choisir :",cats,cats.index(item["category"]) if item["category"] in cats else 0,False)
        if not ok:return
        meta=animation_library.load_metadata(item["path"]); meta["category"]=value
        animation_library.save_metadata(item["path"],meta)
        item["category"]=value; self.refresh()

    def send_to_mapping(self):
        item=self.current()
        if not item:return
        self.mapping_page.source.setText(item["path"])
        idx=self.mapping_page.parentWidget().indexOf(self.mapping_page) if self.mapping_page.parentWidget() else -1
        parent=self.mapping_page.parentWidget()
        if idx>=0 and hasattr(parent,"setCurrentIndex"): parent.setCurrentIndex(idx)
        self.status.setText("✅ Animation envoyée vers Rig Mapping & Clips.")

    def preview(self):
        item=self.current()
        if not item:return
        if item["format"]=="BLEND":
            source=item["path"]
        else:
            target=self.mapping_page.target.text().strip()
            if not target:
                QMessageBox.information(self,"Preview","Pour un FBX/BVH, choisissez d'abord une cible .blend dans Rig Mapping puis importez l'animation.")
                return
            QMessageBox.information(self,"Preview","Envoyez d'abord ce FBX/BVH vers Rig Mapping pour l'importer en .blend, puis prévisualisez la scène obtenue.")
            self.send_to_mapping(); return
        try:
            p=Path(source)
            out=p.with_name(p.stem+"_preview.mp4")
            script=blender_rig_mapping.preview_script(source,str(out),1,120)
            cmd=blender_rig_mapping.command(self.blender_page.current_executable(),script,source)
            self.run_process(cmd,"Prévisualisation")
        except Exception as exc: QMessageBox.warning(self,"Preview",str(exc))

    def run_process(self,cmd,label):
        if self.proc is not None:return
        p=QProcess(self); self.proc=p
        p.setWorkingDirectory(cmd["cwd"]); p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.finished.connect(lambda code,status:self.finished(p,code,label))
        self.status.setText("⏳ "+label+"…"); p.start(cmd["program"],cmd["args"])

    def finished(self,p,code,label):
        if self.proc is not p:return
        self.proc=None; p.deleteLater()
        self.status.setText(("✅ " if code==0 else "❌ ")+label+f" · code {code}")

    def open_folder(self):
        item=self.current()
        if not item:return
        QProcess.startDetached("explorer",[str(Path(item["path"]).parent)])

    def shutdown(self):
        if self.proc:self.proc.kill(); self.proc.waitForFinished(1000); self.proc=None
