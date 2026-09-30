"""Page Source Pinokio : installation guidée de pterm + catalogue."""
import html
import platform as py_platform
from PyQt6.QtCore import QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QComboBox,
    QListWidget,QListWidgetItem,QTextBrowser,QMessageBox,QSplitter)
from src.backend import pinokio_integration as pinokio

class PinokioPage(QWidget):
    def __init__(self):
        super().__init__(); self.results=[]; self.current=None; self.process=None; self.process_kind=""
        root=QVBoxLayout(self)
        intro=QLabel("Recherchez les applications et modèles Pinokio. Si pterm manque, IA Manager peut maintenant l'installer automatiquement.")
        intro.setWordWrap(True); root.addWidget(intro)
        row=QHBoxLayout(); self.query=QLineEdit(); self.query.setPlaceholderText("image, video, TTS, ComfyUI, face, music, 3D…"); self.query.returnPressed.connect(self.search)
        self.sort=QComboBox(); [self.sort.addItem(a,b) for a,b in (("Pertinence","relevance"),("Populaires","popular"),("Tendances","trending"),("Récents","latest"),("Nom","name"))]
        self.gpu=QComboBox(); self.gpu.addItem("Tous GPU",""); self.gpu.addItem("NVIDIA","nvidia"); self.gpu.addItem("AMD","amd"); self.gpu.addItem("Apple","apple")
        b=QPushButton("Rechercher dans Pinokio"); b.clicked.connect(self.search)
        row.addWidget(self.query,1); row.addWidget(self.sort); row.addWidget(self.gpu); row.addWidget(b); root.addLayout(row)
        sr=QHBoxLayout(); self.status=QLabel(); self.status.setWordWrap(True)
        detect=QPushButton("Détecter Pinokio"); detect.clicked.connect(self.detect)
        self.install_pterm_btn=QPushButton("⬇ Installer pterm automatiquement"); self.install_pterm_btn.setObjectName("Primary"); self.install_pterm_btn.clicked.connect(self.install_pterm)
        pinokio_site=QPushButton("🌐 Installer / ouvrir Pinokio"); pinokio_site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://pinokio.computer/")))
        node_site=QPushButton("Installer Node.js"); node_site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://nodejs.org/en/download")))
        sr.addWidget(self.status,1); sr.addWidget(detect); sr.addWidget(self.install_pterm_btn); sr.addWidget(pinokio_site); sr.addWidget(node_site); root.addLayout(sr)
        split=QSplitter(); self.list=QListWidget(); self.list.currentItemChanged.connect(self.select); self.details=QTextBrowser(); self.details.setOpenExternalLinks(True); split.addWidget(self.list); split.addWidget(self.details); split.setSizes([360,700]); root.addWidget(split,1)
        ar=QHBoxLayout(); self.download_btn=QPushButton("⬇ Télécharger dans Pinokio"); self.run_btn=QPushButton("▶ Installer / lancer dans Pinokio"); self.open_btn=QPushButton("Ouvrir la fiche / dépôt")
        self.download_btn.clicked.connect(self.download); self.run_btn.clicked.connect(self.run_app); self.open_btn.clicked.connect(self.open_page)
        ar.addWidget(self.download_btn); ar.addWidget(self.run_btn); ar.addWidget(self.open_btn); ar.addStretch(1); root.addLayout(ar)
        self.log=QLabel(); self.log.setWordWrap(True); root.addWidget(self.log); self.detect(); self.update_buttons()

    def platform_key(self):
        n=py_platform.system().lower(); return "windows" if n.startswith("win") else ("mac" if n=="darwin" else "linux")
    def detect(self):
        s=pinokio.local_status(); parts=[]
        parts.append("✅ pterm détecté" if s["pterm"] else "⚪ pterm absent")
        parts.append("✅ npm détecté" if s.get("npm") else "⚪ npm absent")
        if s["running"]:
            v=s.get("version") or {}; label=v.get("pinokio") or v.get("pinokiod") or ""; parts.append("✅ Pinokio actif"+(f" ({label})" if label else ""))
        else: parts.append("⚪ Pinokio non détecté sur 127.0.0.1:42000")
        self.status.setText(" · ".join(parts)); self.install_pterm_btn.setEnabled(not bool(s["pterm"]) and bool(s.get("npm")) and self.process is None); self.update_buttons()
    def install_pterm(self):
        try: cmd=pinokio.pterm_install_command()
        except Exception as exc:
            QMessageBox.warning(self,"Pinokio",str(exc)+"\n\nLe bouton Installer Node.js ouvre la page officielle."); return
        reply=QMessageBox.question(self,"Installer pterm","IA Manager va exécuter la commande officielle npm install -g pterm. Continuer ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply==QMessageBox.StandardButton.Yes: self.execute(cmd,"Installation de pterm","pterm")
    def search(self):
        self.status.setText("⏳ Recherche dans le registre Pinokio…")
        try: self.results=pinokio.search_registry(self.query.text(),30,self.sort.currentData(),self.platform_key(),self.gpu.currentData())
        except Exception as exc: self.results=[]; self.list.clear(); self.status.setText("❌ Recherche Pinokio impossible : "+str(exc)); return
        self.list.clear()
        for i,item in enumerate(self.results):
            tags=", ".join(item["tags"][:4]); line=f"{item['name']}\n{item['author']}"+(" · "+tags if tags else ""); q=QListWidgetItem(line); q.setData(0x0100,i); q.setToolTip(item["description"]); self.list.addItem(q)
        self.status.setText(f"✅ {len(self.results)} résultat(s) Pinokio.");
        if self.list.count(): self.list.setCurrentRow(0)
    def select(self,current,previous):
        self.current=None
        if not current: self.details.clear(); self.update_buttons(); return
        i=current.data(0x0100)
        if not isinstance(i,int) or not (0<=i<len(self.results)): return
        self.current=self.results[i]; item=self.current; tags=", ".join(item["tags"]) or "non indiqués"
        self.details.setHtml(f"<h2>{html.escape(item['name'])}</h2><p>{html.escape(item['description'] or 'Pas de description.')}</p><p><b>Auteur :</b> {html.escape(item['author'] or 'non indiqué')}</p><p><b>Tags :</b> {html.escape(tags)}</p><p><b>Identifiant :</b> {html.escape(item['id'])}</p><p>1. Télécharger clone l'application dans Pinokio. 2. Installer / lancer exécute ensuite le lanceur Pinokio avec confirmation.</p>"); self.update_buttons()
    def update_buttons(self):
        has=bool(self.current); pterm=bool(pinokio.pterm_path()); uri=bool((self.current or {}).get("install_uri")); self.download_btn.setEnabled(has and pterm and uri and self.process is None); self.run_btn.setEnabled(has and pterm and uri and self.process is None); self.open_btn.setEnabled(has and bool((self.current or {}).get("url") or (self.current or {}).get("repo")))
    def open_page(self):
        if self.current:
            u=self.current.get("url") or self.current.get("repo");
            if u: QDesktopServices.openUrl(QUrl(u))
    def execute(self,command,label,kind="app"):
        if self.process is not None: QMessageBox.information(self,"Pinokio","Une action Pinokio est déjà en cours."); return
        p=QProcess(self); self.process=p; self.process_kind=kind; p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels); p.finished.connect(lambda code,status:self.finished_process(p,code,label)); p.errorOccurred.connect(lambda _err:self.log.setText("❌ "+p.errorString())); self.log.setText("⏳ "+label+"…"); self.update_buttons(); p.start(command["program"],command["args"])
    def finished_process(self,process,code,label):
        if self.process is not process: return
        out=bytes(process.readAllStandardOutput()).decode("utf-8",errors="replace").strip(); kind=self.process_kind; self.process=None; self.process_kind=""; process.deleteLater(); self.log.setText(("✅ " if code==0 else "❌ ")+label+f" · code {code}"+(f"\n{out[-1200:]}" if out else "")); self.detect()
        if code==0 and kind=="pterm": QMessageBox.information(self,"Pinokio","pterm est installé. Vous pouvez maintenant sélectionner une application puis cliquer Télécharger dans Pinokio.")
    def download(self):
        if not self.current: return
        try: cmd=pinokio.download_command(self.current)
        except Exception as exc: QMessageBox.warning(self,"Pinokio",str(exc)); return
        if QMessageBox.question(self,"Télécharger dans Pinokio",f"Télécharger « {self.current['name']} » dans Pinokio ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes: self.execute(cmd,"Téléchargement Pinokio")
    def run_app(self):
        if not self.current: return
        try: cmd=pinokio.run_command(self.current)
        except Exception as exc: QMessageBox.warning(self,"Pinokio",str(exc)); return
        if QMessageBox.warning(self,"Exécuter une application Pinokio",f"« {self.current['name']} » peut installer des dépendances sur ce PC. Continuer ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Yes: self.execute(cmd,"Installation / lancement Pinokio")
