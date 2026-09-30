"""v166 : grand check-up UX, dédoublonnage et pages plus lisibles."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QWidget,
)

from src.backend import settings


# En mode simple, on garde une seule porte d'entrée par besoin.
SIMPLE_ATTRS = {
    "goal_assistant_tab",       # démarrer / choisir un objectif
    "local_assistant_tab",      # dépannage intelligent
    "chat_tab",
    "smart_library_tab",        # remplace l'accès direct au catalogue détaillé
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
    "mode_tab",                 # toujours permettre de revenir en avancé
}

SIMPLE_TITLES = {
    "goal_assistant_tab": "Démarrer",
    "local_assistant_tab": "Aide intelligente",
    "chat_tab": "Chat",
    "smart_library_tab": "Mes modèles",
    "search_tab": "Trouver un modèle",
    "download_center_tab": "Téléchargements",
    "history_tab": "Historique",
    "recipes_tab": "Guides & recettes",
    "image_studio_tab": "Images",
    "media_studio_tab": "Audio · Vidéo · 3D",
    "creative_tools_tab": "Moteurs locaux",
    "health_tab": "Diagnostic",
    "hardware_profiles_tab": "Matériel & profils",
    "storage_tab": "Stockage",
    "tutorial_tab": "Tuto",
    "mode_tab": "Mode Simple / Avancé",
}


def _widget_attr(window, widget):
    if widget is None:
        return ""
    # Liste ciblée avant le fallback : évite un scan coûteux de toutes les propriétés Qt.
    known = set(SIMPLE_ATTRS) | {
        "dashboard_tab", "models_tab", "projects_tab", "workspace_tab",
        "training_tab", "surgery_dashboard_tab", "obliteratus_tab",
        "heretic_tab", "abliteration_lab_tab", "erisforge_tab",
        "mergekit_tab", "family_tree_tab", "benchmark_tab",
        "setup_tab", "comparator_tab", "bench_tab", "connections_tab",
        "tasks_tab", "github_tab", "mobile_tab", "studio_hub_tab", "termux_tab",
    }
    for attr in known:
        if getattr(window, attr, None) is widget:
            return attr
    return ""


def _mode(window):
    return str(settings.get("interface_mode") or "advanced")


def _apply_nav(window):
    """Filtre texte + mode Simple/Avancé en une seule passe."""
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    nav = shell.navigation
    search = getattr(shell, "v149_filter", None)
    needle = search.text().strip().casefold() if search is not None else ""
    simple = _mode(window) == "simple"

    current_heading = None
    section_entries = []

    def finish_section():
        if current_heading is not None:
            current_heading.setHidden(not any(not item.isHidden() for item in section_entries))

    for i in range(nav.count()):
        item = nav.item(i)
        kind = item.data(Qt.ItemDataRole.UserRole + 1)

        if kind == "heading":
            finish_section()
            current_heading = item
            section_entries = []
            continue

        if kind != "entry":
            continue

        section_entries.append(item)
        index = item.data(Qt.ItemDataRole.UserRole)
        widget = window.tabs.widget(index) if isinstance(index, int) and 0 <= index < window.tabs.count() else None
        attr = _widget_attr(window, widget)

        # Restaurer le titre d'origine en avancé ; utiliser des noms orientés besoin en simple.
        entry = shell.entries.get(index)
        original_title = entry[1] if entry else item.text()
        original_subtitle = entry[2] if entry else item.toolTip()
        item.setText(SIMPLE_TITLES.get(attr, original_title) if simple else original_title)

        allowed_by_mode = (not simple) or (attr in SIMPLE_ATTRS)
        hay = (item.text() + " " + original_subtitle).casefold()
        allowed_by_search = (not needle) or needle in hay
        item.setHidden(not (allowed_by_mode and allowed_by_search))

    finish_section()


def _repair_navigation_mode(window):
    """Corrige l'interaction v149 filtre <-> v165 Mode Simple."""
    try:
        from src.ui import v165_extension as v165
        v165.SIMPLE_ATTRS = set(SIMPLE_ATTRS)
        v165._apply_navigation_mode = lambda w, mode: _apply_nav(w)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    search = getattr(shell, "v149_filter", None)
    if search is not None and not getattr(search, "_v166_filter", False):
        try:
            search.textChanged.disconnect()
        except Exception:
            pass
        search.textChanged.connect(lambda _text: _apply_nav(window))
        search._v166_filter = True

    mode_tab = getattr(window, "mode_tab", None)
    if mode_tab is not None and not getattr(mode_tab, "_v166_mode", False):
        old_change = mode_tab.change_mode

        def change_mode():
            old_change()
            _apply_nav(window)
            simple = _mode(window) == "simple"
            mode_tab.status.setText(
                "✅ Mode Simple : navigation épurée par besoin."
                if simple else
                "✅ Mode Avancé : tous les outils techniques sont visibles."
            )

        mode_tab.change_mode = change_mode
        try:
            mode_tab.mode.currentIndexChanged.disconnect()
        except Exception:
            pass
        mode_tab.mode.currentIndexChanged.connect(mode_tab.change_mode)
        mode_tab._v166_mode = True

    _apply_nav(window)


