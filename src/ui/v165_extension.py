"""v165 : Mode Simple / Avancé."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from src.backend import settings


SIMPLE_ATTRS = {
    "goal_assistant_tab",
    "local_assistant_tab",
    "dashboard_tab",
    "chat_tab",
    "models_tab",
    "smart_library_tab",
    "search_tab",
    "download_center_tab",
    "history_tab",
    "recipes_tab",
    "image_studio_tab",
    "media_studio_tab",
    "creative_tools_tab",
    "health_tab",
    "hardware_profiles_tab",
    "storage_tab",
    "tutorial_tab",
}

SIMPLE_SECTIONS = {"ACCUEIL", "CRÉER", "ANALYSER", "SYSTÈME", "AIDE"}


def _find_attr(window, widget):
    for name in dir(window):
        if name.startswith("_"):
            continue
        try:
            if getattr(window, name, None) is widget:
                return name
        except Exception:
            pass
    return ""


def _apply_navigation_mode(window, mode):
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    nav = shell.navigation
    simple = mode == "simple"
    section = None
    section_items = []

    # Masque les entrées avancées, puis masque les titres sans entrée visible.
    for i in range(nav.count()):
        item = nav.item(i)
        kind = item.data(Qt.ItemDataRole.UserRole + 1)

        if kind == "heading":
            if section is not None:
                visible = any(not it.isHidden() for it in section_items)
                section.setHidden(not visible)
            section = item
            section_items = []
            continue

        if kind != "entry":
            continue

        section_items.append(item)

        if not simple:
            item.setHidden(False)
            continue

        index = item.data(Qt.ItemDataRole.UserRole)
        widget = window.tabs.widget(index) if isinstance(index, int) and 0 <= index < window.tabs.count() else None
        attr = _find_attr(window, widget) if widget is not None else ""

        # Navigation simple : uniquement écrans essentiels.
        item.setHidden(attr not in SIMPLE_ATTRS)

    if section is not None:
        visible = any(not it.isHidden() for it in section_items)
        section.setHidden(not visible)

    # Réapplique le filtre texte actuel après changement de mode.
    search = getattr(shell, "v149_filter", None)
    if search is not None:
        text = search.text()
        search.blockSignals(True)
        search.setText("")
        search.blockSignals(False)
        search.setText(text)


class ModeTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.build_ui()
        self.load_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("🎚 Mode Simple / Avancé")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Le Mode Simple allège la navigation sans supprimer aucun outil. "
            "Le Mode Avancé réaffiche toute l'application immédiatement."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Mode d'interface"))
        self.mode = QComboBox()
        self.mode.addItem("🙂 Simple", "simple")
        self.mode.addItem("🛠 Avancé", "advanced")
        self.mode.currentIndexChanged.connect(self.change_mode)
        row.addWidget(self.mode)
        row.addStretch()
        cl.addLayout(row)

        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        cl.addWidget(self.desc)

        self.keep_advanced_entry = QCheckBox(
            "Toujours garder cet écran accessible dans la navigation"
        )
        self.keep_advanced_entry.setChecked(True)
        self.keep_advanced_entry.setEnabled(False)
        cl.addWidget(self.keep_advanced_entry)

        buttons = QHBoxLayout()

        simple = QPushButton("🙂 Passer en Mode Simple")
        simple.setObjectName("Primary")
        simple.clicked.connect(lambda: self.set_mode("simple"))
        buttons.addWidget(simple)

        advanced = QPushButton("🛠 Passer en Mode Avancé")
        advanced.clicked.connect(lambda: self.set_mode("advanced"))
        buttons.addWidget(advanced)

        assistant = QPushButton("✨ Ouvrir « Que voulez-vous faire ? »")
        assistant.clicked.connect(lambda: self.open_attr("goal_assistant_tab"))
        buttons.addWidget(assistant)

        cl.addLayout(buttons)
        root.addWidget(card)

        simple_box = QFrame()
        simple_box.setObjectName("Card")
        sl = QVBoxLayout(simple_box)
        sl.setContentsMargins(16, 16, 16, 16)

        t = QLabel("Mode Simple — écrans mis en avant")
        t.setObjectName("Title")
        sl.addWidget(t)

        text = QLabel(
            "• Que voulez-vous faire ?\n"
            "• Assistant IA Manager\n"
            "• Chat / Modèles / Bibliothèque / Recherche\n"
            "• Téléchargements / Historique\n"
            "• Recettes / Images / Audio-Vidéo-3D / Outils locaux\n"
            "• Centre de santé / Profils matériels / Stockage\n"
            "• Tuto\n\n"
            "Les écrans techniques avancés restent présents et peuvent être ouverts par les recettes, "
            "l'assistant ou les raccourcis internes."
        )
        text.setWordWrap(True)
        sl.addWidget(text)
        root.addWidget(simple_box)

        advanced_box = QFrame()
        advanced_box.setObjectName("Card")
        al = QVBoxLayout(advanced_box)
        al.setContentsMargins(16, 16, 16, 16)

        t2 = QLabel("Mode Avancé — tout IA Manager")
        t2.setObjectName("Title")
        al.addWidget(t2)

        text2 = QLabel(
            "Affiche aussi les outils experts : entraînement, fusion, chirurgie IA, Obliteratus, "
            "Heretic, Abliteration Lab, ErisForge, MergeKit, benchmarks, comparateurs, GitHub, "
            "connexions, téléphone, tâches et autres écrans techniques."
        )
        text2.setWordWrap(True)
        al.addWidget(text2)
        root.addWidget(advanced_box)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addStretch()

    def load_state(self):
        mode = str(settings.get("interface_mode") or "advanced")
        idx = self.mode.findData(mode)
        self.mode.blockSignals(True)
        self.mode.setCurrentIndex(idx if idx >= 0 else self.mode.findData("advanced"))
        self.mode.blockSignals(False)
        self.update_desc(mode)

    def update_desc(self, mode):
        if mode == "simple":
            self.desc.setText(
                "🙂 Mode Simple actif : la barre latérale montre seulement les écrans essentiels. "
                "Aucune fonction n'est supprimée."
            )
        else:
            self.desc.setText(
                "🛠 Mode Avancé actif : tous les écrans et outils techniques sont visibles."
            )

    def set_mode(self, mode):
        idx = self.mode.findData(mode)
        if idx >= 0:
            self.mode.setCurrentIndex(idx)

    def change_mode(self):
        mode = self.mode.currentData()
        settings.set("interface_mode", mode)
        _apply_navigation_mode(self.window, mode)
        self.update_desc(mode)

        goal = getattr(self.window, "goal_assistant_tab", None)
        if goal is not None:
            try:
                goal.status.setText(
                    "Mode Simple actif : commencez par votre objectif."
                    if mode == "simple"
                    else "Mode Avancé actif : tous les outils experts sont visibles."
                )
            except Exception:
                pass

        self.status.setText(
            "✅ Mode Simple appliqué immédiatement."
            if mode == "simple"
            else "✅ Mode Avancé appliqué immédiatement."
        )

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "AIDE":
                if not any(e[0] == "mode_tab" for e in entries):
                    entries.insert(0, (
                        "mode_tab",
                        "Mode Simple / Avancé",
                        "Allégez la navigation ou affichez tous les outils."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def _add_header_switch(window, tab):
    shell = getattr(window, "studio_shell", None)
    if shell is None or hasattr(shell, "v165_mode_button"):
        return

    try:
        header = shell.title.parentWidget()
        layout = header.layout() if header is not None else None
        if layout is None:
            return

        button = QPushButton()
        button.setToolTip("Basculer rapidement entre Mode Simple et Mode Avancé")

        def refresh_text():
            mode = str(settings.get("interface_mode") or "advanced")
            button.setText("🙂 Simple" if mode == "simple" else "🛠 Avancé")

        def toggle():
            current = str(settings.get("interface_mode") or "advanced")
            tab.set_mode("advanced" if current == "simple" else "simple")
            refresh_text()

        button.clicked.connect(toggle)
        layout.addWidget(button)
        shell.v165_mode_button = button
        shell.v165_refresh_mode_button = refresh_text

        old_change = tab.change_mode

        def wrapped_change():
            old_change()
            refresh_text()

        tab.change_mode = wrapped_change
        tab.mode.currentIndexChanged.disconnect()
        tab.mode.currentIndexChanged.connect(tab.change_mode)
        refresh_text()
    except Exception:
        pass


def install_v165(window):
    if getattr(window, "_v165_interface_modes", False):
        return

    tab = ModeTab(window)
    window.mode_tab = tab

    tutorial = getattr(window, "tutorial_tab", None)
    idx = window.tabs.indexOf(tutorial)
    window.tabs.insertTab(idx if idx >= 0 else window.tabs.count(), tab, "🎚 Mode Simple / Avancé")

    _add_nav(window)
    _add_header_switch(window, tab)

    mode = str(settings.get("interface_mode") or "advanced")
    _apply_navigation_mode(window, mode)
    tab.update_desc(mode)

    window._v165_interface_modes = True
