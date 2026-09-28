"""Branchement isolé du Studio IA v100/v101 dans l'interface existante."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.tabs.studio_hub_tab import StudioHubTab


def install_v100(window):
    """Ajoute le Studio IA sans renuméroter les 19 onglets historiques."""
    if hasattr(window, 'studio_hub_tab'):
        return window.studio_hub_tab
    tab = StudioHubTab()
    window.studio_hub_tab = tab
    index = window.tabs.addTab(tab, "✨ Studio IA local")
    tab.open_local_tools.connect(lambda: window.tabs.setCurrentWidget(window.creative_tools_tab))
    window.setup_tab.analysis_done.connect(tab.set_system_info)

    heading = QListWidgetItem("STUDIO IA")
    heading.setFlags(Qt.ItemFlag.NoItemFlags)
    window.studio_shell.navigation.addItem(heading)
    item = QListWidgetItem("Studio IA local")
    item.setData(Qt.ItemDataRole.UserRole, index)
    item.setToolTip("Catalogue, favoris, profils et pipelines visuels 100 % locaux.")
    window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index] = (
        item, "Studio IA local", "Choisissez vos modèles, composez vos pipelines et préparez vos outils locaux.", "STUDIO IA"
    )
    return tab
