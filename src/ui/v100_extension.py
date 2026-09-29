
"""Branchement isolé du Studio IA v100 à v119."""
import base64
import html
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QMessageBox

from src.backend import model_search as ms, studio_advisor, creative_chat, settings
from src.backend import attachments as chat_att
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
from src.ui.studio_v114_mapping import RigMappingClipsPage
from src.ui.studio_v115_library import AnimationLibraryPage
from src.ui.studio_v116_pipeline import CharacterPipelinePage
from src.ui.termux_tab import TermuxTab
from src.ui.workers import FunctionWorker, DownloadWorker, CancellableFunctionWorker
from src.ui import style


def _repair_search_tab(window):
    tab=getattr(window,'search_tab',None)
    if tab is None or getattr(tab,'_v102_search_fixed',False): return
    def current_source_key(self): return ('huggingface','github','modelscope','civitai')[self.source.currentIndex()]
    def on_result_selected(self,current,_prev):
        if current is None:return
        repo=current.data(Qt.ItemDataRole.UserRole); self.detail_request+=1; rid=self.detail_request
        self.details=None; self.quant_list.clear()
        self.detail.setHtml(f"<h2>{html.escape(str(repo))}</h2><p>⏳ Chargement de la fiche…</p>")
        self.update_buttons()
        self.detail_worker=FunctionWorker(ms.cached_details,self.current_source_key(),repo)
        self.detail_worker.done.connect(lambda ok,res,r=rid,rp=repo:self.on_details(r,rp,ok,res))
        self.detail_worker.start()
    tab.current_source_key=MethodType(current_source_key,tab)
    try: tab.result_list.currentItemChanged.disconnect(tab.on_result_selected)
    except (TypeError,RuntimeError): pass
    tab.on_result_selected=MethodType(on_result_selected,tab)
    tab.result_list.currentItemChanged.connect(tab.on_result_selected)
    tab._v102_search_fixed=True


def _repair_ollama_progress(window):
    tab=getattr(window,"search_tab",None)
    if tab is None or getattr(tab,"_v117_ollama_progress",False): return
    old_cancel=tab.cancel_download
    old_done=tab.on_downloaded

    def human_bytes(value):
        value=float(max(0,int(value or 0)))
        for unit in ("o","Ko","Mo","Go"):
            if value<1024 or unit=="Go":
                return f"{value:.1f} {unit}" if unit!="o" else f"{int(value)} {unit}"
            value/=1024

    def on_ollama_progress(self,done,total):
        if total>0:
            self.progress.setRange(0,100)
            self.progress.setValue(min(100,int(done*100/total)))
            self.dl_status.setText(f"⏳ Ollama : {human_bytes(done)} / {human_bytes(total)} ({int(done*100/total)} %)")
        else:self.progress.setRange(0,0)

    def on_ollama_status(self,status):
        if status and self.progress.maximum()==0:self.dl_status.setText("⏳ Ollama : "+str(status))

    def start_download(self,name,size_text=""):
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(self,"Ollama absent","Ollama doit être installé et lancé pour télécharger des modèles.")
            return
        installed={m.lower() for m in self.ai_manager.get_available_models(force=True)}
        if name.lower() in installed:
            self.dl_status.setText(f"✅ {name} est déjà installé.")
            if self.details:self.show_details(self.details)
            return
        self.progress.setVisible(True);self.progress.setRange(0,0);self.progress.setValue(0)
        self.cancel_btn.setVisible(True)
        self.dl_status.setText(f"⏳ Préparation du téléchargement de {name} {size_text}…")
        self.dl_worker=DownloadWorker(self.ai_manager,name)
        self.dl_worker.progress.connect(self.on_ollama_progress)
        self.dl_worker.status.connect(self.on_ollama_status)
        self.dl_worker.finished_ok.connect(lambda ok,err,n=name:self.on_downloaded(ok,err,n))
        self.dl_worker.start();self.update_buttons()

    def cancel_download(self):
        if self.dl_worker is not None and self.dl_worker.isRunning():
            self.dl_worker.stop();self.dl_status.setText("⏹ Annulation Ollama demandée…");return
        old_cancel()

    def on_downloaded(self,ok,error,name):
        self.dl_worker=None;self.progress.setRange(0,100);old_done(ok,error,name)

    tab.on_ollama_progress=MethodType(on_ollama_progress,tab)
    tab.on_ollama_status=MethodType(on_ollama_status,tab)
    tab.start_download=MethodType(start_download,tab)
    tab.cancel_download=MethodType(cancel_download,tab)
    tab.on_downloaded=MethodType(on_downloaded,tab)
    try:tab.cancel_btn.clicked.disconnect()
    except (TypeError,RuntimeError):pass
    tab.cancel_btn.clicked.connect(tab.cancel_download)
    tab._v117_ollama_progress=True


