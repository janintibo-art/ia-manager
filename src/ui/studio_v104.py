"""Assistant d'installation de packs v105."""
from pathlib import Path
import codecs
import shutil

from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QFileDialog, QMessageBox, QCheckBox
)

from src.backend import creative_tools, local_utilities, settings, studio_advisor
from src.backend import studio_pack_installer as packer


class PackInstallerPage(QWidget):
    open_local_tools = pyqtSignal()

    def __init__(self, hub, creative_tab):
        super().__init__()
        self.hub = hub
        self.creative_tab = creative_tab
        self.plan = {}
        self.running_key = None
        self.utility_process = None
        self.utility_steps = []
        self.utility_log = None
        self.utility_decoder = None
        self.poll = QTimer(self)
        self.poll.setInterval(1200)
        self.poll.timeout.connect(self.check_progress)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Installe automatiquement les moteurs gérés et les utilitaires v105, chacun dans "
            "son environnement séparé. Le plan peut être repris après un arrêt ou une coupure."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        row = QHBoxLayout()
        self.pack = QComboBox()
        for p in studio_advisor.PACKS: self.pack.addItem(p["name"], p["id"])
        self.root_dir = QLineEdit(str(settings.get("creative_tools_root") or Path.home() / "IA Manager" / "Outils"))
        browse = QPushButton("Parcourir…"); browse.clicked.connect(self.choose_root)
        row.addWidget(QLabel("Pack :")); row.addWidget(self.pack, 1)
        row.addWidget(QLabel("Dossier :")); row.addWidget(self.root_dir, 2); row.addWidget(browse)
        root.addLayout(row)

        py = QHBoxLayout()
        self.python39 = QLineEdit(); self.python39.setPlaceholderText("Python 3.9 pour AudioCraft")
        self.python310 = QLineEdit(); self.python310.setPlaceholderText("Python 3.10/3.11 pour le reste")
        p39 = QPushButton("Python 3.9…"); p39.clicked.connect(lambda: self.choose_python(self.python39))
        p310 = QPushButton("Python 3.10/11…"); p310.clicked.connect(lambda: self.choose_python(self.python310))
        py.addWidget(self.python39, 1); py.addWidget(p39); py.addWidget(self.python310, 1); py.addWidget(p310)
        root.addLayout(py)

        opts = QHBoxLayout()
        self.hardware = QComboBox()
        self.hardware.addItem("NVIDIA / CUDA", "nvidia"); self.hardware.addItem("CPU", "cpu")
        self.auto_continue = QCheckBox("Continuer automatiquement"); self.auto_continue.setChecked(True)
        opts.addWidget(QLabel("Profil :")); opts.addWidget(self.hardware); opts.addWidget(self.auto_continue); opts.addStretch(1)
        root.addLayout(opts)

        actions = QHBoxLayout()
        self.prepare_btn = QPushButton("Préparer le plan")
        self.start_btn = QPushButton("Installer / reprendre")
        self.next_btn = QPushButton("Étape suivante")
        self.stop_btn = QPushButton("Arrêter après l'étape en cours")
        self.open_btn = QPushButton("Ouvrir Outils locaux")
        self.prepare_btn.clicked.connect(self.prepare_plan); self.start_btn.clicked.connect(self.start_or_resume)
        self.next_btn.clicked.connect(self.install_current); self.stop_btn.clicked.connect(self.stop_after_current)
        self.open_btn.clicked.connect(self.open_local_tools.emit)
        for b in (self.prepare_btn, self.start_btn, self.next_btn, self.stop_btn, self.open_btn): actions.addWidget(b)
        root.addLayout(actions)

        self.status = QLabel(); self.status.setWordWrap(True); root.addWidget(self.status)
        self.queue = QListWidget(); root.addWidget(self.queue, 1)
        self.details = QTextBrowser(); self.details.setMaximumHeight(200); root.addWidget(self.details)

        self.pack.currentIndexChanged.connect(self.prepare_plan)
        self.queue.currentItemChanged.connect(self.show_selected)
        self.restore()
        if not self.plan: self.prepare_plan()

    def choose_root(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier des moteurs et utilitaires", self.root_dir.text())
        if path: self.root_dir.setText(path)

    def choose_python(self, target):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir python.exe", str(Path.home()))
        if path: target.setText(path)

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
                self.pack.blockSignals(True); self.pack.setCurrentIndex(idx); self.pack.blockSignals(False)
            self.refresh_queue()

    def prepare_plan(self):
        if self.running_key: return
        self.plan = packer.build_plan(self.pack.currentData())
        self.poll.stop(); self.save(); self.refresh_queue()

    def entry_state(self, entry):
        kind, key = packer.split_token(entry)
        root = self.root_dir.text().strip()
        if not root: return "non installé"
        if kind == "engine":
            return creative_tools.read_manifest(root, key).get("state", "non installé")
        return local_utilities.read_manifest(root, key).get("state", "non installé")

    def is_done(self, entry):
        state = self.entry_state(entry)
        return state in ("installé — poids à préparer", "installé — prêt")

    def refresh_queue(self):
        self.queue.clear()
        if not self.plan: return
        for i, entry in enumerate(self.plan["managed"]):
            kind, key = packer.split_token(entry)
            state = self.entry_state(entry)
            pointer = "➡ " if i == self.plan["index"] else ""
            icon = "✅" if self.is_done(entry) else ("🟠" if state == "installation incomplète" else "⚪")
            label = packer.display(entry)
            family = "moteur" if kind == "engine" else "utilitaire"
            item = QListWidgetItem(f"{pointer}{icon} {label}\n{family} · {state}")
            item.setData(0x0100, ("managed", entry)); self.queue.addItem(item)

        tool_map = {t["id"]: t for t in studio_advisor.catalog.TOOLS}
        for tid in self.plan["manual"]:
            tool = tool_map.get(tid, {"name": tid, "description": "Outil externe", "url": ""})
            item = QListWidgetItem(f"🔗 {tool['name']}\nInstallation manuelle · {tool.get('description','')}")
            item.setData(0x0100, ("manual", tool)); self.queue.addItem(item)

        self.status.setText(
            f"Pack « {self.plan['pack_name']} » · {len(self.plan['managed'])} étape(s) automatisable(s) · "
            f"{len(self.plan['manual'])} manuelle(s) · état : {self.plan['state']}."
            + (f" Dernière erreur : {self.plan['last_error']}" if self.plan.get("last_error") else "")
        )
        self.next_btn.setEnabled(bool(packer.current_key(self.plan)) and not self.running_key)
        self.start_btn.setEnabled(not self.running_key); self.stop_btn.setEnabled(bool(self.running_key))

    def show_selected(self, item, previous):
        if not item: return
        kind, value = item.data(0x0100)
        if kind == "manual":
            self.details.setHtml(
                f"<h3>{value.get('name','')}</h3><p>{value.get('description','')}</p>"
                "<p>Installation manuelle conservée pour éviter une recette non vérifiée.</p>"
            ); return
        etype, key = packer.split_token(value)
        if etype == "engine":
            tool = creative_tools.TOOLS[key]
            self.details.setHtml(f"<h3>{tool['name']}</h3><p>{tool['note']}</p><p><b>Python :</b> {tool['python']}</p>")
        else:
            tool = local_utilities.UTILITIES[key]
            self.details.setHtml(f"<h3>{tool['name']}</h3><p>{tool['note']}</p><p><b>Python :</b> {tool['python']}</p>")

    def validate_common(self, entry):
        root = self.root_dir.text().strip()
        if not root: raise ValueError("Choisissez le dossier d'installation.")
        python = self.python39.text().strip() if packer.python_kind(entry) == "py39" else self.python310.text().strip()
        if not python or not Path(python).is_file():
            expected = "Python 3.9" if packer.python_kind(entry) == "py39" else "Python 3.10 ou 3.11"
            raise ValueError(f"Sélectionnez {expected}.")
        return root, python

    def start_or_resume(self):
        if self.running_key: return
        while True:
            entry = packer.current_key(self.plan)
            if not entry:
                self.plan["state"] = "terminé"; self.save(); self.refresh_queue()
                QMessageBox.information(self, "Installation du pack",
                    "Toutes les étapes automatisables sont terminées.\nLes poids IA restent à préparer explicitement.")
                return
            if self.is_done(entry):
                self.plan = packer.advance(self.plan); continue
            break
        self.install_current()

    def install_current(self):
        if self.running_key: return
        entry = packer.current_key(self.plan)
        if not entry: self.start_or_resume(); return
        try:
            root, python = self.validate_common(entry)
            self.plan["state"] = "installation"; self.plan["last_error"] = ""
            self.running_key = entry; self.save(); self.refresh_queue()
            kind, key = packer.split_token(entry)
            if kind == "engine":
                self.install_engine(root, key, python)
            else:
                self.install_utility(root, key, python)
        except Exception as exc:
            self.running_key = None; self.plan = packer.mark_error(self.plan, str(exc))
            self.save(); self.refresh_queue()

    def install_engine(self, root, key, python):
        if not shutil.which("git"):
            raise ValueError("Git n'est pas détecté. Installez Git puis redémarrez IA Manager.")
        tab = self.creative_tab
        index = tab.choice.findData(key)
        if index < 0: raise ValueError("Moteur absent de l'onglet Outils locaux.")
        tab.choice.setCurrentIndex(index); tab.directory.setText(root); tab.python.setText(python)
        hw = tab.hardware.findData(self.hardware.currentData())
        if hw >= 0: tab.hardware.setCurrentIndex(hw)
        tab.install_tool()
        if not tab.active:
            raise ValueError(tab.status.text() or "Impossible de démarrer l'installation.")
        self.poll.start()

    def install_utility(self, root, key, python):
        git = shutil.which("git")
        if local_utilities.UTILITIES[key].get("needs_git") and not git:
            raise ValueError("Git est requis pour " + local_utilities.UTILITIES[key]["name"] + ".")
        local_utilities.prepare(root, key)
        self.utility_steps = local_utilities.install_plan(root, key, python, git)
        p = local_utilities.paths(root, key)
        self.utility_log = open(p["log"], "a", encoding="utf-8")
        self.utility_env = local_utilities.environment(root, key)
        self.next_utility_step()

    def next_utility_step(self):
        if not self.utility_steps:
            entry = self.running_key
            _, key = packer.split_token(entry)
            local_utilities.set_state(self.root_dir.text().strip(), key, True)
            if self.utility_log: self.utility_log.close(); self.utility_log = None
            self.running_key = None
            self.plan = packer.advance(self.plan); self.save(); self.refresh_queue()
            if self.auto_continue.isChecked(): QTimer.singleShot(500, self.start_or_resume)
            return
        step = self.utility_steps.pop(0)
        self.status.setText(step["label"])
        if self.utility_log:
            self.utility_log.write("\n> " + step["label"] + "\n"); self.utility_log.flush()
        p = QProcess(self); self.utility_process = p
        self.utility_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        env = QProcessEnvironment.systemEnvironment()
        for k, v in self.utility_env.items(): env.insert(k, v)
        p.setProcessEnvironment(env); p.setWorkingDirectory(step["cwd"])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self.read_utility_output(p))
        p.finished.connect(lambda code, status: self.utility_exited(p, code, status))
        p.start(step["program"], step["args"])

    def read_utility_output(self, p):
        if self.utility_process is p and self.utility_decoder:
            text = self.utility_decoder.decode(bytes(p.readAllStandardOutput()))
            if self.utility_log: self.utility_log.write(text); self.utility_log.flush()

    def utility_exited(self, p, code, status):
        if self.utility_process is not p: return
        self.read_utility_output(p)
        if self.utility_decoder and self.utility_log:
            self.utility_log.write(self.utility_decoder.decode(b"", final=True)); self.utility_log.flush()
        self.utility_process = None; p.deleteLater()
        if code != 0 or status != QProcess.ExitStatus.NormalExit:
            entry = self.running_key; _, key = packer.split_token(entry)
            local_utilities.set_state(self.root_dir.text().strip(), key, False)
            if self.utility_log: self.utility_log.close(); self.utility_log = None
            self.running_key = None
            self.plan = packer.mark_error(self.plan, f"Échec {local_utilities.UTILITIES[key]['name']} (code {code}).")
            self.save(); self.refresh_queue(); return
        self.next_utility_step()

    def check_progress(self):
        if not self.running_key: self.poll.stop(); return
        kind, key = packer.split_token(self.running_key)
        if kind != "engine": return
        if self.creative_tab.active:
            self.status.setText(f"Installation de {creative_tools.TOOLS[key]['name']} · {self.creative_tab.status.text()}")
            return
        self.poll.stop(); entry = self.running_key; self.running_key = None
        if self.is_done(entry):
            self.plan = packer.advance(self.plan); self.save(); self.refresh_queue()
            if self.auto_continue.isChecked(): QTimer.singleShot(500, self.start_or_resume)
        else:
            self.plan = packer.mark_error(self.plan, self.creative_tab.status.text() or "Installation incomplète.")
            self.save(); self.refresh_queue()

    def stop_after_current(self):
        self.auto_continue.setChecked(False)
        self.status.setText("Arrêt automatique désactivé : la chaîne s'arrêtera après l'étape actuelle.")

    def shutdown(self):
        self.auto_continue.setChecked(False); self.poll.stop(); self.save()
