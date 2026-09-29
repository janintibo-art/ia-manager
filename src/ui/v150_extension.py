"""v150 : corrective installation créative + mise en page."""
import json, os, subprocess
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)
from src.backend import python_detection as pd, settings

def _tool_python_requirement(key):
    return ({(3,9)},"Python 3.9") if key=="audiocraft" else ({(3,10),(3,11)},"Python 3.10 ou 3.11")

def _looks_like_python(path):
    p=Path(str(path or "").strip().strip('"'))
    if not p.is_file(): return False
    name=p.name.lower()
    if "installer" in name or "install-manager" in name or "manager installer" in name:return False
    return name in ("python.exe","python3.exe") if os.name=="nt" else name.startswith("python")

def _probe_python(program,prefix_args):
    cmd=[str(program)]+list(prefix_args)+["-c","import sys,json; print(json.dumps({'exe':sys.executable,'v':list(sys.version_info[:3])}))"]
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=4,creationflags=flags)
        if r.returncode:return None
        data=json.loads(r.stdout.strip().splitlines()[-1])
        exe=str(data.get("exe") or ""); version=tuple(data.get("v") or ())[:2]
        return (exe,version) if Path(exe).is_file() else None
    except Exception:
        return None

def _detect(tab,show=True):
    allowed,label=_tool_python_requirement(tab.choice.currentData())
    candidates=[(p,a) for p,a in pd.candidates(tab.python.text().strip()) if "installer" not in Path(str(p)).name.lower()]
    for program,args in candidates:
        result=_probe_python(program,args)
        if result and result[1] in allowed:
            tab.python.setText(result[0])
            if show: tab.status.setText(f"✅ {label} détecté automatiquement : {result[0]}")
            return result[0]
    tab.python.clear()
    if show:
        tab.status.setText(f"⚠️ Aucun {label} compatible détecté pour {tab.choice.currentText()}. Installez cette version puis relancez la détection.")
    return ""

def _patch_creative(window):
    tab=getattr(window,"creative_tools_tab",None)
    if tab is None or getattr(tab,"_v150_fixed",False):return
    root=tab.layout()
    detect=QPushButton("✨ Détecter automatiquement le bon Python"); detect.setObjectName("Primary")
    detect.clicked.connect(lambda:_detect(tab,True))
    warning=QLabel("Important : ne sélectionnez pas « Python Install Manager Installer.exe ». IA Manager a besoin du vrai fichier python.exe installé.")
    warning.setWordWrap(True); warning.setObjectName("Muted")
    root.insertWidget(2,detect); root.insertWidget(3,warning)
    def auto():
        if not _looks_like_python(tab.python.text()):_detect(tab,False)
    tab.choice.currentIndexChanged.connect(auto); auto()
    original=tab.install_tool
    try: tab.install.clicked.disconnect()
    except Exception: pass
    def safe_install():
        if not _looks_like_python(tab.python.text()):
            if not _detect(tab,True):return
        original()
    tab.install.clicked.connect(safe_install)
    tab.steps_hint.setText("Étapes : 1. Détecter le bon Python · 2. Installer / reprendre · 3. attendre « Installation terminée » · 4. Démarrer · 5. ouvrir l’interface.")
    tab.log.setMaximumHeight(280); tab.log.setMinimumHeight(150)
    for b in tab.findChildren(QPushButton):
        if b.text()=="Installer Python":
            b.setText("Télécharger Python (site officiel)")
    tab._v150_fixed=True

def _patch_image(window):
    tab=getattr(window,"image_studio_tab",None)
    if tab is None or getattr(tab,"_v150_fixed",False):return
    for b in tab.findChildren(QPushButton):
        if "Installer / démarrer les outils locaux" in b.text():
            b.pressed.connect(lambda:settings.set("creative_tools_requested","comfyui"))
            b.setText("1 · Installer / démarrer ComfyUI"); b.setObjectName("Primary"); break
    tab.status.setText("Étapes : 1. installer/démarrer ComfyUI · 2. installer un checkpoint · 3. revenir ici et cliquer Connecter / actualiser les modèles.")
    tab._v150_fixed=True

def _transfer(item,target):
    if item.widget() is not None:target.addWidget(item.widget())
    elif item.layout() is not None:target.addLayout(item.layout())
    elif item.spacerItem() is not None:target.addItem(item.spacerItem())

def _make_scrollable(tab,max_log=240):
    if tab is None or getattr(tab,"_v150_scrollable",False):return
    old=tab.layout()
    if old is None:return
    if any(isinstance(old.itemAt(i).widget(),QScrollArea) for i in range(old.count())):
        tab._v150_scrollable=True;return
    host=QWidget(); lay=QVBoxLayout(host); lay.setContentsMargins(8,8,8,8);lay.setSpacing(10)
    items=[]
    while old.count():items.append(old.takeAt(0))
    for item in items:_transfer(item,lay)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);scroll.setWidget(host)
    old.setContentsMargins(0,0,0,0);old.addWidget(scroll)
    for log in tab.findChildren(QPlainTextEdit):
        if log.isReadOnly():log.setMaximumHeight(max_log);log.setMinimumHeight(140)
    tab._v150_scrollable=True

def _fix_cards(window):
    tab=getattr(window,"surgery_dashboard_tab",None)
    if tab is None:return
    cards=list(getattr(tab,"cards",{}).values())
    if not cards:return
    for card in cards:
        card.setMinimumWidth(0);card.setMaximumWidth(16777215)
        card.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        for lab in card.findChildren(QLabel):
            lab.setMinimumWidth(0);lab.setWordWrap(True)
            lab.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
    parent=cards[0].parentWidget()
    if parent and parent.layout():
        outer=parent.layout();grid=None
        for i in range(outer.count()):
            sub=outer.itemAt(i).layout()
            if isinstance(sub,QGridLayout):grid=sub;break
        if grid:
            for c in cards:grid.removeWidget(c)
            for r,c in enumerate(cards):grid.addWidget(c,r,0)
            grid.setColumnStretch(0,1)

def _patch_media(window):
    tab=getattr(window,"media_studio_tab",None)
    if tab is None or getattr(tab,"_v150_fixed",False):return
    tab.quick_steps.setText("Choisissez un modèle : IA Manager ouvrira Outils locaux sur le moteur correspondant. Utilisez ensuite Détecter Python → Installer → Démarrer.")
    tab._v150_fixed=True

def install_v150(window):
    if getattr(window,"_v150_corrective",False):return
    _patch_creative(window);_patch_image(window);_patch_media(window)
    _make_scrollable(getattr(window,"obliteratus_tab",None),240)
    _make_scrollable(getattr(window,"mergekit_tab",None),240)
    _fix_cards(window)
    shell=getattr(window,"studio_shell",None)
    if shell is not None and hasattr(shell,"refresh_navigation"):shell.refresh_navigation()
    window._v150_corrective=True