def _attach_creative_chat(window):
    tab=window.chat_tab
    if getattr(tab,"_v119_creative_chat",False):return

    old_refresh=tab.refresh_models
    old_hint=tab.show_hint
    old_send=tab.send_message
    old_render=tab.render_message
    old_link=tab.on_link
    old_settings=tab.open_model_settings
    old_reset=tab.reset_conversation
    old_stop=tab.stop_generation
    tab.creative_worker=None
    tab.creative_generation=0

    def reset_conversation(self):
        self.creative_generation += 1
        return old_reset()

    def refresh_models(self):
        keep=self.current_ref()
        old_refresh()
        for label,ref,model in creative_chat.choices():
            self.model_select.addItem(label,ref)
            i=self.model_select.count()-1
            tip=f"{model['label']}\n{model['specialty']}\n💻 Création locale via {model['engine']}"
            self.model_select.setItemData(i,tip,Qt.ItemDataRole.ToolTipRole)
            self.model_select.setItemData(i,label,Qt.ItemDataRole.AccessibleTextRole)
        if keep and creative_chat.is_creative_ref(keep):
            idx=self.model_select.findData(keep)
            if idx>=0:self.model_select.setCurrentIndex(idx)
        self.show_hint()

    def show_hint(self):
        ref=self.current_ref()
        if not creative_chat.is_creative_ref(ref):
            return old_hint()
        model=creative_chat.model_for_ref(ref)
        state=creative_chat.tool_state(model["engine"])
        status="✅ moteur installé" if state["installed"] else "⚠️ moteur à installer"
        if model["kind"]=="image":
            extra="Décrivez l'image puis Envoyer. ComfyUI doit être démarré et le checkpoint présent."
        elif model["kind"]=="audio":
            extra="Décrivez le son ou la musique. Ajoutez par exemple « durée 12 s » (maximum 20 s)."
        else:
            extra="Joignez une image de référence : le Chat la préparera puis vous dirigera vers le moteur 3D."
        self.hint.setText(f"{model['label']} · {model['specialty']} · {status}\n{extra}")
        self.model_select.setToolTip(f"{model['label']}\n{model['specialty']}\nCréation locale via {model['engine']}")

    def send_message(self):
        ref=self.current_ref()
        if not creative_chat.is_creative_ref(ref):
            return old_send()
        if self.attachment_loading:
            self.status.setText("Attendez la fin du chargement des pièces jointes.")
            return
        if self.creative_worker is not None and self.creative_worker.isRunning():
            self.status.setText("Une création est déjà en cours.")
            return
        text=self.message_input.toPlainText().strip()
        model=creative_chat.model_for_ref(ref)
        if not text and not self.pending:
            return
        if model["kind"] in ("image","audio") and not text:
            QMessageBox.information(self,"Chat créatif","Décrivez ce que vous voulez créer.")
            return

        attachments=list(self.pending)
        display=text or "Créer à partir de l’image jointe."
        message=chat_att.build_message(display,attachments)
        self.messages.append(message)
        self.stream_ref=ref
        self.render_message(len(self.messages)-1,ref)
        self.pending=[]
        self.refresh_attach_bar()
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.status.setText(f"⏳ {model['label']} prépare la création locale…")

        worker=CancellableFunctionWorker(
            creative_chat.generate,ref,text,attachments,
            queue_label="Création locale · "+model["label"],
        )
        self.creative_worker=worker
        generation=self.creative_generation
        worker.done.connect(lambda ok,res,w=worker,r=ref,g=generation:self.creative_done(w,r,g,ok,res))
        self.send_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        worker.start()

    def creative_done(self,worker,ref,generation,ok,result):
        if self.creative_worker is not worker:return
        self.creative_worker=None
        self.send_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        if generation != self.creative_generation:
            self.send_btn.setEnabled(True)
            self.status.setText("Création terminée dans l’ancienne conversation ; résultat ignoré ici.")
            return
        self.send_btn.setEnabled(True)
        if not ok:
            self.system_message("❌ Création impossible : "+html.escape(str(result)))
            self.status.setText("La demande est conservée. Vérifiez le moteur local puis réessayez.")
            return
        answer={
            "role":"assistant",
            "content":str(result.get("text") or "Création terminée."),
            "creative_result":dict(result),
        }
        self.messages.append(answer)
        self.render_message(len(self.messages)-1,ref)
        self.status.setText("✅ Création terminée.")
        try:self.save_current(ref)
        except Exception as exc:self.system_message("⚠️ Sauvegarde impossible : "+html.escape(str(exc)))

    def stop_generation(self):
        if self.creative_worker is not None and self.creative_worker.isRunning():
            self.creative_worker.stop()
            self.status.setText("⏹ Arrêt de la création demandé…")
            return
        preview=getattr(self,"preview3d_worker",None)
        if preview is not None and preview.isRunning():
            preview.stop()
            self.status.setText("⏹ Arrêt de l’aperçu demandé…")
            return
        return old_stop()

    def render_message(self,index,model_ref):
        m=self.messages[index]
        result=m.get("creative_result")
        if not result:
            return old_render(index,model_ref)
        body=html.escape(m.get("content","")).replace("\n","<br>")
        path=str(result.get("path") or "")
        kind=result.get("kind")
        if kind=="image" and path and Path(path).is_file():
            data=base64.b64encode(Path(path).read_bytes()).decode("ascii")
            image=self.image_html(data)
            if image:body+="<br>"+image
            body+=f"<br><a href='creativefile:{index}'>🖼️ Ouvrir l’image originale</a>"
        elif kind=="audio" and path and Path(path).is_file():
            body+=f"<br><a href='creativefile:{index}'>▶️ Écouter le WAV</a>"
            body+=f" · <a href='creativefolder:{index}'>📁 Ouvrir le dossier</a>"
        elif kind=="handoff":
            if path:
                body+=f"<br><a href='creativefile:{index}'>🖼️ Ouvrir la référence préparée</a>"
            body+=f"<br><a href='creativetool:{index}'>🛠️ Installer / démarrer le moteur</a>"
        who="Création · "+str(result.get("label") or "IA locale")
        self.append_html(self.bubble_html(who,body,style.SURFACE,style.GREEN))

    def on_link(self,url):
        link=url.toString()
        kind,_,rest=link.partition(":")
        if kind in ("creativefile","creativefolder","creativetool"):
            try:
                idx=int(rest)
                result=self.messages[idx].get("creative_result") or {}
                if kind=="creativetool":
                    engine=str(result.get("engine") or "")
                    if engine:
                        settings.set("creative_tools_requested",engine)
                        window.tabs.setCurrentWidget(window.creative_tools_tab)
                        self.status.setText("Outils locaux ouvert sur "+engine+".")
                    return
                path=Path(str(result.get("path") or ""))
                if not path.exists():
                    self.status.setText("Fichier créatif introuvable.")
                    return
                target=path.parent if kind=="creativefolder" else path
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))
                return
            except (IndexError,ValueError,OSError) as exc:
                self.status.setText("Action créative impossible : "+str(exc))
                return
        return old_link(url)

    def open_model_settings(self):
        if creative_chat.is_creative_ref(self.current_ref()):
            model=creative_chat.model_for_ref(self.current_ref())
            QMessageBox.information(
                self,"Réglages du modèle créatif",
                f"{model['label']} utilise {model['engine']}.\n\n"
                "Les réglages et l'installation de ce moteur se trouvent dans Outils locaux."
            )
            return
        return old_settings()

    tab.refresh_models=MethodType(refresh_models,tab)
    tab.reset_conversation=MethodType(reset_conversation,tab)
    tab.show_hint=MethodType(show_hint,tab)
    tab.send_message=MethodType(send_message,tab)
    tab.creative_done=MethodType(creative_done,tab)
    tab.stop_generation=MethodType(stop_generation,tab)
    tab.render_message=MethodType(render_message,tab)
    tab.on_link=MethodType(on_link,tab)
    tab.open_model_settings=MethodType(open_model_settings,tab)

    # Reconnecter les signaux qui pointaient vers les anciennes méthodes liées.
    try:tab.model_select.currentIndexChanged.disconnect()
    except (TypeError,RuntimeError):pass
    tab.model_select.currentIndexChanged.connect(tab.show_hint)
    try:tab.send_btn.clicked.disconnect()
    except (TypeError,RuntimeError):pass
    tab.send_btn.clicked.connect(tab.send_message)
    try:tab.stop_btn.clicked.disconnect()
    except (TypeError,RuntimeError):pass
    tab.stop_btn.clicked.connect(tab.stop_generation)
    try:tab.chat_display.anchorClicked.disconnect()
    except (TypeError,RuntimeError):pass
    tab.chat_display.anchorClicked.connect(tab.on_link)

    tab._v119_creative_chat=True
    tab.refresh_models()


