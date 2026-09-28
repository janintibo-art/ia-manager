"""Studio IA v101 : catalogue, favoris, profils et éditeur de pipelines locaux."""
import html

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QTextBrowser, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QInputDialog,
    QMessageBox, QGroupBox, QAbstractItemView
)

from src.backend import studio_catalog as catalog, pipeline_designer as designer, settings


class StudioHubTab(QWidget):
    open_local_tools = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.vram = 0.0
        self.ram = 0.0
        self.current_model = None
        self.favorite_ids = set(designer.favorites(settings.get('studio_v101_favorites')))
        self.saved_pipelines = designer.validate_saved(settings.get('studio_v101_pipelines'))
        root = QVBoxLayout(self)
        title = QLabel("Studio IA local v101")
        title.setObjectName("Title")
        root.addWidget(title)
        self.hardware = QLabel("Compatibilité : lancez Analyse pour utiliser automatiquement la RAM et la VRAM détectées.")
        self.hardware.setWordWrap(True)
        root.addWidget(self.hardware)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._models_page(), "Modèles")
        self.tabs.addTab(self._tools_page(), "Outils")
        self.tabs.addTab(self._pipelines_page(), "Pipelines visuels")
        self.tabs.addTab(self._profiles_page(), "Profils projet")

    # --------------------------------------------------------------- modèles
    def _models_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.category = QComboBox(); self.category.addItem("Toutes"); self.category.addItems(catalog.CATEGORIES)
        self.search = QLineEdit(); self.search.setPlaceholderText("Rechercher : code, FLUX, musique, vidéo, 3D, RAG…")
        self.compatible = QCheckBox("Seulement adaptés")
        self.favorites_only = QCheckBox("★ Favoris")
        filters.addWidget(self.category); filters.addWidget(self.search, 1); filters.addWidget(self.compatible); filters.addWidget(self.favorites_only)
        lay.addLayout(filters)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.models = QListWidget(); self.models.setMinimumWidth(280)
        self.details = QTextBrowser()
        split.addWidget(self.models); split.addWidget(self.details); split.setSizes([320, 720])
        lay.addWidget(split, 1)
        actions = QHBoxLayout()
        self.favorite_btn = QPushButton("☆ Ajouter aux favoris")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.model_link = QPushButton("Ouvrir la page du modèle")
        self.model_link.clicked.connect(self.open_model_link)
        local = QPushButton("Ouvrir Outils locaux"); local.clicked.connect(self.open_local_tools.emit)
        actions.addWidget(self.favorite_btn); actions.addWidget(self.model_link); actions.addWidget(local); actions.addStretch(1)
        lay.addLayout(actions)
        self.category.currentIndexChanged.connect(self.refresh_models)
        self.search.textChanged.connect(self.refresh_models)
        self.compatible.toggled.connect(self.refresh_models)
        self.favorites_only.toggled.connect(self.refresh_models)
        self.models.currentItemChanged.connect(self.show_model)
        self.refresh_models()
        return page

    def toggle_favorite(self):
        if not self.current_model: return
        mid = self.current_model['id']
        if mid in self.favorite_ids: self.favorite_ids.remove(mid)
        else: self.favorite_ids.add(mid)
        settings.set('studio_v101_favorites', sorted(self.favorite_ids))
        self.show_model(self.models.currentItem(), None)
        if self.favorites_only.isChecked(): self.refresh_models()

    # ---------------------------------------------------------------- outils
    def _tools_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        intro = QLabel(f"{len(catalog.TOOLS)} outils locaux complémentaires. Double-cliquez une ligne pour ouvrir sa page officielle.")
        intro.setWordWrap(True); lay.addWidget(intro)
        table = QTableWidget(len(catalog.TOOLS), 4)
        table.setHorizontalHeaderLabels(("Outil", "Famille", "Rôle", "Lien"))
        table.verticalHeader().setVisible(False); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for row, tool in enumerate(catalog.TOOLS):
            for col, value in enumerate((tool['name'], tool['category'], tool['description'], tool['url'])):
                item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole, tool['url']); table.setItem(row, col, item)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.cellDoubleClicked.connect(lambda r, c: QDesktopServices.openUrl(QUrl(table.item(r, 0).data(Qt.ItemDataRole.UserRole))))
        lay.addWidget(table, 1)
        local = QPushButton("Installer / démarrer les moteurs déjà gérés par IA Manager")
        local.clicked.connect(self.open_local_tools.emit); lay.addWidget(local)
        return page

    # ------------------------------------------------------------ pipelines
    def _pipelines_page(self):
        page = QWidget(); root = QVBoxLayout(page)
        intro = QLabel("Construisez une chaîne locale étape par étape. L’éditeur prépare et mémorise le workflow ; il ne lance aucun outil sans votre action.")
        intro.setWordWrap(True); root.addWidget(intro)
        top = QHBoxLayout()
        self.pipeline_templates = QComboBox()
        self.pipeline_templates.addItem("Nouveau pipeline", None)
        for pipe in catalog.PIPELINES: self.pipeline_templates.addItem(pipe['name'], pipe)
        for pipe in self.saved_pipelines: self.pipeline_templates.addItem("★ " + pipe['name'], pipe)
        load_btn = QPushButton("Charger"); load_btn.clicked.connect(self.load_pipeline_template)
        save_btn = QPushButton("Enregistrer"); save_btn.clicked.connect(self.save_pipeline)
        delete_btn = QPushButton("Supprimer perso"); delete_btn.clicked.connect(self.delete_pipeline)
        top.addWidget(QLabel("Modèle :")); top.addWidget(self.pipeline_templates, 1); top.addWidget(load_btn); top.addWidget(save_btn); top.addWidget(delete_btn)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QGroupBox("Briques disponibles"); ll = QVBoxLayout(left)
        self.step_filter = QLineEdit(); self.step_filter.setPlaceholderText("Filtrer les étapes…")
        self.step_library = QListWidget(); self.step_library.setMinimumWidth(260)
        ll.addWidget(self.step_filter); ll.addWidget(self.step_library, 1)
        add = QPushButton("Ajouter →"); add.clicked.connect(self.add_step); ll.addWidget(add)
        split.addWidget(left)

        center = QGroupBox("Pipeline"); cl = QVBoxLayout(center)
        self.pipeline_name = QLineEdit(); self.pipeline_name.setPlaceholderText("Nom du pipeline")
        self.pipeline_steps = QListWidget()
        self.pipeline_steps.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        buttons = QHBoxLayout()
        up = QPushButton("↑"); up.clicked.connect(lambda: self.move_step(-1))
        down = QPushButton("↓"); down.clicked.connect(lambda: self.move_step(1))
        remove = QPushButton("Retirer"); remove.clicked.connect(self.remove_step)
        clear = QPushButton("Vider"); clear.clicked.connect(self.pipeline_steps.clear)
        for b in (up, down, remove, clear): buttons.addWidget(b)
        cl.addWidget(self.pipeline_name); cl.addWidget(self.pipeline_steps, 1); cl.addLayout(buttons)
        split.addWidget(center)

        right = QGroupBox("Guide de lancement"); rl = QVBoxLayout(right)
        self.pipeline_guide = QTextBrowser()
        refresh = QPushButton("Actualiser le guide"); refresh.clicked.connect(self.refresh_guide)
        tools = QPushButton("Ouvrir Outils locaux"); tools.clicked.connect(self.open_local_tools.emit)
        rl.addWidget(self.pipeline_guide, 1); rl.addWidget(refresh); rl.addWidget(tools)
        split.addWidget(right); split.setSizes([280, 360, 430])
        root.addWidget(split, 1)
        self.step_filter.textChanged.connect(self.refresh_step_library)
        self.pipeline_steps.model().rowsInserted.connect(lambda *_: self.refresh_guide())
        self.pipeline_steps.model().rowsRemoved.connect(lambda *_: self.refresh_guide())
        self.refresh_step_library(); self.load_pipeline_template()
        return page

    def refresh_step_library(self):
        if not hasattr(self, 'step_library'): return
        needle = self.step_filter.text().strip().lower(); self.step_library.clear()
        for step in designer.STEP_LIBRARY:
            hay = f"{step['name']} {step['family']} {step['role']}".lower()
            if needle and needle not in hay: continue
            item = QListWidgetItem(f"{step['name']}\n{step['family']} · {step['role']}")
            item.setData(Qt.ItemDataRole.UserRole, step['id']); self.step_library.addItem(item)

    def current_step_ids(self):
        return [self.pipeline_steps.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.pipeline_steps.count())]

    def set_steps(self, ids):
        known = designer.step_map(); self.pipeline_steps.clear()
        for sid in designer.normalize_steps(ids):
            step = known[sid]; item = QListWidgetItem(step['name']); item.setData(Qt.ItemDataRole.UserRole, sid); item.setToolTip(step['role']); self.pipeline_steps.addItem(item)
        self.refresh_guide()

    def add_step(self):
        item = self.step_library.currentItem()
        if not item: return
        sid = item.data(Qt.ItemDataRole.UserRole); step = designer.step_map()[sid]
        out = QListWidgetItem(step['name']); out.setData(Qt.ItemDataRole.UserRole, sid); out.setToolTip(step['role']); self.pipeline_steps.addItem(out)
        self.pipeline_steps.setCurrentItem(out)

    def remove_step(self):
        row = self.pipeline_steps.currentRow()
        if row >= 0: self.pipeline_steps.takeItem(row); self.refresh_guide()

    def move_step(self, delta):
        row = self.pipeline_steps.currentRow(); target = row + delta
        if row < 0 or target < 0 or target >= self.pipeline_steps.count(): return
        item = self.pipeline_steps.takeItem(row); self.pipeline_steps.insertItem(target, item); self.pipeline_steps.setCurrentRow(target); self.refresh_guide()

    def load_pipeline_template(self):
        data = self.pipeline_templates.currentData()
        if not data:
            self.pipeline_name.clear(); self.set_steps(()); return
        self.pipeline_name.setText(str(data.get('name', '')))
        self.set_steps(data.get('steps', ()))

    def save_pipeline(self):
        try: record = designer.pipeline_record(self.pipeline_name.text(), self.current_step_ids())
        except ValueError as exc: QMessageBox.warning(self, "Pipeline", str(exc)); return
        self.saved_pipelines = [p for p in self.saved_pipelines if p['name'].casefold() != record['name'].casefold()]
        self.saved_pipelines.append(record); settings.set('studio_v101_pipelines', self.saved_pipelines)
        self.rebuild_pipeline_combo(record['name'])
        QMessageBox.information(self, "Pipeline", "Pipeline enregistré dans IA Manager.")

    def delete_pipeline(self):
        data = self.pipeline_templates.currentData()
        if not data: return
        name = str(data.get('name', ''))
        old = len(self.saved_pipelines)
        self.saved_pipelines = [p for p in self.saved_pipelines if p['name'].casefold() != name.casefold()]
        if len(self.saved_pipelines) == old:
            QMessageBox.information(self, "Pipeline", "Les pipelines intégrés ne sont pas supprimés. Enregistrez une variante sous un autre nom."); return
        settings.set('studio_v101_pipelines', self.saved_pipelines); self.rebuild_pipeline_combo(); self.load_pipeline_template()

    def rebuild_pipeline_combo(self, select_name=None):
        self.pipeline_templates.blockSignals(True); self.pipeline_templates.clear(); self.pipeline_templates.addItem("Nouveau pipeline", None)
        for pipe in catalog.PIPELINES: self.pipeline_templates.addItem(pipe['name'], pipe)
        selected = 0
        for pipe in self.saved_pipelines:
            self.pipeline_templates.addItem("★ " + pipe['name'], pipe)
            if select_name and pipe['name'].casefold() == select_name.casefold(): selected = self.pipeline_templates.count()-1
        self.pipeline_templates.setCurrentIndex(selected); self.pipeline_templates.blockSignals(False)

    def refresh_guide(self):
        if not hasattr(self, 'pipeline_guide'): return
        lines = designer.guide_for_steps(self.current_step_ids())
        if not lines:
            self.pipeline_guide.setPlainText("Ajoutez des briques à gauche ou chargez un pipeline intégré."); return
        self.pipeline_guide.setHtml("<h3>Ordre conseillé</h3>" + "".join(f"<p>{html.escape(line)}</p>" for line in lines) +
            "<hr><p><b>Mode sûr :</b> préparez chaque moteur, faites un petit essai, puis passez à l’étape suivante. IA Manager ne déclenche pas de téléchargement ou d’exécution depuis cet éditeur.</p>")

    # ------------------------------------------------------------- profils
    def _profiles_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Un profil remplit vos favoris et prépare le pipeline conseillé sans installer de modèle à votre place."))
        self.profile_list = QListWidget()
        for profile in designer.PROJECT_PROFILES:
            item = QListWidgetItem(profile['name'] + "\n" + profile['description']); item.setData(Qt.ItemDataRole.UserRole, profile); self.profile_list.addItem(item)
        lay.addWidget(self.profile_list, 1)
        self.profile_details = QTextBrowser(); lay.addWidget(self.profile_details, 1)
        buttons = QHBoxLayout()
        apply_btn = QPushButton("Appliquer ce profil"); apply_btn.clicked.connect(self.apply_profile)
        pipeline_btn = QPushButton("Préparer son pipeline"); pipeline_btn.clicked.connect(self.prepare_profile_pipeline)
        buttons.addWidget(apply_btn); buttons.addWidget(pipeline_btn); buttons.addStretch(1); lay.addLayout(buttons)
        self.profile_list.currentItemChanged.connect(self.show_profile)
        if self.profile_list.count(): self.profile_list.setCurrentRow(0)
        return page

    def show_profile(self, item, previous):
        if not item: return
        p = item.data(Qt.ItemDataRole.UserRole)
        models = [m['name'] for m in catalog.MODELS if m['id'] in p['favorites']]
        self.profile_details.setHtml(f"<h2>{html.escape(p['name'])}</h2><p>{html.escape(p['description'])}</p><p><b>Pipeline :</b> {html.escape(p['pipeline'])}</p><p><b>Favoris suggérés :</b> {html.escape(', '.join(models) or 'à choisir dans le catalogue')}</p>")

    def apply_profile(self):
        item = self.profile_list.currentItem()
        if not item: return
        p = item.data(Qt.ItemDataRole.UserRole); known = {m['id'] for m in catalog.MODELS}
        self.favorite_ids.update(mid for mid in p['favorites'] if mid in known)
        settings.set('studio_v101_favorites', sorted(self.favorite_ids)); self.refresh_models()
        QMessageBox.information(self, "Profil", f"Profil « {p['name']} » appliqué : favoris ajoutés, sans modifier vos installations.")

    def prepare_profile_pipeline(self):
        item = self.profile_list.currentItem()
        if not item: return
        p = item.data(Qt.ItemDataRole.UserRole)
        index = self.pipeline_templates.findText(p['pipeline'])
        if index >= 0: self.pipeline_templates.setCurrentIndex(index); self.load_pipeline_template(); self.tabs.setCurrentIndex(2)

    # ------------------------------------------------------------- commun
    def set_system_info(self, info):
        cap = catalog.hardware_capacity(info); self.vram, self.ram = cap['vram'], cap['ram']
        parts = []
        if self.ram: parts.append(f"RAM détectée ~{self.ram:g} Go")
        if self.vram: parts.append(f"VRAM détectée ~{self.vram:g} Go")
        self.hardware.setText("Compatibilité indicative : " + (" · ".join(parts) if parts else "aucune valeur RAM/VRAM exploitable dans l’analyse."))
        self.refresh_models()

    def refresh_models(self):
        if not hasattr(self, 'models'): return
        previous = self.current_model['id'] if self.current_model else None
        self.models.blockSignals(True); self.models.clear(); selected = 0
        values = catalog.filter_models(self.search.text(), self.category.currentText(), self.compatible.isChecked(), self.vram, self.ram)
        if self.favorites_only.isChecked(): values = [m for m in values if m['id'] in self.favorite_ids]
        for i, model in enumerate(values):
            status, _ = catalog.compatibility(model, self.vram, self.ram)
            icon = {"bon":"✅", "limite":"🟠", "difficile":"🔴", "inconnu":"⚪"}[status]
            star = "★ " if model['id'] in self.favorite_ids else ""
            item = QListWidgetItem(f"{star}{icon} {model['name']}\n{model['category']} · {model['engine']}")
            item.setData(Qt.ItemDataRole.UserRole, model); item.setToolTip(model['specialty']); self.models.addItem(item)
            if model['id'] == previous: selected = i
        self.models.blockSignals(False)
        if self.models.count(): self.models.setCurrentRow(selected)
        else: self.current_model = None; self.details.setPlainText("Aucun modèle ne correspond à ces filtres.")

    def show_model(self, item, previous):
        self.current_model = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.favorite_btn.setEnabled(bool(self.current_model))
        self.model_link.setEnabled(bool(self.current_model))
        if not self.current_model: return
        model = self.current_model; status, reason = catalog.compatibility(model, self.vram, self.ram)
        labels = {"bon":"Bon candidat", "limite":"À tester avec prudence", "difficile":"Très exigeant pour ce profil", "inconnu":"Compatibilité à vérifier"}
        self.favorite_btn.setText("★ Retirer des favoris" if model['id'] in self.favorite_ids else "☆ Ajouter aux favoris")
        self.details.setHtml(
            f"<h2>{html.escape(model['name'])}</h2><p><b>{labels[status]}</b> — {html.escape(reason)}</p>"
            f"<p><b>Spécialité :</b> {html.escape(model['specialty'])}</p><p><b>Moteur :</b> {html.escape(model['engine'])}</p>"
            f"<p><b>Entrée :</b> {html.escape(model['input'])} &nbsp; <b>Sortie :</b> {html.escape(model['output'])}</p>"
            f"<p><b>Repères :</b> RAM {model['min_ram']} Go · VRAM {model['min_vram']} Go · poids ~{model['size_gb']} Go selon variante/quantification.</p>"
            "<p>Ces valeurs servent au tri local et ne garantissent ni vitesse ni compatibilité absolue.</p>")

    def open_model_link(self):
        if self.current_model: QDesktopServices.openUrl(QUrl(self.current_model['url']))
