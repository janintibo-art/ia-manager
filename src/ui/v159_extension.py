"""v159 : Assistant 'Que voulez-vous faire ?'."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)


TASKS = [
    {
        "key": "chat",
        "icon": "💬",
        "title": "Discuter avec une IA",
        "desc": "Poser des questions, rédiger, résumer, traduire ou travailler sur un projet.",
        "target": "chat_tab",
        "button": "Ouvrir le Chat",
    },
    {
        "key": "image",
        "icon": "🎨",
        "title": "Créer une image",
        "desc": "Utiliser ComfyUI et les modèles image locaux installés.",
        "target": "image_studio_tab",
        "button": "Créer une image",
    },
    {
        "key": "audio",
        "icon": "🎵",
        "title": "Créer musique / son",
        "desc": "MusicGen, AudioGen et autres moteurs audio locaux.",
        "target": "media_studio_tab",
        "button": "Créer du son",
        "media_category": "Musique et sons",
    },
    {
        "key": "video",
        "icon": "🎬",
        "title": "Créer une vidéo",
        "desc": "Wan, LTX-Video et workflows vidéo ComfyUI.",
        "target": "media_studio_tab",
        "button": "Créer une vidéo",
        "media_category": "Vidéo",
    },
    {
        "key": "3d",
        "icon": "🧊",
        "title": "Créer un objet 3D",
        "desc": "TripoSR ou Hunyuan3D à partir d'une image de référence.",
        "target": "media_studio_tab",
        "button": "Créer en 3D",
        "media_category": "Modélisation 3D",
    },
    {
        "key": "train",
        "icon": "🧠",
        "title": "Entraîner une IA",
        "desc": "QLoRA / LoRA, dataset et réglages guidés.",
        "target": "training_tab",
        "button": "Entraîner",
    },
    {
        "key": "merge",
        "icon": "🧩",
        "title": "Fusionner des IA",
        "desc": "Fusion de modèles avec MergeKit puis export GGUF / Ollama.",
        "target": "mergekit_tab",
        "button": "Fusionner",
    },
    {
        "key": "surgery",
        "icon": "🧬",
        "title": "Modifier / chirurgicaliser un modèle",
        "desc": "Obliteratus, Heretic, Abliteration Lab ou ErisForge depuis un seul centre.",
        "target": "surgery_dashboard_tab",
        "button": "Ouvrir Chirurgie IA",
    },
    {
        "key": "download",
        "icon": "⬇",
        "title": "Trouver / télécharger un modèle",
        "desc": "Chercher sur Hugging Face, GitHub, ModelScope, Civitai ou Ollama.",
        "target": "search_tab",
        "button": "Rechercher",
    },
    {
        "key": "library",
        "icon": "📚",
        "title": "Gérer mes modèles",
        "desc": "Voir compatibilité, spécialités, taille et modèles installés.",
        "target": "smart_library_tab",
        "button": "Ouvrir la bibliothèque",
    },
    {
        "key": "benchmark",
        "icon": "📊",
        "title": "Comparer des IA",
        "desc": "Mesurer vitesse, VRAM et qualité avec les mêmes prompts.",
        "target": "benchmark_tab",
        "button": "Comparer",
    },
    {
        "key": "health",
        "icon": "🩺",
        "title": "Réparer / diagnostiquer",
        "desc": "Vérifier Python, Git, Ollama, ComfyUI, GPU, ports et stockage.",
        "target": "health_tab",
        "button": "Diagnostiquer",
    },
]


class TaskCard(QFrame):
    def __init__(self, parent, task):
        super().__init__(parent)
        self.parent_page = parent
        self.task = task
        self.setObjectName("AssistantTaskCard")
        self.setMinimumHeight(170)
        self.setStyleSheet("""
        QFrame#AssistantTaskCard {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
        }
        QLabel#AssistantTaskTitle {
            font-size: 16px;
            font-weight: 700;
        }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        title = QLabel(f"{task['icon']} {task['title']}")
        title.setObjectName("AssistantTaskTitle")
        lay.addWidget(title)

        desc = QLabel(task["desc"])
        desc.setWordWrap(True)
        desc.setSizePolicy(desc.sizePolicy().horizontalPolicy(), desc.sizePolicy().verticalPolicy())
        lay.addWidget(desc)

        lay.addStretch()

        btn = QPushButton(task["button"])
        btn.setObjectName("Primary")
        btn.clicked.connect(lambda: self.parent_page.launch(task))
        lay.addWidget(btn)


class GoalAssistantTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cards = []
        self.build_ui()

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

        title = QLabel("✨ Que voulez-vous faire ?")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Choisissez simplement votre objectif. IA Manager ouvre ensuite le bon outil "
            "et prépare le point de départ lorsque c'est possible."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Filtrer : image, vidéo, fusion, réparer…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        search_row.addWidget(self.search, 1)

        health = QPushButton("🩺 Vérifier le PC avant de commencer")
        health.clicked.connect(lambda: self.open_attr("health_tab"))
        search_row.addWidget(health)
        root.addLayout(search_row)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        root.addLayout(self.grid)

        for i, task in enumerate(TASKS):
            card = TaskCard(self, task)
            self.cards.append((task, card))
            self.grid.addWidget(card, i // 3, i % 3)

        self.status = QLabel(
            "Astuce : si vous ne savez pas quel moteur choisir, commencez par l'objectif. "
            "Les détails techniques restent accessibles ensuite."
        )
        self.status.setWordWrap(True)
        self.status.setObjectName("Muted")
        root.addWidget(self.status)

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)
            return True
        self.status.setText("Cet outil n'est pas disponible dans cette version.")
        return False

    def launch(self, task):
        target = task.get("target")
        tab = getattr(self.window, target, None)
        if tab is None:
            self.status.setText(f"{task['title']} : écran indisponible.")
            return

        # Préparation légère et sûre, sans lancer d'action lourde automatiquement.
        if target == "media_studio_tab" and task.get("media_category"):
            try:
                idx = tab.category.findText(task["media_category"])
                if idx >= 0:
                    tab.category.setCurrentIndex(idx)
            except Exception:
                pass

        if target == "image_studio_tab":
            try:
                tab.status.setText(
                    "Assistant IA Manager : vérifiez que ComfyUI est lancé, puis choisissez un checkpoint et décrivez votre image."
                )
            except Exception:
                pass

        if target == "training_tab":
            try:
                if hasattr(tab, "status"):
                    tab.status.setText(
                        "Assistant IA Manager : choisissez d'abord un modèle de base et un dataset avant de lancer l'entraînement."
                    )
            except Exception:
                pass

        if target == "mergekit_tab":
            try:
                if hasattr(tab, "merge_status"):
                    tab.merge_status.setText(
                        "Assistant IA Manager : choisissez les modèles à fusionner puis la méthode MergeKit."
                    )
            except Exception:
                pass

        if target == "surgery_dashboard_tab":
            try:
                if hasattr(tab, "status"):
                    tab.status.setText(
                        "Assistant IA Manager : indiquez le modèle source puis choisissez l'objectif de modification."
                    )
            except Exception:
                pass

        if target == "benchmark_tab":
            try:
                tab.refresh_models()
            except Exception:
                pass

        if target == "smart_library_tab":
            try:
                tab.refresh()
            except Exception:
                pass

        if target == "health_tab":
            try:
                tab.scan()
            except Exception:
                pass

        self.window.tabs.setCurrentWidget(tab)

    def apply_filter(self, text):
        needle = (text or "").strip().casefold()
        visible = []
        for task, card in self.cards:
            hay = " ".join([
                task["title"], task["desc"], task["button"], task["key"]
            ]).casefold()
            show = not needle or needle in hay
            card.setVisible(show)
            if show:
                visible.append(card)

        # Recompose la grille pour éviter les trous.
        for _, card in self.cards:
            self.grid.removeWidget(card)
        for i, card in enumerate(visible):
            self.grid.addWidget(card, i // 3, i % 3)


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ACCUEIL":
                if not any(e[0] == "goal_assistant_tab" for e in entries):
                    entries.insert(0, (
                        "goal_assistant_tab",
                        "Que voulez-vous faire ?",
                        "Choisissez un objectif et laissez IA Manager ouvrir le bon outil."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v159(window):
    if getattr(window, "_v159_goal_assistant", False):
        return

    tab = GoalAssistantTab(window)
    window.goal_assistant_tab = tab

    dashboard = getattr(window, "dashboard_tab", None)
    idx = window.tabs.indexOf(dashboard)
    window.tabs.insertTab(idx if idx >= 0 else 0, tab, "✨ Que voulez-vous faire ?")

    _add_nav(window)
    window._v159_goal_assistant = True