def _open_search_result(window,source_index,query):
    tab=window.search_tab;tab.source.setCurrentIndex(int(source_index));tab.query.setText(str(query));window.tabs.setCurrentWidget(tab);tab.search()

def _open_pinokio_result(studio_tab,query):
    page=studio_tab.pinokio_v107;page.query.setText(str(query));idx=studio_tab.tabs.indexOf(page)
    if idx>=0:studio_tab.tabs.setCurrentIndex(idx)
    page.search()

def _attach_v103(tab):
    if getattr(tab,'_v103_attached',False):return
    page=StudioPlannerPage(tab);page.open_local_tools.connect(tab.open_local_tools.emit);tab.planner_v103=page;tab.tabs.insertTab(0,page,'Mon Studio');tab._v103_attached=True

def _attach_v104(tab,creative_tab):
    if getattr(tab,'_v104_attached',False):return
    page=PackInstallerPage(tab,creative_tab);page.open_local_tools.connect(tab.open_local_tools.emit);tab.installer_v104=page;tab.tabs.insertTab(1,page,'Installer un pack');tab._v104_attached=True

def _attach_v111(tab):
    if getattr(tab,'_v111_blender_attached',False):return
    page=BlenderStudioPage();tab.blender_v111=page;tab.tabs.insertTab(2,page,'Blender Studio');tab._v111_blender_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v112(tab):
    if getattr(tab,'_v112_game_ready_attached',False):return
    page=BlenderGameReadyPage(tab.blender_v111);tab.game_ready_v112=page;tab.tabs.insertTab(3,page,'Game Ready');tab._v112_game_ready_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v113(tab):
    if getattr(tab,'_v113_animation_attached',False):return
    page=BlenderAnimationPage(tab.blender_v111);tab.animation_v113=page;tab.tabs.insertTab(4,page,'Animation & Retargeting');tab._v113_animation_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v114(tab):
    if getattr(tab,'_v114_mapping_attached',False):return
    page=RigMappingClipsPage(tab.blender_v111);tab.mapping_v114=page;tab.tabs.insertTab(5,page,'Rig Mapping & Clips');tab._v114_mapping_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v115(tab):
    if getattr(tab,'_v115_library_attached',False):return
    page=AnimationLibraryPage(tab.blender_v111,tab.mapping_v114);tab.library_v115=page;tab.tabs.insertTab(6,page,'Bibliothèque animations');tab._v115_library_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v116(tab):
    if getattr(tab,'_v116_pipeline_attached',False):return
    page=CharacterPipelinePage(tab.blender_v111,tab.mapping_v114);tab.pipeline_v116=page;tab.tabs.insertTab(7,page,'Pipeline personnage');tab._v116_pipeline_attached=True;QApplication.instance().aboutToQuit.connect(page.shutdown)

