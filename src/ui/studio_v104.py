"""Assistant d'installation de packs v104."""
from pathlib import Path
import shutil

from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QFileDialog, QMessageBox, QCheckBox
)

from src.backend import creative_tools, settings, studio_advisor
from src.backend import studio_pack_installer as packer


class PackInstallerPage(QWidget):
    open_local_tools = pyqtSignal()

    def __init__(self, hub, creative_tab):
        super().__init__()
        self.hub = hub
        self.creative_tab = creative_tab
        self.plan = {}
        self.running_key = None
        self.poll = QTimer(self)
        self.poll.setInterval(1200)
        self.poll.timeout.connect(self.check_progress)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Installe automatiquement, un par un, les moteurs déjà gérés par IA Manager. "
            "Chaque moteur garde son environnement séparé et son journal. Les outils non gérés "
            "restent listés pour installation manuelle."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        row = QHBoxLayout()
        self.pack = QComboBox()
        for p in studio_advisor.PACKS:
            self.pack.addItem(p["name"], p["id"])
        self.root_dir = QLineEdit(str(settings.get("creative_tools_root") or Path.home() / "IA Manager" / "Outils"))
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self.choose_root)
        row.addWidget(QLabel("Pack :"))
        row.addWidget(self.pack, 1)
        row.addWidget(QLabel("Dossier :"))
        row.addWidget(self.root_dir, 2)
        row.addWidget(browse)
        root.addLayout(row)

        py = QHBoxLayout()
        self.python39 = QLineEdit()
        self.python39.setPlaceholderText("Python 3.9 pour AudioCraft")
        self.python310 = QLineEdit()
        self.python310.setPlaceholderText("Python 3.10/3.11 pour image/3D")
        p39 = QPushButton("Python 3.9…")
        p310 = QPushButton("Python 3.10/11…")
        p39.clicked.connect(lambda: self.choose_python(self.python39))
        p310.clicked.connect(lambda: self.choose_python(self.python310))
        py.addWidget(self.python39, 1); py.addWidget(p39)
        py.addWidget(self.python310, 1); py.addWidget(p310)
        root.addLayout(py)

        opts = QHBoxLayout()
        self.hardware = QComboBox()
        self.hardware.addItem("NVIDIA / CUDA", "nvidia")
        self.hardware.addItem("CPU", "cpu")
        self.auto_continue = QCheckBox("Continuer automatiquement après chaque moteur")
        self.auto_continue.setChecked(True)
        opts.addWidget(QLabel("Profil :")); opts.addWidget(self.hardware)
        opts.addWidget(self.auto_continue); opts.addStretch(1)
        root.addLayout(opts)

        actions = QHBoxLayout()
        self.prepare_btn = QPushButton("Préparer le plan")
        self.start_btn = QPushButton("Installer / reprendre")
        self.next_btn = QPushButton("Étape suivante")
        self.stop_btn = QPushButton("Arrêter après l'étape en cours")
        self.open_btn = QPushButton("Ouvrir Outils locaux")
        self.prepare_btn.clicked.connect(self.prepare_plan)
        self.start_btn.clicked.connect(self.start_or_resume)
        self.next_btn.clicked.connect(self.install_current)
        self.stop_btn.clicked.connect(self.stop_after_current)
        self.open_btn.clicked.connect(self.open_local_tools.emit)
        for b in (self.prepare_btn, self.start_btn, self.next_btn, self.stop_btn, self.open_btn):
            actions.addWidget(b)
        root.addLayout(actions)

        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.queue = QListWidget()
        root.addWidget(self.queue, 1)

        self.details = QTextBrowser()
        self.details.setMaximumHeight(200)
        root.addWidget(self.details)

        self.pack.currentIndexChanged.connect(self.prepare_plan)
        self.queue.currentItemChanged.connect(self.show_selected)
        self.restore()
        if not self.plan:
            self.prepare_plan()

    def choose_root(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier des moteurs", self.root_dir.text())
        if path:
            self.root_dir.setText(path)

    def choose_python(self, target):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir python.exe", str(Path.home()))
        if path:
            target.setText(path)

    def save(self):
        settings.set("studio_v104_install_plan", self.plan)
        settings.set("studio_v104_python39", self.python39.text().strip())
        settings.set("studio_v104_python310", self.python310.text().strip())
        settings.set("creative_tools_root", self.root_dir.text().strip())

    def restore(self):
        self.python39.setText(str(settings.get("studio_v104_python39") or ""))
        self.python310.setText(str(settings.get("studio_v104_python310") or ""))
        saved = packer.sanitize(settings.get("studio_v104_install_plan"))
        if saved:
            self.plan = saved
            idx = self.pack.findData(saved["pack_id"])
            if idx >= 0:
                self.pack.blockSignals(True)
                self.pack.setCurrentIndex(idx)
                self.pack.blockSignals(False)
            self.refresh_queue()

    def prepare_plan(self):
        self.plan = packer.build_plan(self.pack.currentData())
        self.running_key = None
        self.poll.stop()
        self.save()
        self.refresh_queue()

    def refresh_queue(self):
        self.queue.clear()
        if not self.plan:
            return
        root = self.root_dir.text().strip()
        for i, key in enumerate(self.plan["managed"]):
            tool = creative_tools.TOOLS[key]
            manifest = creative_tools.read_manifest(root, key) if root else {}
            state = manifest.get("state", "non installé")
            pointer = "➡ " if i == self.plan["index"] else ""
            icon = "✅" if state == "installé — poids à préparer" else ("🟠" if state == "installation incomplète" else "⚪")
            item = QListWidgetItem(f"{pointer}{icon} {tool['name']}\n{state}")
            item.setData(0x0100, ("managed", key))
            self.queue.addItem(item)
        tool_map = {t["id"]: t for t in studio_advisor.catalog.TOOLS}
        for tid in self.plan["manual"]:
            tool = tool_map.get(tid, {"name": tid, "description": "Outil externe", "url": ""})
            item = QListWidgetItem(f"🔗 {tool['name']}\nInstallation manuelle · {tool.get('description','')}")
            item.setData(0x0100, ("manual", tool))
            self.queue.addItem(item)

        self.status.setText(
            f"Pack « {self.plan['pack_name']} » · {len(self.plan['managed'])} moteur(s) automatisable(s) · "
            f"{len(self.plan['manual'])} outil(s) manuel(s) · état : {self.plan['state']}."
            + (f" Dernière erreur : {self.plan['last_error']}" if self.plan.get("last_error") else "")
        )
        self.next_btn.setEnabled(bool(packer.current_key(self.plan)) and not self.running_key)
        self.start_btn.setEnabled(not self.running_key)
        self.stop_btn.setEnabled(bool(self.running_key))

    def show_selected(self, item, previous):
        if not item:
            return
        kind, value = item.data(0x0100)
        if kind == "managed":
            tool = creative_tools.TOOLS[value]
            self.details.setHtml(
                f"<h3>{tool['name']}</h3><p>{tool['note']}</p>"
                f"<p><b>Python :</b> {tool['python']}</p>"
                "<p>L'installation reprend dans le même dossier si une tentative précédente est incomplète.</p>"
            )
        else:
            tool = value
            url = tool.get("url", "")
            self.details.setHtml(
                f"<h3>{tool.get('name','')}</h3><p>{tool.get('description','')}</p>"
                "<p>Cet outil n'est pas automatisé par IA Manager v104 afin d'éviter une installation non maîtrisée.</p>"
                + (f"<p><a href='{url}'>Page officielle</a></p>" if url else "")
            )
            self.details.setOpenExternalLinks(True)

    def validate_common(self, key):
        root = self.root_dir.text().strip()
        if not root:
            raise ValueError("Choisissez le dossier des moteurs.")
        python = self.python39.text().strip() if packer.python_kind(key) == "py39" else self.python310.text().strip()
        if not python or not Path(python).is_file():
            expected = "Python 3.9" if key == "audiocraft" else "Python 3.10 ou 3.11"
            raise ValueError(f"Sélectionnez {expected} avant de continuer.")
        if not shutil.which("git"):
            raise ValueError("Git n'est pas détecté. Installez Git puis redémarrez IA Manager.")
        return root, python

    def start_or_resume(self):
        if self.running_key:
            return
        # Saute les moteurs déjà terminés, utile après redémarrage.
        while True:
            key = packer.current_key(self.plan)
            if not key:
                self.plan["state"] = "terminé"
                self.save(); self.refresh_queue()
                QMessageBox.information(self, "Installation du pack",
                                        "Tous les moteurs automatisables du pack sont terminés.\n"
                                        "Les poids des modèles et les outils manuels restent à préparer.")
                return
            manifest = creative_tools.read_manifest(self.root_dir.text().strip(), key)
            if manifest.get("state") == "installé — poids à préparer":
                self.plan = packer.advance(self.plan)
                continue
            break
        self.install_current()

    def install_current(self):
        if self.running_key:
            return
        key = packer.current_key(self.plan)
        if not key:
            self.start_or_resume()
            return
        try:
            root, python = self.validate_common(key)
            self.save()
            tab = self.creative_tab
            index = tab.choice.findData(key)
            if index < 0:
                raise ValueError("Ce moteur n'est plus disponible dans Outils locaux.")
            tab.choice.setCurrentIndex(index)
            tab.directory.setText(root)
            tab.python.setText(python)
            hw = tab.hardware.findData(self.hardware.currentData())
            if hw >= 0:
                tab.hardware.setCurrentIndex(hw)
            self.running_key = key
            self.plan["state"] = "installation"
            self.plan["last_error"] = ""
            self.save()
            self.refresh_queue()
            tab.install_tool()
            # install_tool peut échouer avant de devenir actif.
            if not tab.active:
                self.running_key = None
                message = tab.status.text() or "Impossible de démarrer l'installation."
                self.plan = packer.mark_error(self.plan, message)
                self.save(); self.refresh_queue()
                return
            self.poll.start()
        except Exception as exc:
            self.running_key = None
            self.plan = packer.mark_error(self.plan, str(exc))
            self.save(); self.refresh_queue()

    def check_progress(self):
        if not self.running_key:
            self.poll.stop()
            return
        # Tant que l'onglet Outils locaux a une action active, on attend.
        if self.creative_tab.active:
            self.status.setText(
                f"Installation de {creative_tools.TOOLS[self.running_key]['name']} en cours · "
                f"{self.creative_tab.status.text()}"
            )
            return
        self.poll.stop()
        key = self.running_key
        self.running_key = None
        manifest = creative_tools.read_manifest(self.root_dir.text().strip(), key)
        if manifest.get("state") == "installé — poids à préparer":
            self.plan = packer.advance(self.plan)
            self.save(); self.refresh_queue()
            if self.auto_continue.isChecked():
                QTimer.singleShot(800, self.start_or_resume)
        else:
            self.plan = packer.mark_error(
                self.plan,
                self.creative_tab.status.text() or "Installation incomplète. Consultez le journal Outils locaux."
            )
            self.save(); self.refresh_queue()

    def stop_after_current(self):
        self.auto_continue.setChecked(False)
        self.status.setText("La chaîne s'arrêtera après l'étape en cours. "
                            "Vous pourrez reprendre plus tard avec Installer / reprendre.")

    def shutdown(self):
        self.auto_continue.setChecked(False)
        self.poll.stop()
        self.save()
