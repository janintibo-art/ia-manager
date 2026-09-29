"""v151 : Python automatique pour Outils locaux."""
import os
from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtWidgets import QLabel, QPushButton
from src.backend import python_auto_install as pai
from src.ui import v150_extension as v150

def _set_controls(tab,busy):
    tab.v151_auto_btn.setEnabled(not busy)
    tab.choice.setEnabled(not busy)
    tab.install.setEnabled(not busy and not bool(tab.active))
    tab.pick_python.setEnabled(not busy)
    tab.python.setEnabled(not busy)

def _update_button(tab):
    tag=pai.required_tag(tab.choice.currentData())
    tab.v151_auto_btn.setText(f"⚡ Installer automatiquement Python {tag}")

def _finish_success(tab,path):
    tab.python.setText(path)
    _set_controls(tab,False)
    tab.v151_status.setText("✅ Python installé et détecté automatiquement. Cliquez maintenant sur « 1 · Installer / reprendre ».")
    tab.status.setText("✅ Python prêt : "+path)

def _find_runtime(tab):
    tag=pai.required_tag(tab.choice.currentData())
    found=v150._detect(tab,False)
    if found:return found
    manager=pai.manager_program()
    return pai.runtime_from_manager(manager,tag) if manager else ""

def _after_install(tab):
    found=_find_runtime(tab)
    if found:
        _finish_success(tab,found);return
    _set_controls(tab,False)
    tab.v151_status.setText("⚠️ Python a été installé mais son chemin n'est pas encore visible. Fermez puis relancez IA Manager, puis cliquez sur Détecter automatiquement le bon Python.")

def _start_runtime_install(tab):
    tag=pai.required_tag(tab.choice.currentData())
    manager=pai.manager_program()
    if not manager:
        _set_controls(tab,False)
        tab.v151_status.setText("⚠️ Python Install Manager reste introuvable. Utilisez « Télécharger Python (site officiel) », puis relancez IA Manager.")
        return
    tab.v151_mode="runtime"
    env=QProcessEnvironment.systemEnvironment()
    env.insert("PYTHON_MANAGER_CONFIRM","0")
    env.insert("PYTHONUNBUFFERED","1")
    tab.v151_process.setProcessEnvironment(env)
    tab.v151_status.setText(f"⬇️ Installation automatique de Python {tag}… Vous n’avez rien à saisir.")
    tab.v151_process.start(manager,["install",tag])

def _auto_install(tab):
    if tab.v151_process.state()!=QProcess.ProcessState.NotRunning:return
    found=_find_runtime(tab)
    if found:
        _finish_success(tab,found);return
    if os.name!="nt":
        tab.v151_status.setText("Installation automatique prévue pour Windows.")
        return
    _set_controls(tab,True)
    if pai.manager_program():
        _start_runtime_install(tab);return
    winget=pai.winget_program()
    if not winget:
        _set_controls(tab,False)
        tab.v151_status.setText("⚠️ Ni Python Install Manager ni WinGet ne sont disponibles. Utilisez le téléchargement officiel une seule fois.")
        return
    tab.v151_mode="manager"
    tab.v151_status.setText("⬇️ Installation du gestionnaire Python officiel via WinGet… Vous n’avez rien à saisir.")
    tab.v151_process.start(winget,pai.python_manager_winget_args())

def _output(tab):
    data=bytes(tab.v151_process.readAllStandardOutput()).decode("utf-8",errors="replace")
    if data:tab.log.appendPlainText(data.rstrip())

def _finished(tab,code,status):
    _output(tab)
    if code!=0 or status!=QProcess.ExitStatus.NormalExit:
        _set_controls(tab,False)
        tab.v151_status.setText(f"❌ Installation automatique interrompue (code {code}). Consultez le journal.")
        tab.v151_mode="";return
    mode=tab.v151_mode;tab.v151_mode=""
    if mode=="manager":
        _start_runtime_install(tab)
    elif mode=="runtime":
        _after_install(tab)

def _error(tab,_):
    _output(tab);_set_controls(tab,False)
    tab.v151_status.setText("❌ Windows n’a pas pu lancer l’installation automatique : "+tab.v151_process.errorString())
    tab.v151_mode=""

def install_v151(window):
    if getattr(window,"_v151_python_auto",False):return
    tab=getattr(window,"creative_tools_tab",None)
    if tab is None:return
    root=tab.layout()
    tab.v151_auto_btn=QPushButton()
    tab.v151_auto_btn.setObjectName("Primary")
    tab.v151_auto_btn.setMinimumHeight(46)
    tab.v151_status=QLabel("IA Manager peut installer lui-même la version Python requise.")
    tab.v151_status.setWordWrap(True)
    root.insertWidget(2,tab.v151_auto_btn)
    root.insertWidget(3,tab.v151_status)
    tab.v151_process=QProcess(tab)
    tab.v151_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v151_process.readyReadStandardOutput.connect(lambda:_output(tab))
    tab.v151_process.finished.connect(lambda c,s:_finished(tab,c,s))
    tab.v151_process.errorOccurred.connect(lambda e:_error(tab,e))
    tab.v151_mode=""
    tab.v151_auto_btn.clicked.connect(lambda:_auto_install(tab))
    tab.choice.currentIndexChanged.connect(lambda:_update_button(tab))
    _update_button(tab)
    tab.pick_python.setText("Choisir manuellement…")
    tab.steps_hint.setText("Parcours conseillé : 1. Installer automatiquement Python · 2. Installer / reprendre le moteur · 3. Démarrer · 4. Ouvrir l’interface.")
    window._v151_python_auto=True