def _button_by_text(parent, text):
    for button in parent.findChildren(QPushButton):
        if button.text() == text:
            return button
    return None


def _install_chat_clarity(window):
    tab = getattr(window, "chat_tab", None)
    if tab is None or getattr(tab, "_v166_clarity", False):
        return

    advanced = []
    for attr in (
        "code_mode", "web_mode", "memory_mode", "commands_btn",
        "profile_label", "context_label", "compact_btn", "restore_code_btn",
    ):
        widget = getattr(tab, attr, None)
        if widget is not None:
            advanced.append(widget)

    for text in ("✨ Tâches", "↶ Reprendre ma demande", "💾 Exporter la discussion", "Ouvrir les archives"):
        widget = _button_by_text(tab, text)
        if widget is not None:
            advanced.append(widget)

    # Un petit bandeau remplace plusieurs rangées d'options en utilisation courante.
    bar = QFrame(tab)
    bar.setObjectName("Card")
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(10, 6, 10, 6)

    label = QLabel("Discussion")
    label.setObjectName("Muted")
    lay.addWidget(label)
    lay.addStretch()

    toggle = QPushButton("⚙ Options avancées")
    toggle.setCheckable(True)
    toggle.setChecked(_mode(window) != "simple")
    lay.addWidget(toggle)

    try:
        tab.layout().insertWidget(2, bar)
    except Exception:
        tab.layout().addWidget(bar)

    def apply(checked=None):
        show = toggle.isChecked() if checked is None else bool(checked)
        for widget in advanced:
            widget.setVisible(show)
        toggle.setText("▴ Masquer les options" if show else "⚙ Options avancées")

    toggle.toggled.connect(apply)
    apply()

    tab.v166_advanced_toggle = toggle
    tab.v166_advanced_widgets = advanced
    tab._v166_clarity = True


def _install_tools_clarity(window):
    tab = getattr(window, "creative_tools_tab", None)
    if tab is None or getattr(tab, "_v166_clarity", False):
        return

    doctor = None
    importer = None
    for box in tab.findChildren(QGroupBox):
        title = box.title()
        if "ComfyUI Doctor" in title:
            doctor = box
        elif "Importer les modèles téléchargés" in title:
            importer = box

    bar = QFrame(tab)
    bar.setObjectName("Card")
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(10, 6, 10, 6)

    lay.addWidget(QLabel("Affichage :"))

    doctor_btn = QPushButton("🩺 ComfyUI Doctor")
    doctor_btn.setCheckable(True)
    doctor_btn.setChecked(False)
    doctor_btn.setEnabled(doctor is not None)
    lay.addWidget(doctor_btn)

    import_btn = QPushButton("📥 Import modèles")
    import_btn.setCheckable(True)
    import_btn.setChecked(False)
    import_btn.setEnabled(importer is not None)
    lay.addWidget(import_btn)

    log_btn = QPushButton("📜 Journal technique")
    log_btn.setCheckable(True)
    log_btn.setChecked(False)
    lay.addWidget(log_btn)

    lay.addStretch()

    try:
        tab.layout().insertWidget(1, bar)
    except Exception:
        tab.layout().addWidget(bar)

    if doctor is not None:
        doctor.setVisible(False)
        doctor_btn.toggled.connect(doctor.setVisible)
    if importer is not None:
        importer.setVisible(False)
        import_btn.toggled.connect(importer.setVisible)

    log = getattr(tab, "log", None)
    if log is not None:
        log.setVisible(False)
        log_btn.toggled.connect(log.setVisible)

    # Les infos restent disponibles mais ne saturent plus la page au démarrage.
    tab.v166_doctor_btn = doctor_btn
    tab.v166_import_btn = import_btn
    tab.v166_log_btn = log_btn
    tab._v166_clarity = True


