
"""Branchement isolé du Studio IA v100 à v113."""
import html
from types import MethodType
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication,QListWidgetItem
from src.backend import model_search as ms, studio_advisor
from src.backend.studio_pack_v105 import extend_packs_v105
from src.backend.studio_pack_v111 import extend_packs_v111
from src.ui.tabs.studio_hub_tab import StudioHubTab
from src.ui.studio_v103 import StudioPlannerPage
from src.ui.studio_v104 import PackInstallerPage
from src.ui.studio_v106 import WeightStoragePage
from src.ui.studio_v107 import PinokioPage
from src.ui.studio_v108_sources import ExtraSourcesPage
from src.ui.studio_v109_universal import UniversalSearchPage
from src.ui.studio_v111_blender import BlenderStudioPage
from src.ui.studio_v112_game_ready import BlenderGameReadyPage
from src.ui.studio_v113_animation import BlenderAnimationPage
from src.ui.termux_tab import TermuxTab
from src.ui.workers import FunctionWorker

def _repair_search_tab(window):
    tab=getattr(window,'search_tab',None)
    if tab is None or getattr(tab,'_v102_search_fixed',False): return
    def current_source_key(self): return ('huggingface','github','modelscope','civitai')[self.source.currentIndex()]
    def on_result_selected(self,current,_prev):
        if current is None:return
        repo=current.data(Qt.ItemDataRole.UserRole); self.detail_request+=1; rid=self.detail_request
        self.details=None; self.quant_list.clear(); self.detail.setHtml(f"<h2>{html.escape(str(repo))}</h2><p>⏳ Chargement de la fiche…</p>"); self.update_buttons()
        self.detail_worker=FunctionWorker(ms.cached_details,self.current_source_key(),repo)
        self.detail_worker.done.connect(lambda ok,res,r=rid,rp=repo:self.on_details(r,rp,ok,res)); self.detail_worker.start()
    tab.current_source_key=MethodType(current_source_key,tab)
    try: tab.result_list.currentItemChanged.disconnect(tab.on_result_selected)
    except (TypeError,RuntimeError): pass
    tab.on_result_selected=MethodType(on_result_selected,tab); tab.result_list.currentItemChanged.connect(tab.on_result_selected); tab._v102_search_fixed=True

def _open_search_result(window,source_index,query):
    tab=window.search_tab; tab.source.setCurrentIndex(int(source_index)); tab.query.setText(str(query)); window.tabs.setCurrentWidget(tab); tab.search()

def _open_pinokio_result(studio_tab,query):
    page=studio_tab.pinokio_v107; page.query.setText(str(query)); idx=studio_tab.tabs.indexOf(page)
    if idx>=0: studio_tab.tabs.setCurrentIndex(idx)
    page.search()

def _attach_v103(tab):
    if getattr(tab,'_v103_attached',False):return
    page=StudioPlannerPage(tab); page.open_local_tools.connect(tab.open_local_tools.emit); tab.planner_v103=page; tab.tabs.insertTab(0,page,'Mon Studio'); tab._v103_attached=True

def _attach_v104(tab,creative_tab):
    if getattr(tab,'_v104_attached',False):return
    page=PackInstallerPage(tab,creative_tab); page.open_local_tools.connect(tab.open_local_tools.emit); tab.installer_v104=page; tab.tabs.insertTab(1,page,'Installer un pack'); tab._v104_attached=True

def _attach_v111(tab):
    if getattr(tab,'_v111_blender_attached',False):return
    page=BlenderStudioPage(); tab.blender_v111=page; tab.tabs.insertTab(2,page,'Blender Studio'); tab._v111_blender_attached=True; QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v112(tab):
    if getattr(tab,'_v112_game_ready_attached',False):return
    page=BlenderGameReadyPage(tab.blender_v111); tab.game_ready_v112=page; tab.tabs.insertTab(3,page,'Game Ready'); tab._v112_game_ready_attached=True; QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v113(tab):
    if getattr(tab,'_v113_animation_attached',False):return
    page=BlenderAnimationPage(tab.blender_v111); tab.animation_v113=page; tab.tabs.insertTab(4,page,'Animation & Retargeting'); tab._v113_animation_attached=True; QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v106(tab):
    if getattr(tab,'_v106_attached',False):return
    page=WeightStoragePage(tab); tab.weights_v106=page; tab.tabs.insertTab(5,page,'Poids & stockage'); tab._v106_attached=True

