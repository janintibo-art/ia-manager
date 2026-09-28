"""Branchement isolé du Studio IA v100 à v105."""
import html
from types import MethodType

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.backend import model_search as ms
from src.backend import studio_advisor
from src.backend.studio_pack_v105 import extend_packs_v105
from src.ui.tabs.studio_hub_tab import StudioHubTab
from src.ui.studio_v103 import StudioPlannerPage
from src.ui.studio_v104 import PackInstallerPage
from src.ui.workers import FunctionWorker


def _repair_search_tab(window):
    tab = getattr(window, "search_tab", None)
    if tab is None or getattr(tab, "_v102_search_fixed", False): return
    def current_source_key(self):
        return ("huggingface", "github", "modelscope", "civitai")[self.source.currentIndex()]
    def on_result_selected(self, current, _prev):
        if current is None: return
        repo = current.data(Qt.ItemDataRole.UserRole)
        self.detail_request += 1; rid = self.detail_request
        self.details = None; self.quant_list.clear()
        self.detail.setHtml(f"<h2>{html.escape(str(repo))}</h2><p>⏳ Chargement de la fiche…</p>")
        self.update_buttons()
        self.detail_worker = FunctionWorker(ms.cached_details, self.current_source_key(), repo)
        self.detail_worker.done.connect(lambda ok, res, r=rid, rp=repo: self.on_details(r, rp, ok, res))
        self.detail_worker.start()
    tab.current_source_key = MethodType(current_source_key, tab)
    try: tab.result_list.currentItemChanged.disconnect(tab.on_result_selected)
    except (TypeError, RuntimeError): pass
    tab.on_result_selected = MethodType(on_result_selected, tab)
    tab.result_list.currentItemChanged.connect(tab.on_result_selected)
    tab._v102_search_fixed = True


def _attach_v103(tab):
    if getattr(tab, "_v103_attached", False): return
    page = StudioPlannerPage(tab); page.open_local_tools.connect(tab.open_local_tools.emit)
    tab.planner_v103 = page; tab.tabs.insertTab(0, page, "Mon Studio"); tab._v103_attached = True


def _attach_v104(tab, creative_tab):
    if getattr(tab, "_v104_attached", False): return
    page = PackInstallerPage(tab, creative_tab); page.open_local_tools.connect(tab.open_local_tools.emit)
    tab.installer_v104 = page; tab.tabs.insertTab(1, page, "Installer un pack"); tab._v104_attached = True


def install_v100(window):
    _repair_search_tab(window)
    studio_advisor.extend_catalog()
    extend_packs_v105()
    if hasattr(window, "studio_hub_tab"):
        tab = window.studio_hub_tab; _attach_v103(tab); _attach_v104(tab, window.creative_tools_tab); return tab
    tab = StudioHubTab(); _attach_v103(tab); _attach_v104(tab, window.creative_tools_tab)
    window.studio_hub_tab = tab
    index = window.tabs.addTab(tab, "✨ Studio IA local")
    tab.open_local_tools.connect(lambda: window.tabs.setCurrentWidget(window.creative_tools_tab))
    window.setup_tab.analysis_done.connect(tab.set_system_info)
    window.setup_tab.analysis_done.connect(lambda _info: tab.planner_v103.refresh())
    heading = QListWidgetItem("STUDIO IA"); heading.setFlags(Qt.ItemFlag.NoItemFlags); window.studio_shell.navigation.addItem(heading)
    item = QListWidgetItem("Studio IA local"); item.setData(Qt.ItemDataRole.UserRole, index)
    item.setToolTip("Catalogue, recommandations, installation guidée, profils et pipelines locaux.")
    window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index] = (
        item, "Studio IA local", "Composez un studio adapté, installez ses moteurs et utilitaires, puis préparez vos pipelines.", "STUDIO IA"
    )
    return tab