def _frame_with_label(parent, needle):
    for frame in parent.findChildren(QFrame):
        for label in frame.findChildren(QLabel):
            if needle in label.text():
                return frame
    return None


def _install_analysis_clarity(window):
    tab = getattr(window, "setup_tab", None)
    if tab is None or getattr(tab, "_v166_clarity", False):
        return

    quick = _frame_with_label(tab, "Bien démarrer")
    allocation = _frame_with_label(tab, "Répartition de la mémoire")

    # "Bien démarrer" fait doublon avec Démarrer + Centre de santé.
    if quick is not None:
        quick.setVisible(False)

    if allocation is not None:
        allocation.setVisible(False)

    bar = QFrame(tab)
    bar.setObjectName("Card")
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(10, 6, 10, 6)
    lay.addWidget(QLabel("Vue : matériel + recommandations"))
    lay.addStretch()

    alloc_btn = QPushButton("⚙ Répartition VRAM / RAM")
    alloc_btn.setCheckable(True)
    alloc_btn.setChecked(False)
    alloc_btn.setEnabled(allocation is not None)
    lay.addWidget(alloc_btn)

    if allocation is not None:
        alloc_btn.toggled.connect(allocation.setVisible)

    # Le contenu est dans le QScrollArea : insérer dans son widget.
    try:
        scroll = tab.findChild(__import__("PyQt6.QtWidgets", fromlist=["QScrollArea"]).QScrollArea)
        if scroll is not None and scroll.widget() is not None:
            scroll.widget().layout().insertWidget(1, bar)
        else:
            tab.layout().addWidget(bar)
    except Exception:
        pass

    tab.v166_alloc_btn = alloc_btn
    tab._v166_clarity = True


def _rename_advanced_hubs(window):
    """Les noms doivent expliquer le rôle au lieu de laisser croire à un doublon."""
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    # Studio IA est surtout devenu un atelier 3D / Blender / pipeline.
    studio = getattr(window, "studio_hub_tab", None)
    if studio is not None:
        idx = window.tabs.indexOf(studio)
        if idx >= 0:
            window.tabs.setTabText(idx, "🧊 Studio 3D / Blender")
        entry = shell.entries.get(idx)
        if entry:
            item, _title, _subtitle, section = entry
            shell.entries[idx] = (
                item,
                "Studio 3D / Blender",
                "Pipeline personnage, Blender, rig, animations, Pinokio et outils 3D.",
                section,
            )

    # L'onglet Analyse est le matériel réel, le Centre de santé est le diagnostic logiciel.
    setup = getattr(window, "setup_tab", None)
    if setup is not None:
        idx = window.tabs.indexOf(setup)
        entry = shell.entries.get(idx)
        if entry:
            item, _title, _subtitle, section = entry
            shell.entries[idx] = (
                item,
                "Mon PC",
                "Matériel détecté, recommandations de modèles et répartition mémoire.",
                section,
            )

    models = getattr(window, "models_tab", None)
    if models is not None:
        idx = window.tabs.indexOf(models)
        entry = shell.entries.get(idx)
        if entry:
            item, _title, _subtitle, section = entry
            shell.entries[idx] = (
                item,
                "Catalogue conseillé",
                "Fiches détaillées et modèles recommandés du catalogue IA Manager.",
                section,
            )

    smart = getattr(window, "smart_library_tab", None)
    if smart is not None:
        idx = window.tabs.indexOf(smart)
        entry = shell.entries.get(idx)
        if entry:
            item, _title, _subtitle, section = entry
            shell.entries[idx] = (
                item,
                "Mes modèles",
                "Modèles installés, compatibilité et gestion quotidienne.",
                section,
            )

    _apply_nav(window)


def install_v166(window):
    if getattr(window, "_v166_checkup", False):
        return

    _repair_navigation_mode(window)
    _install_chat_clarity(window)
    _install_tools_clarity(window)
    _install_analysis_clarity(window)
    _rename_advanced_hubs(window)

    # Résumé discret dans l'assistant d'accueil.
    goal = getattr(window, "goal_assistant_tab", None)
    if goal is not None:
        try:
            goal.status.setText(
                "Interface consolidée : les fonctions expertes restent disponibles, "
                "mais les pages courantes sont plus légères."
            )
        except Exception:
            pass

    window._v166_checkup = True