def _attach_v106(tab):
    if getattr(tab,'_v106_attached',False):return
    page=WeightStoragePage(tab);tab.weights_v106=page;tab.tabs.insertTab(8,page,'Poids & stockage');tab._v106_attached=True

def _attach_v107(tab):
    if getattr(tab,'_v107_attached',False):return
    page=PinokioPage();tab.pinokio_v107=page;tab.tabs.insertTab(9,page,'Pinokio');tab._v107_attached=True

def _attach_v108_sources(tab):
    if getattr(tab,'_v108_sources_attached',False):return
    page=ExtraSourcesPage();tab.sources_v108=page;tab.tabs.insertTab(10,page,'Sources+');tab._v108_sources_attached=True

def _attach_v109(tab,window):
    if getattr(tab,'_v109_attached',False):return
    page=UniversalSearchPage()
    page.open_search_result.connect(lambda source,query:_open_search_result(window,source,query))
    page.open_pinokio.connect(lambda query:_open_pinokio_result(tab,query))
    tab.universal_v109=page;tab.tabs.insertTab(11,page,'Recherche universelle');tab._v109_attached=True

def _attach_termux(window):
    if hasattr(window,'termux_tab'):return window.termux_tab
    tab=TermuxTab();window.termux_tab=tab;index=window.tabs.addTab(tab,'📱 Termux')
    heading=QListWidgetItem('TÉLÉPHONE & TERMINAL');heading.setFlags(Qt.ItemFlag.NoItemFlags);window.studio_shell.navigation.addItem(heading)
    item=QListWidgetItem('Termux');item.setData(Qt.ItemDataRole.UserRole,index);item.setToolTip('Commandes Termux, GitHub et connexion SSH au téléphone.');window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index]=(item,'Termux','Préparez les commandes Android et pilotez Termux en SSH depuis le PC.','TÉLÉPHONE & TERMINAL')
    QApplication.instance().aboutToQuit.connect(tab.shutdown);return tab

