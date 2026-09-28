"""Branchement isolé du Studio IA v100/v101 et correctifs ciblés v102."""
import html
from types import MethodType

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.backend import model_search as ms
from src.ui.tabs.studio_hub_tab import StudioHubTab
from src.ui.workers import FunctionWorker


def _repair_search_tab(window):
    """Corrige le routage des sources et le chargement des fiches de Recherche."""
    tab = getattr(window, "search_tab", None)
    if tab is None or getattr(tab, "_v102_search_fixed", False):
        return

    def current_source_key(self):
        # Ordre réel de la combo :
        # 0 Hugging Face, 1 GitHub, 2 ModelScope, 3 Civitai.
        return ("huggingface", "github", "modelscope", "civitai")[self.source.currentIndex()]

    def on_result_selected(self, current, _prev):
        if current is None:
            return
        repo = current.data(Qt.ItemDataRole.UserRole)
        self.detail_request += 1
        rid = self.detail_request
        self.details = None
        self.quant_list.clear()
        self.detail.setHtml(
            f"<h2>{html.escape(str(repo))}</h2><p>⏳ Chargement de la fiche…</p>"
        )
        self.update_buttons()

        # Le worker avait été déplacé par erreur dans export_details().
        # Il doit démarrer immédiatement quand l'utilisateur choisit un résultat.
        self.detail_worker = FunctionWorker(ms.cached_details, self.current_source_key(), repo)
        self.detail_worker.done.connect(
            lambda ok, res, r=rid, rp=repo: self.on_details(r, rp, ok, res)
        )
        self.detail_worker.start()

    # current_source_key est consulté dynamiquement par search(), détails, favoris, etc.
    tab.current_source_key = MethodType(current_source_key, tab)

    # La connexion Qt a mémorisé l'ancienne méthode au démarrage :
    # il faut donc la débrancher avant de reconnecter la version corrigée.
    try:
        tab.result_list.currentItemChanged.disconnect(tab.on_result_selected)
    except (TypeError, RuntimeError):
        pass
    tab.on_result_selected = MethodType(on_result_selected, tab)
    tab.result_list.currentItemChanged.connect(tab.on_result_selected)
    tab._v102_search_fixed = True


def install_v100(window):
    """Ajoute le Studio IA sans renuméroter les 19 onglets historiques."""
    _repair_search_tab(window)

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
