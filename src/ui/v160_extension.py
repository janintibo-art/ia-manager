"""v160 : Recettes et workflows guidés prêts à l'emploi."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import creative_tools


RECIPES = [
    {
        "id": "sdxl",
        "icon": "🎨",
        "title": "Image locale — SDXL / ComfyUI",
        "category": "Image",
        "engine": "comfyui",
        "target": "image_studio_tab",
        "steps": [
            ("Installer ComfyUI", "Outils locaux", "creative_tools_tab"),
            ("Installer au moins un checkpoint SDXL compatible", "Création d’images", "image_studio_tab"),
            ("Connecter IA Manager à ComfyUI", "Création d’images", "image_studio_tab"),
            ("Écrire le prompt puis générer", "Création d’images", "image_studio_tab"),
        ],
        "note": "Recette locale. Le coût dépend uniquement de votre matériel et des modèles utilisés.",
    },
    {
        "id": "musicgen",
        "icon": "🎵",
        "title": "Musique locale — MusicGen Small",
        "category": "Audio",
        "engine": "audiocraft",
        "target": "media_studio_tab",
        "media_category": "Musique et sons",
        "steps": [
            ("Installer AudioCraft", "Outils locaux", "creative_tools_tab"),
            ("Choisir MusicGen Small", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Décrire style, tempo, instruments et ambiance", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Démarrer l’interface puis générer", "Audio · Vidéo · 3D", "media_studio_tab"),
        ],
        "note": "Commencer par MusicGen Small pour valider l’installation avant les modèles plus lourds.",
    },
    {
        "id": "wan",
        "icon": "🎬",
        "title": "Vidéo locale — Wan 2.1 dans ComfyUI",
        "category": "Vidéo",
        "engine": "comfyui",
        "target": "media_studio_tab",
        "media_category": "Vidéo",
        "steps": [
            ("Installer / démarrer ComfyUI", "Outils locaux", "creative_tools_tab"),
            ("Choisir Wan 2.1 T2V 1.3B", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Installer les poids et composants demandés par le workflow", "ComfyUI", "creative_tools_tab"),
            ("Commencer en petite résolution / courte durée", "Audio · Vidéo · 3D", "media_studio_tab"),
        ],
        "note": "La vidéo est nettement plus gourmande que l’image. Commencer petit permet de valider le workflow.",
    },
    {
        "id": "triposr",
        "icon": "🧊",
        "title": "3D rapide — TripoSR",
        "category": "3D",
        "engine": "triposr",
        "target": "media_studio_tab",
        "media_category": "Modélisation 3D",
        "steps": [
            ("Installer TripoSR", "Outils locaux", "creative_tools_tab"),
            ("Préparer une image claire de l’objet", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Démarrer l’interface TripoSR", "Outils locaux", "creative_tools_tab"),
            ("Importer l’image et exporter le maillage", "Audio · Vidéo · 3D", "media_studio_tab"),
        ],
        "note": "Idéal pour objets, props et personnages simples. Le résultat n’est pas automatiquement riggé.",
    },
    {
        "id": "hunyuan3d",
        "icon": "🧱",
        "title": "3D détaillée — Hunyuan3D 2",
        "category": "3D",
        "engine": "hunyuan3d",
        "target": "media_studio_tab",
        "media_category": "Modélisation 3D",
        "steps": [
            ("Installer Hunyuan3D 2", "Outils locaux", "creative_tools_tab"),
            ("Préparer l’image de référence", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Générer la forme", "Audio · Vidéo · 3D", "media_studio_tab"),
            ("Générer / vérifier la texture", "Audio · Vidéo · 3D", "media_studio_tab"),
        ],
        "note": "Plus complet que TripoSR mais aussi plus exigeant en dépendances et en GPU.",
    },
    {
        "id": "lora",
        "icon": "🧠",
        "title": "Entraînement — LoRA / QLoRA",
        "category": "Entraînement",
        "target": "training_tab",
        "steps": [
            ("Choisir le modèle de base", "Entraîner / Fusionner", "training_tab"),
            ("Préparer / sélectionner le dataset", "Entraîner / Fusionner", "training_tab"),
            ("Vérifier VRAM, contexte, rank et batch", "Entraîner / Fusionner", "training_tab"),
            ("Lancer l’entraînement puis tester l’adapter", "Entraîner / Fusionner", "training_tab"),
        ],
        "note": "Commencer petit : dataset propre, peu d’époques, puis augmenter si nécessaire.",
    },
    {
        "id": "mergekit",
        "icon": "🧩",
        "title": "Fusion — MergeKit",
        "category": "Fusion",
        "target": "mergekit_tab",
        "steps": [
            ("Installer / réparer MergeKit", "MergeKit", "mergekit_tab"),
            ("Choisir des modèles compatibles", "MergeKit", "mergekit_tab"),
            ("Sélectionner la méthode de fusion", "MergeKit", "mergekit_tab"),
            ("Fusionner puis convertir / importer vers Ollama", "MergeKit", "mergekit_tab"),
        ],
        "note": "Les architectures et vocabulaires doivent être compatibles. Toujours conserver les modèles sources.",
    },
    {
        "id": "surgery",
        "icon": "🧬",
        "title": "Chirurgie IA — variante comportementale",
        "category": "Chirurgie",
        "target": "surgery_dashboard_tab",
        "steps": [
            ("Choisir le modèle source", "Chirurgie IA", "surgery_dashboard_tab"),
            ("Choisir l’objectif : simple / auto / géométrie / comportement", "Chirurgie IA", "surgery_dashboard_tab"),
            ("Ouvrir Obliteratus, Heretic, Abliteration Lab ou ErisForge", "Chirurgie IA", "surgery_dashboard_tab"),
            ("Créer la variante puis benchmarker Original / Variante", "Benchmark IA", "benchmark_tab"),
        ],
        "note": "Une transformation ne garantit pas un meilleur modèle : toujours comparer avant/après.",
    },
]


class RecipesTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.recipes = RECIPES
        self.build_ui()
        self.populate()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("📖 Recettes / workflows")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Des parcours prêts à l’emploi. Chaque recette vérifie les prérequis connus, "
            "explique les étapes et ouvre les bons écrans dans le bon ordre."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Catégorie"))
        self.category = QComboBox()
        self.category.addItem("Toutes", "")
        for name in ("Image", "Audio", "Vidéo", "3D", "Entraînement", "Fusion", "Chirurgie"):
            self.category.addItem(name, name)
        self.category.currentIndexChanged.connect(self.populate)
        filters.addWidget(self.category)

        self.refresh_btn = QPushButton("🔄 Vérifier les prérequis")
        self.refresh_btn.clicked.connect(self.show_recipe)
        filters.addWidget(self.refresh_btn)
        filters.addStretch()
        root.addLayout(filters)

        content = QHBoxLayout()

        self.list = QListWidget()
        self.list.setMinimumWidth(320)
        self.list.currentItemChanged.connect(lambda *_: self.show_recipe())
        content.addWidget(self.list, 1)

        right = QFrame()
        right.setObjectName("Card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel("Choisissez une recette")
        self.title_label.setObjectName("Title")
        self.title_label.setWordWrap(True)
        rl.addWidget(self.title_label)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        rl.addWidget(self.note)

        self.engine_state = QLabel("")
        self.engine_state.setWordWrap(True)
        rl.addWidget(self.engine_state)

        self.steps = QTableWidget(0, 4)
        self.steps.setHorizontalHeaderLabels(["Étape", "Action", "Écran", "Ouvrir"])
        self.steps.verticalHeader().hide()
        self.steps.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.steps.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.steps.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(self.steps, 1)

        actions = QHBoxLayout()
        self.prepare_btn = QPushButton("✨ Préparer cette recette")
        self.prepare_btn.setObjectName("Primary")
        self.prepare_btn.clicked.connect(self.prepare_recipe)
        actions.addWidget(self.prepare_btn)

        self.continue_btn = QPushButton("▶ Continuer")
        self.continue_btn.clicked.connect(self.continue_recipe)
        actions.addWidget(self.continue_btn)

        actions.addStretch()
        rl.addLayout(actions)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        rl.addWidget(self.status)

        content.addWidget(right, 2)
        root.addLayout(content)

    def selected(self):
        item = self.list.currentItem()
        if item is None:
            return None
        rid = item.data(Qt.ItemDataRole.UserRole)
        return next((r for r in self.recipes if r["id"] == rid), None)

    def populate(self):
        keep = self.selected()["id"] if self.selected() else ""
        cat = self.category.currentData() if hasattr(self, "category") else ""
        self.list.blockSignals(True)
        self.list.clear()
        visible = [r for r in self.recipes if not cat or r["category"] == cat]
        for recipe in visible:
            item = QListWidgetItem(f"{recipe['icon']} {recipe['title']}")
            item.setData(Qt.ItemDataRole.UserRole, recipe["id"])
            self.list.addItem(item)

        row = 0
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == keep:
                row = i
                break
        if self.list.count():
            self.list.setCurrentRow(row)
        self.list.blockSignals(False)
        self.show_recipe()

    def _engine_ready(self, recipe):
        key = recipe.get("engine")
        if not key:
            return True, "Pas de moteur externe obligatoire pour cette recette."
        tools_tab = getattr(self.window, "creative_tools_tab", None)
        if tools_tab is None:
            return False, "Onglet Outils locaux indisponible."
        try:
            root = tools_tab.directory.text()
            p = creative_tools.paths(root, key)
            manifest = creative_tools.read_manifest(root, key)
            source_ok = p["source"].is_dir()
            python_ok = p["python"].is_file()
            installed = source_ok and python_ok and manifest.get("state") == "installé — poids à préparer"
            if installed:
                return True, f"✅ {creative_tools.TOOLS[key]['name']} installé."
            if source_ok or python_ok:
                return False, f"⚠️ {creative_tools.TOOLS[key]['name']} partiellement installé."
            return False, f"⚪ {creative_tools.TOOLS[key]['name']} à installer."
        except Exception as exc:
            return False, f"⚠️ Vérification impossible : {exc}"

    def show_recipe(self):
        recipe = self.selected()
        if not recipe:
            self.title_label.setText("Aucune recette")
            self.note.clear()
            self.engine_state.clear()
            self.steps.setRowCount(0)
            return

        self.title_label.setText(f"{recipe['icon']} {recipe['title']}")
        self.note.setText(recipe["note"])

        ready, detail = self._engine_ready(recipe)
        self.engine_state.setText(("✅ Prérequis moteur : " if ready else "⚠️ Prérequis moteur : ") + detail)

        self.steps.setRowCount(len(recipe["steps"]))
        for row, (action, screen, attr) in enumerate(recipe["steps"]):
            self.steps.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.steps.setItem(row, 1, QTableWidgetItem(action))
            self.steps.setItem(row, 2, QTableWidgetItem(screen))
            btn = QPushButton("Ouvrir")
            btn.setEnabled(getattr(self.window, attr, None) is not None)
            btn.clicked.connect(lambda _=False, a=attr: self.open_attr(a))
            self.steps.setCellWidget(row, 3, btn)

        self.steps.resizeColumnsToContents()
        self.steps.horizontalHeader().setStretchLastSection(True)
        self.prepare_btn.setEnabled(True)
        self.continue_btn.setEnabled(True)
        self.status.setText("Recette chargée. Utilisez « Préparer » pour positionner les bons écrans.")

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is None:
            self.status.setText("Écran indisponible : " + attr)
            return False
        self.window.tabs.setCurrentWidget(tab)
        return True

    def _select_media_category(self, recipe):
        cat = recipe.get("media_category")
        tab = getattr(self.window, "media_studio_tab", None)
        if not cat or tab is None:
            return
        try:
            idx = tab.category.findText(cat)
            if idx >= 0:
                tab.category.setCurrentIndex(idx)
        except Exception:
            pass

    def _select_creative_engine(self, recipe):
        key = recipe.get("engine")
        tab = getattr(self.window, "creative_tools_tab", None)
        if not key or tab is None:
            return
        try:
            idx = tab.choice.findData(key)
            if idx >= 0:
                tab.choice.setCurrentIndex(idx)
        except Exception:
            pass

    def prepare_recipe(self):
        recipe = self.selected()
        if not recipe:
            return

        self._select_media_category(recipe)
        self._select_creative_engine(recipe)

        target = getattr(self.window, recipe.get("target", ""), None)
        if target is not None:
            if recipe["id"] == "sdxl":
                try:
                    target.status.setText(
                        "Recette SDXL : démarrez ComfyUI, actualisez les checkpoints, puis écrivez votre prompt."
                    )
                except Exception:
                    pass
            elif recipe["id"] == "lora":
                try:
                    if hasattr(target, "status"):
                        target.status.setText(
                            "Recette LoRA/QLoRA : modèle de base → dataset → mémoire/rank/batch → entraînement."
                        )
                except Exception:
                    pass
            elif recipe["id"] == "mergekit":
                try:
                    if hasattr(target, "merge_status"):
                        target.merge_status.setText(
                            "Recette MergeKit : installez l’outil, choisissez les modèles compatibles puis la méthode."
                        )
                except Exception:
                    pass
            elif recipe["id"] == "surgery":
                try:
                    if hasattr(target, "status"):
                        target.status.setText(
                            "Recette Chirurgie IA : modèle source → objectif → moteur → benchmark avant/après."
                        )
                except Exception:
                    pass

        ready, _ = self._engine_ready(recipe)
        if recipe.get("engine") and not ready:
            self.open_attr("creative_tools_tab")
            self.status.setText(
                "Le moteur n’est pas encore prêt : IA Manager a sélectionné le bon moteur dans Outils locaux."
            )
        else:
            self.open_attr(recipe.get("target", ""))
            self.status.setText("✅ Recette préparée. Vous pouvez continuer étape par étape.")

    def continue_recipe(self):
        recipe = self.selected()
        if not recipe:
            return
        ready, _ = self._engine_ready(recipe)
        if recipe.get("engine") and not ready:
            self._select_creative_engine(recipe)
            self.open_attr("creative_tools_tab")
            self.status.setText("Étape suivante : installer / réparer le moteur recommandé.")
            return

        self._select_media_category(recipe)
        self.open_attr(recipe.get("target", ""))
        self.status.setText("Étape suivante ouverte.")


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "CRÉER":
                if not any(e[0] == "recipes_tab" for e in entries):
                    entries.insert(0, (
                        "recipes_tab",
                        "Recettes / workflows",
                        "Parcours guidés pour image, audio, vidéo, 3D, entraînement, fusion et chirurgie."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def _add_to_goal_assistant(window):
    tab = getattr(window, "goal_assistant_tab", None)
    if tab is None:
        return
    try:
        # Petit raccourci dans le message de bas de page ; sans reconstruire les cartes v159.
        tab.status.setText(
            "Astuce : pour un parcours complet étape par étape, ouvrez « Recettes / workflows » dans la section CRÉER."
        )
    except Exception:
        pass


def install_v160(window):
    if getattr(window, "_v160_recipes", False):
        return

    tab = RecipesTab(window)
    window.recipes_tab = tab

    media = getattr(window, "media_studio_tab", None)
    idx = window.tabs.indexOf(media)
    insert_at = idx if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "📖 Recettes / workflows")

    _add_nav(window)
    _add_to_goal_assistant(window)

    window._v160_recipes = True