def _attach_v107(tab):
    if getattr(tab,'_v107_attached',False):return
    page=PinokioPage(); tab.pinokio_v107=page; tab.tabs.insertTab(6,page,'Pinokio'); tab._v107_attached=True

def _attach_v108_sources(tab):
    if getattr(tab,'_v108_sources_attached',False):return
    page=ExtraSourcesPage(); tab.sources_v108=page; tab.tabs.insertTab(7,page,'Sources+'); tab._v108_sources_attached=True

def _attach_v109(tab,window):
    if getattr(tab,'_v109_attached',False):return
    page=UniversalSearchPage(); page.open_search_result.connect(lambda source,query:_open_search_result(window,source,query)); page.open_pinokio.connect(lambda query:_open_pinokio_result(tab,query))
    tab.universal_v109=page; tab.tabs.insertTab(8,page,'Recherche universelle'); tab._v109_attached=True

def _attach_termux(window):
    if hasattr(window,'termux_tab'):return window.termux_tab
    tab=TermuxTab(); window.termux_tab=tab; index=window.tabs.addTab(tab,'📱 Termux')
    heading=QListWidgetItem('TÉLÉPHONE & TERMINAL'); heading.setFlags(Qt.ItemFlag.NoItemFlags); window.studio_shell.navigation.addItem(heading)
    item=QListWidgetItem('Termux'); item.setData(Qt.ItemDataRole.UserRole,index); item.setToolTip('Commandes Termux, GitHub et connexion SSH au téléphone.'); window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index]=(item,'Termux','Préparez les commandes Android et pilotez Termux en SSH depuis le PC.','TÉLÉPHONE & TERMINAL')
    QApplication.instance().aboutToQuit.connect(tab.shutdown); return tab

def install_v100(window):
    _repair_search_tab(window); studio_advisor.extend_catalog(); extend_packs_v105(); extend_packs_v111()
    if hasattr(window,'studio_hub_tab'):
        tab=window.studio_hub_tab
        _attach_v103(tab); _attach_v104(tab,window.creative_tools_tab); _attach_v111(tab); _attach_v112(tab); _attach_v113(tab); _attach_v106(tab); _attach_v107(tab); _attach_v108_sources(tab); _attach_v109(tab,window); _attach_termux(window)
        return tab
    tab=StudioHubTab()
    _attach_v103(tab); _attach_v104(tab,window.creative_tools_tab); _attach_v111(tab); _attach_v112(tab); _attach_v113(tab); _attach_v106(tab); _attach_v107(tab); _attach_v108_sources(tab); _attach_v109(tab,window)
    window.studio_hub_tab=tab; index=window.tabs.addTab(tab,'✨ Studio IA local')
    tab.open_local_tools.connect(lambda:window.tabs.setCurrentWidget(window.creative_tools_tab)); window.setup_tab.analysis_done.connect(tab.set_system_info); window.setup_tab.analysis_done.connect(lambda _info:tab.planner_v103.refresh())
    heading=QListWidgetItem('STUDIO IA'); heading.setFlags(Qt.ItemFlag.NoItemFlags); window.studio_shell.navigation.addItem(heading)
    item=QListWidgetItem('Studio IA local'); item.setData(Qt.ItemDataRole.UserRole,index); item.setToolTip('Blender, Game Ready, animations, retargeting, recherche et stockage.'); window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index]=(item,'Studio IA local','Préparez, optimisez et animez vos personnages 3D IA avant export jeu.','STUDIO IA')
    _attach_termux(window); return tab