def install_v100(window):
    _repair_search_tab(window)
    _repair_ollama_progress(window)
    _attach_creative_chat(window)
    studio_advisor.extend_catalog()
    extend_packs_v105()
    extend_packs_v111()
    if hasattr(window,'studio_hub_tab'):
        tab=window.studio_hub_tab
        _attach_v103(tab);_attach_v104(tab,window.creative_tools_tab);_attach_v111(tab);_attach_v112(tab);_attach_v113(tab);_attach_v114(tab);_attach_v115(tab);_attach_v116(tab);_attach_v106(tab);_attach_v107(tab);_attach_v108_sources(tab);_attach_v109(tab,window);_attach_termux(window)
        return tab
    tab=StudioHubTab()
    _attach_v103(tab);_attach_v104(tab,window.creative_tools_tab);_attach_v111(tab);_attach_v112(tab);_attach_v113(tab);_attach_v114(tab);_attach_v115(tab);_attach_v116(tab);_attach_v106(tab);_attach_v107(tab);_attach_v108_sources(tab);_attach_v109(tab,window)
    window.studio_hub_tab=tab
    index=window.tabs.addTab(tab,'✨ Studio IA local')
    tab.open_local_tools.connect(lambda:window.tabs.setCurrentWidget(window.creative_tools_tab))
    window.setup_tab.analysis_done.connect(tab.set_system_info)
    window.setup_tab.analysis_done.connect(lambda _info:tab.planner_v103.refresh())
    heading=QListWidgetItem('STUDIO IA');heading.setFlags(Qt.ItemFlag.NoItemFlags);window.studio_shell.navigation.addItem(heading)
    item=QListWidgetItem('Studio IA local');item.setData(Qt.ItemDataRole.UserRole,index);item.setToolTip('Pipeline personnage complet, Blender, animations, recherche et stockage.');window.studio_shell.navigation.addItem(item)
    window.studio_shell.entries[index]=(item,'Studio IA local','Transformez automatiquement un modèle 3D en personnage prêt pour le jeu.','STUDIO IA')
    _attach_termux(window)
    return tab
