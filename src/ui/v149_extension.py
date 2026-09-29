"""Extension v149 : navigation globale dynamique et check-up visuel."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QListWidgetItem


# Chaque widget connu est affecté à UNE section seulement.
GROUPS = (
    ("ACCUEIL", (
        ("dashboard_tab", "Tableau de bord", "Vue d’ensemble de la mémoire et des IA chargées."),
        ("chat_tab", "Chat", "Discutez avec vos modèles locaux et connectés."),
        ("models_tab", "Modèles", "Organisez les modèles présents sur votre machine."),
        ("search_tab", "Recherche", "Trouvez et installez de nouveaux modèles."),
    )),
    ("CRÉER", (
        ("projects_tab", "Projets", "Retrouvez vos fichiers, consignes et conversations."),
        ("workspace_tab", "Espace de travail", "Préparez documents, profils et essais."),
        ("training_tab", "Entraîner / Fusionner", "Spécialisez et fusionnez vos modèles."),
        ("image_studio_tab", "Création d’images", "Créez des images avec vos moteurs locaux."),
        ("media_studio_tab", "Audio · Vidéo · 3D", "Travaillez avec les modèles multimédia."),
        ("creative_tools_tab", "Outils locaux", "Installez et démarrez les moteurs créatifs."),
    )),
    ("CHIRURGIE & FUSION", (
        ("surgery_dashboard_tab", "Chirurgie IA", "Centre de commande des outils de modification de modèles."),
        ("obliteratus_tab", "Obliteratus", "Modification guidée et versions locales."),
        ("heretic_tab", "Heretic", "Optimisation automatique d’abliteration."),
        ("abliteration_lab_tab", "Abliteration Lab", "Projected, biprojected et norm-preserving."),
        ("erisforge_tab", "ErisForge", "Transformations comportementales par directions."),
        ("mergekit_tab", "MergeKit", "Fusionnez plusieurs modèles et variantes."),
        ("family_tree_tab", "Famille IA", "Visualisez la filiation de vos modèles."),
        ("benchmark_tab", "Benchmark IA", "Comparez performances et critères qualitatifs."),
    )),
    ("ANALYSER", (
        ("setup_tab", "Analyse", "Vérifiez le matériel et l’installation."),
        ("comparator_tab", "Comparateur", "Comparez plusieurs réponses côte à côte."),
        ("bench_tab", "Test de vitesse", "Mesurez les performances de la configuration."),
    )),
    ("SYSTÈME", (
        ("connections_tab", "Connexions", "Configurez Ollama, LM Studio et les services API."),
        ("tasks_tab", "Tâches", "Planifiez et suivez vos travaux automatiques."),
        ("github_tab", "GitHub", "Gérez vos dépôts et workflows."),
        ("mobile_tab", "Téléphone", "Connectez Android à IA Manager."),
    )),
    ("AIDE", (
        ("tutorial_tab", "Tuto", "Retrouvez les explications et conseils d’utilisation."),
    )),
)


def _actual_index(window, attr):
    widget = getattr(window, attr, None)
    if widget is None:
        return -1
    return window.tabs.indexOf(widget)


def _all_grouped_widgets(window):
    widgets = set()
    for _, entries in GROUPS:
        for attr, _, _ in entries:
            widget = getattr(window, attr, None)
            if widget is not None:
                widgets.add(widget)
    return widgets


def _rebuild_navigation(window):
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    nav = shell.navigation
    current_widget = window.tabs.currentWidget()
    nav.blockSignals(True)
    nav.clear()
    shell.entries.clear()

    for section, entries in GROUPS:
        available = []
        for attr, title, subtitle in entries:
            index = _actual_index(window, attr)
            if index >= 0:
                available.append((index, title, subtitle))

        if not available:
            continue

        heading = QListWidgetItem(section)
        heading.setFlags(Qt.ItemFlag.NoItemFlags)
        heading.setData(Qt.ItemDataRole.UserRole + 1, "heading")
        nav.addItem(heading)

        for index, title, subtitle in available:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setData(Qt.ItemDataRole.UserRole + 1, "entry")
            item.setToolTip(subtitle)
            nav.addItem(item)
            shell.entries[index] = (item, title, subtitle, section)

    # Tout onglet ajouté par une future version reste accessible automatiquement.
    grouped = _all_grouped_widgets(window)
    unknown = []
    for index in range(window.tabs.count()):
        widget = window.tabs.widget(index)
        if widget not in grouped:
            unknown.append((index, window.tabs.tabText(index)))

    if unknown:
        heading = QListWidgetItem("AUTRES")
        heading.setFlags(Qt.ItemFlag.NoItemFlags)
        heading.setData(Qt.ItemDataRole.UserRole + 1, "heading")
        nav.addItem(heading)
        for index, title in unknown:
            clean = title.strip() or f"Écran {index + 1}"
            subtitle = "Écran supplémentaire installé dans IA Manager."
            item = QListWidgetItem(clean)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setData(Qt.ItemDataRole.UserRole + 1, "entry")
            item.setToolTip(subtitle)
            nav.addItem(item)
            shell.entries[index] = (item, clean, subtitle, "AUTRES")

    nav.blockSignals(False)

    idx = window.tabs.indexOf(current_widget)
    if idx >= 0:
        shell._sync(idx)


def _add_filter(window):
    shell = getattr(window, "studio_shell", None)
    if shell is None or hasattr(shell, "v149_filter"):
        return

    nav = shell.navigation
    parent = nav.parentWidget()
    layout = parent.layout() if parent is not None else None
    if layout is None:
        return

    search = QLineEdit()
    search.setPlaceholderText("🔎 Filtrer les écrans…")
    search.setClearButtonEnabled(True)
    search.setToolTip("Tapez par exemple : Heretic, image, GitHub, benchmark…")
    search.setAccessibleName("Filtrer la navigation")
    search.setMaximumHeight(38)

    index = layout.indexOf(nav)
    layout.insertWidget(max(0, index), search)
    shell.v149_filter = search

    def apply_filter(text):
        needle = (text or "").strip().casefold()

        # Entrées visibles selon la recherche.
        section_has_visible = {}
        current_section = None
        for i in range(nav.count()):
            item = nav.item(i)
            kind = item.data(Qt.ItemDataRole.UserRole + 1)
            if kind == "heading":
                current_section = item.text()
                section_has_visible[current_section] = False
                continue

            hay = (item.text() + " " + item.toolTip()).casefold()
            visible = not needle or needle in hay
            item.setHidden(not visible)
            if current_section and visible:
                section_has_visible[current_section] = True

        # Masque les titres de sections sans résultat.
        current_section = None
        for i in range(nav.count()):
            item = nav.item(i)
            kind = item.data(Qt.ItemDataRole.UserRole + 1)
            if kind == "heading":
                current_section = item.text()
                item.setHidden(bool(needle) and not section_has_visible.get(current_section, False))

    search.textChanged.connect(apply_filter)


def _polish_shell(window):
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    nav = shell.navigation
    # Un rail légèrement plus large évite les titres coupés tout en laissant
    # assez d’espace au contenu principal.
    nav.setMinimumWidth(250)
    nav.setMaximumWidth(280)

    # Le bandeau supérieur ne doit pas prendre trop de place verticalement.
    try:
        header = shell.title.parentWidget()
        if header is not None:
            header.setMaximumHeight(128)
    except Exception:
        pass


def _refresh_on_tab_insertions(window):
    """Expose une fonction réutilisable par les futures extensions."""
    shell = getattr(window, "studio_shell", None)
    if shell is None:
        return

    def refresh_navigation():
        _rebuild_navigation(window)
        if hasattr(shell, "v149_filter"):
            text = shell.v149_filter.text()
            shell.v149_filter.setText("")
            shell.v149_filter.setText(text)

    shell.refresh_navigation = refresh_navigation


def install_v149(window):
    if getattr(window, "_v149_global_navigation", False):
        return

    _rebuild_navigation(window)
    _add_filter(window)
    _polish_shell(window)
    _refresh_on_tab_insertions(window)

    # Check-up : tous les onglets réellement présents doivent avoir une entrée.
    shell = getattr(window, "studio_shell", None)
    mapped = len(shell.entries) if shell is not None else 0
    total = window.tabs.count()

    surgery = getattr(window, "surgery_dashboard_tab", None)
    if surgery is not None and hasattr(surgery, "status"):
        surgery.status.setText(
            f"Navigation globale vérifiée : {mapped}/{total} écrans accessibles depuis la barre latérale."
        )

    window._v149_global_navigation = True
