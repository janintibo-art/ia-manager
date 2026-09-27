"""Onglet Connexions - Claude, ChatGPT, serveurs compatibles, ajout manuel de modèles"""

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from src.backend import providers as pv
from src.backend import settings, diagnostics, settings_backup
from src.backend.ai_manager import AIManager
from src.ui import style
from src.ui.workers import DownloadWorker, FunctionWorker


def card(title: str, subtitle: str = ""):
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(8)
    t = QLabel(title)
    t.setObjectName("CardTitle")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("Muted")
        s.setWordWrap(True)
        s.setTextFormat(Qt.TextFormat.RichText)
        s.setOpenExternalLinks(True)
        lay.addWidget(s)
    return frame, lay


class AccountBox(QWidget):
    """Clé API d'un service (Claude ou ChatGPT)"""

    changed = pyqtSignal()

    def __init__(self, provider_id: str):
        super().__init__()
        self.pid = provider_id
        self.worker: Optional[FunctionWorker] = None
        p = pv.get_provider(provider_id)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)

        name = QLabel(f"<b>{p['name']}</b>")
        lay.addWidget(name)
        row = QHBoxLayout()
        self.key_edit = QLineEdit(p.get("api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Collez ici votre clé API")
        row.addWidget(self.key_edit, 1)
        show = QPushButton("👁")
        show.setToolTip("Afficher / masquer la clé")
        show.setCheckable(True)
        show.toggled.connect(lambda on: self.key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        row.addWidget(show)
        save = QPushButton("💾 Enregistrer et tester")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_and_test)
        row.addWidget(save)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        get_key = QPushButton("🔑 Obtenir une clé")
        get_key.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(p["key_url"])))
        row2.addWidget(get_key)
        site = QPushButton(f"🌐 Ouvrir {p['web_url'].replace('https://', '')}")
        site.setToolTip("Ouvre le site dans votre navigateur (votre abonnement y fonctionne)")
        site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(p["web_url"])))
        row2.addWidget(site)
        forget = QPushButton("Oublier la clé")
        forget.setObjectName("Danger")
        forget.clicked.connect(self.forget)
        row2.addWidget(forget)
        row2.addStretch()
        lay.addLayout(row2)

        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.update_status()

    def update_status(self, extra: str = ""):
        p = pv.get_provider(self.pid)
        if p.get("api_key"):
            n = len(p.get("models", []))
            txt = f"Clé enregistrée ({pv.mask_key(p['api_key'])}) · {n} modèle(s) disponible(s) dans le Chat."
        else:
            txt = "Non connecté."
        self.status.setText(f"{extra}\n{txt}".strip())

    def save_and_test(self):
        p = pv.get_provider(self.pid)
        p["api_key"] = self.key_edit.text().strip()
        if not p["api_key"]:
            self.status.setText("Collez d'abord une clé API.")
            return
        pv.save_provider(p)
        self.status.setText("⏳ Test de la connexion…")
        self.worker = FunctionWorker(pv.fetch_models, p)
        self.worker.done.connect(self.on_tested)
        self.worker.start()

    def on_tested(self, ok: bool, result):
        p = pv.get_provider(self.pid)
        if ok:
            p["models"] = list(result)
            pv.save_provider(p)
            self.update_status("✅ Connexion réussie.")
        else:
            self.update_status(f"❌ Échec : {result}")
        self.changed.emit()

    def forget(self):
        pv.delete_provider(self.pid)
        self.key_edit.clear()
        self.update_status("Clé supprimée.")
        self.changed.emit()


class ConnectionsTab(QWidget):
    """Comptes en ligne, serveurs compatibles, ajout manuel de modèles"""

    providers_changed = pyqtSignal()
    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.current_custom: Optional[str] = None
        self.worker: Optional[FunctionWorker] = None
        self.dl_worker: Optional[DownloadWorker] = None
        self.init_ui()
        self.refresh_custom_list()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(14)

        title = QLabel("Connexions et IA supplémentaires")
        title.setObjectName("Title")
        root.addWidget(title)

        # --- Comptes
        box, lay = card(
            "☁️  Claude et ChatGPT",
            "Pour utiliser Claude ou GPT dans le Chat, il faut une <b>clé API</b>. Anthropic et OpenAI "
            "ne permettent pas de se connecter avec l'identifiant et le mot de passe d'un compte, ni "
            "d'utiliser un abonnement Claude Pro / ChatGPT Plus depuis une autre application. "
            "La clé API est <b>facturée à l'usage, séparément de l'abonnement</b>. "
            "Vos clés restent sur ce PC (dossier .ia_manager de votre profil). "
            "Pour utiliser votre abonnement, ouvrez simplement le site dans le navigateur.")
        self.account_boxes: List[AccountBox] = []
        for pid in ("claude", "chatgpt"):
            ab = AccountBox(pid)
            ab.changed.connect(self.providers_changed.emit)
            lay.addWidget(ab)
            self.account_boxes.append(ab)
        root.addWidget(box)

        # --- Serveurs compatibles
        box, lay = card(
            "🔌  Autres IA (LM Studio, llama.cpp, Jan, OpenRouter, Mistral, Groq…)",
            "Tout logiciel ou service « compatible OpenAI » peut être ajouté : sur ce PC (LM Studio, "
            "llama.cpp, Jan, GPT4All) ou en ligne (OpenRouter, Mistral, Groq…). Ses modèles apparaissent "
            "ensuite dans le Chat.")
        row = QHBoxLayout()
        self.custom_list = QListWidget()
        self.custom_list.setMaximumHeight(200)
        self.custom_list.currentItemChanged.connect(self.on_custom_selected)
        row.addWidget(self.custom_list, 2)

        form_w = QWidget()
        form = QFormLayout(form_w)
        form.setVerticalSpacing(8)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Choisir un type…", "")
        for label in pv.PRESETS:
            self.preset_combo.addItem(label, label)
        self.preset_combo.activated.connect(self.apply_preset)
        form.addRow("Type :", self.preset_combo)
        self.c_name = QLineEdit()
        form.addRow("Nom :", self.c_name)
        self.c_url = QLineEdit()
        self.c_url.setPlaceholderText("http://localhost:1234/v1")
        form.addRow("Adresse :", self.c_url)
        self.c_key = QLineEdit()
        self.c_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.c_key.setPlaceholderText("Clé API (vide pour les logiciels locaux)")
        form.addRow("Clé API :", self.c_key)
        self.c_models = QLineEdit()
        self.c_models.setPlaceholderText("modele-1, modele-2 (ou « Détecter »)")
        form.addRow("Modèles :", self.c_models)
        row.addWidget(form_w, 3)
        lay.addLayout(row)

        btns = QHBoxLayout()
        new_btn = QPushButton("➕ Nouveau")
        new_btn.clicked.connect(self.new_custom)
        btns.addWidget(new_btn)
        detect = QPushButton("🔍 Détecter les modèles")
        detect.clicked.connect(self.detect_models)
        btns.addWidget(detect)
        save = QPushButton("💾 Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_custom)
        btns.addWidget(save)
        delete = QPushButton("🗑 Supprimer")
        delete.setObjectName("Danger")
        delete.clicked.connect(self.delete_custom)
        btns.addWidget(delete)
        btns.addStretch()
        lay.addLayout(btns)
        self.custom_status = QLabel()
        self.custom_status.setObjectName("Muted")
        self.custom_status.setWordWrap(True)
        lay.addWidget(self.custom_status)
        root.addWidget(box)

        # --- Ajout manuel dans Ollama
        box, lay = card(
            "➕  Ajouter un modèle absent du catalogue",
            "Des milliers de modèles au format <b>GGUF</b> existent sur Hugging Face. "
            "<a href='https://huggingface.co/models?library=gguf&sort=trending'>Parcourir les modèles GGUF</a>")
        hf_row = QHBoxLayout()
        hf_row.addWidget(QLabel("Hugging Face :"))
        self.hf_repo = QLineEdit()
        self.hf_repo.setPlaceholderText("utilisateur/depot-GGUF  (ex. bartowski/Llama-3.2-3B-Instruct-GGUF)")
        hf_row.addWidget(self.hf_repo, 3)
        self.hf_quant = QLineEdit()
        self.hf_quant.setPlaceholderText("Q4_K_M (option)")
        self.hf_quant.setMaximumWidth(180)
        hf_row.addWidget(self.hf_quant)
        self.hf_btn = QPushButton("⬇ Télécharger")
        self.hf_btn.setObjectName("Primary")
        self.hf_btn.clicked.connect(self.download_hf)
        hf_row.addWidget(self.hf_btn)
        lay.addLayout(hf_row)

        gg_row = QHBoxLayout()
        gg_row.addWidget(QLabel("Fichier .gguf :"))
        self.gguf_path = QLineEdit()
        self.gguf_path.setPlaceholderText("Fichier déjà téléchargé sur ce PC")
        gg_row.addWidget(self.gguf_path, 3)
        browse = QPushButton("Parcourir")
        browse.clicked.connect(self.browse_gguf)
        gg_row.addWidget(browse)
        self.gguf_name = QLineEdit()
        self.gguf_name.setPlaceholderText("nom-du-modele")
        self.gguf_name.setMaximumWidth(200)
        gg_row.addWidget(self.gguf_name)
        self.gguf_btn = QPushButton("📥 Importer")
        self.gguf_btn.setObjectName("Primary")
        self.gguf_btn.clicked.connect(self.import_gguf)
        gg_row.addWidget(self.gguf_btn)
        lay.addLayout(gg_row)

        self.add_progress = QProgressBar()
        self.add_progress.setRange(0, 0)
        self.add_progress.setTextVisible(False)
        self.add_progress.setVisible(False)
        lay.addWidget(self.add_progress)
        self.add_status = QLabel()
        self.add_status.setObjectName("Muted")
        self.add_status.setWordWrap(True)
        lay.addWidget(self.add_status)
        root.addWidget(box)

        # --- Recherche internet
        box, lay = card(
            "🌐  Recherche internet",
            "L'interrupteur « 🌐 Internet » du Chat fonctionne sans rien régler ici (DuckDuckGo, "
            "avec Wikipédia en secours). Une clé <b>Brave Search</b> (gratuite) ou une adresse "
            "<b>SearXNG</b> donnent des résultats plus fiables, en priorité si renseignées.")
        web_form = QFormLayout()
        web_form.setVerticalSpacing(8)
        self.offline = QCheckBox("Mode hors ligne : bloquer web et fournisseurs distants")
        self.offline.setChecked(bool(settings.get("offline_mode")))
        self.offline.toggled.connect(lambda value: settings.set("offline_mode", value))
        web_form.addRow(self.offline)
        self.brave_key = QLineEdit(settings.get("brave_key") or "")
        self.brave_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.brave_key.setPlaceholderText("Collez ici votre clé API Brave Search (facultatif)")
        web_form.addRow("Clé Brave Search :", self.brave_key)
        self.searxng_url = QLineEdit(settings.get("searxng_url") or "")
        self.searxng_url.setPlaceholderText("http://mon-serveur:8080 (facultatif)")
        web_form.addRow("Adresse SearXNG :", self.searxng_url)
        self.github_token = QLineEdit(settings.get("github_token") or "")
        self.github_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.github_token.setPlaceholderText("Jeton GitHub facultatif (augmente la limite de recherche)")
        web_form.addRow("Jeton GitHub :", self.github_token)
        self.civitai_token = QLineEdit(settings.get("civitai_token") or "")
        self.civitai_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.civitai_token.setPlaceholderText("Jeton Civitai facultatif pour les fichiers privés")
        web_form.addRow("Jeton Civitai :", self.civitai_token)
        self.modelscope_token = QLineEdit(settings.get("modelscope_token") or "")
        self.modelscope_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.modelscope_token.setPlaceholderText("Jeton ModelScope facultatif pour dépôts privés")
        web_form.addRow("Jeton ModelScope :", self.modelscope_token)
        lay.addLayout(web_form)
        web_row = QHBoxLayout()
        brave_key_btn = QPushButton("🔑 Obtenir une clé Brave")
        brave_key_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://brave.com/search/api/")))
        web_row.addWidget(brave_key_btn)
        web_save = QPushButton("💾 Enregistrer")
        web_save.setObjectName("Primary")
        web_save.clicked.connect(self.save_web_settings)
        web_row.addWidget(web_save)
        diag = QPushButton("📋 Exporter un diagnostic sans secrets")
        diag.clicked.connect(self.export_diagnostic)
        web_row.addWidget(diag)
        backup = QPushButton("💾 Sauvegarder la configuration")
        backup.clicked.connect(self.export_backup)
        web_row.addWidget(backup)
        restore = QPushButton("📂 Restaurer")
        restore.clicked.connect(self.import_backup)
        web_row.addWidget(restore)
        web_row.addStretch()
        lay.addLayout(web_row)
        self.web_status = QLabel()
        self.web_status.setObjectName("Muted")
        self.web_status.setWordWrap(True)
        lay.addWidget(self.web_status)
        root.addWidget(box)

        root.addStretch()

    def export_diagnostic(self):
        try:
            path = diagnostics.export()
            self.web_status.setText(f"✅ Diagnostic créé sans clés API ni conversations : {path}")
        except Exception as error:
            self.web_status.setText(f"❌ Diagnostic impossible : {error}")

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la configuration", "ia_manager_config.json",
                                              "Configuration JSON (*.json)")
        if not path:
            return
        try:
            settings_backup.export_file(path)
            self.web_status.setText("✅ Configuration sauvegardée sans clés API. Les clés restent sur cet appareil.")
        except Exception as error:
            self.web_status.setText(f"❌ Sauvegarde impossible : {error}")

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restaurer une configuration", "",
                                              "Configuration JSON (*.json)")
        if not path:
            return
        reply = QMessageBox.question(self, "Restaurer la configuration",
                                     "Les réglages actuels seront remplacés. Continuer ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            count = settings_backup.import_file(path)
            self.offline.setChecked(bool(settings.get("offline_mode")))
            self.brave_key.clear()
            self.searxng_url.setText(settings.get("searxng_url") or "")
            self.refresh_custom_list()
            self.web_status.setText(f"✅ {count} réglages restaurés. Les clés API existantes ont été conservées.")
            self.providers_changed.emit()
        except Exception as error:
            self.web_status.setText(f"❌ Restauration impossible : {error}")

    def save_web_settings(self):
        settings.set("brave_key", self.brave_key.text().strip())
        settings.set("searxng_url", self.searxng_url.text().strip())
        settings.set("github_token", self.github_token.text().strip())
        settings.set("civitai_token", self.civitai_token.text().strip())
        settings.set("modelscope_token", self.modelscope_token.text().strip())
        self.web_status.setText("✅ Enregistré.")

    # ------------------------------------------------------ serveurs compatibles
    def custom_providers(self) -> List[Dict]:
        return [p for p in pv.get_providers() if p["kind"] == "openai_compat"]

    def refresh_custom_list(self, select: Optional[str] = None):
        self.custom_list.blockSignals(True)
        self.custom_list.clear()
        for p in self.custom_providers():
            item = QListWidgetItem(f"{p['name']}\n      {p['base_url']} · {len(p.get('models', []))} modèle(s)")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.custom_list.addItem(item)
        self.custom_list.blockSignals(False)
        if select:
            for i in range(self.custom_list.count()):
                if self.custom_list.item(i).data(Qt.ItemDataRole.UserRole) == select:
                    self.custom_list.setCurrentRow(i)

    def on_custom_selected(self, current, _prev):
        if current is None:
            return
        p = pv.get_provider(current.data(Qt.ItemDataRole.UserRole))
        if not p:
            return
        self.current_custom = p["id"]
        self.c_name.setText(p["name"])
        self.c_url.setText(p["base_url"])
        self.c_key.setText(p.get("api_key", ""))
        self.c_models.setText(", ".join(p.get("models", [])))
        self.custom_status.setText("")

    def new_custom(self):
        self.current_custom = None
        self.custom_list.clearSelection()
        for w in (self.c_name, self.c_url, self.c_key, self.c_models):
            w.clear()
        self.preset_combo.setCurrentIndex(0)
        self.custom_status.setText("Choisissez un type, puis « Détecter les modèles » et « Enregistrer ».")

    def apply_preset(self, _index: int):
        label = self.preset_combo.currentData()
        if not label:
            return
        _pid, url, needs_key = pv.PRESETS[label]
        self.c_name.setText(label.split(" (")[0])
        self.c_url.setText(url)
        self.custom_status.setText(
            "Collez votre clé API, puis « Détecter les modèles »." if needs_key
            else "Lancez le logiciel et son serveur local, puis « Détecter les modèles ».")

    def form_provider(self) -> Dict:
        label = self.preset_combo.currentData()
        base_id = pv.PRESETS[label][0] if label else "perso"
        pid = self.current_custom or pv.unique_id(base_id)
        models = [m.strip() for m in self.c_models.text().split(",") if m.strip()]
        return {"id": pid, "name": self.c_name.text().strip() or pid, "kind": "openai_compat",
                "base_url": self.c_url.text().strip(), "api_key": self.c_key.text().strip(),
                "models": models, "enabled": True}

    def detect_models(self):
        p = self.form_provider()
        if not p["base_url"]:
            self.custom_status.setText("Indiquez d'abord l'adresse du serveur.")
            return
        self.custom_status.setText("⏳ Recherche des modèles…")
        self.worker = FunctionWorker(pv.fetch_models, p)
        self.worker.done.connect(self.on_detected)
        self.worker.start()

    def on_detected(self, ok: bool, result):
        if ok:
            models = list(result)
            if len(models) > 40:
                self.custom_status.setText(f"✅ {len(models)} modèles trouvés : les 40 premiers ont été "
                                           "ajoutés. Retirez ceux qui ne vous servent pas.")
                models = models[:40]
            else:
                self.custom_status.setText(f"✅ {len(models)} modèle(s) trouvé(s). Pensez à enregistrer.")
            self.c_models.setText(", ".join(models))
        else:
            self.custom_status.setText(f"❌ {result}")

    def save_custom(self):
        p = self.form_provider()
        if not p["base_url"]:
            self.custom_status.setText("L'adresse est obligatoire.")
            return
        pv.save_provider(p)
        self.current_custom = p["id"]
        self.refresh_custom_list(select=p["id"])
        self.custom_status.setText(f"✅ Enregistré. {len(p['models'])} modèle(s) disponible(s) dans le Chat.")
        self.providers_changed.emit()

    def delete_custom(self):
        if not self.current_custom:
            return
        reply = QMessageBox.question(self, "Supprimer", "Supprimer cette connexion ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            pv.delete_provider(self.current_custom)
            self.new_custom()
            self.refresh_custom_list()
            self.providers_changed.emit()

    # ------------------------------------------------------ ajout manuel Ollama
    def set_busy(self, busy: bool, text: str = ""):
        self.add_progress.setVisible(busy)
        self.hf_btn.setEnabled(not busy)
        self.gguf_btn.setEnabled(not busy)
        if text:
            self.add_status.setText(text)

    def download_hf(self):
        repo = self.hf_repo.text().strip()
        if repo.lower().startswith("ollama run "):
            # Le bouton Copier de Hugging Face fournit une commande complète.
            # Accepter ce collage sans transmettre « ollama run » à l'API Ollama.
            parts = repo.split()
            if len(parts) != 3:
                self.add_status.setText("Collez une seule commande : ollama run hf.co/utilisateur/depot:Q4_K_M")
                return
            repo = parts[2]
        quant = self.hf_quant.text().strip()
        if ":" in repo.rsplit("/", 1)[-1]:
            repo, pasted_quant = repo.rsplit(":", 1)
            quant = pasted_quant
        if any(c.isspace() for c in repo) or "/" not in repo or not repo.strip("/"):
            self.add_status.setText("Indiquez utilisateur/depot ou collez la commande Ollama de Hugging Face.")
            return
        if not quant or (quant.replace("_", "").isalnum() and len(quant) < 32):
            self.hf_repo.setText(repo)
            self.hf_quant.setText(quant)
        else:
            self.add_status.setText("Quantification invalide : utilisez par exemple Q4_K_M ou Q6_K.")
            return
        if not self.ai_manager.is_ollama_running():
            self.add_status.setText("❌ Ollama doit être lancé.")
            return
        name = pv.hf_model_name(repo, quant)
        self.set_busy(True, f"⏳ Téléchargement de {name}… (plusieurs minutes possible)")
        self.dl_worker = DownloadWorker(self.ai_manager, name)
        self.dl_worker.finished_ok.connect(lambda ok, err: self.on_added(ok, err, name))
        self.dl_worker.start()

    def browse_gguf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fichier GGUF", "", "Modèles GGUF (*.gguf)")
        if path:
            self.gguf_path.setText(path)
            if not self.gguf_name.text().strip():
                from pathlib import Path
                import re
                stem = re.sub(r"[^a-z0-9._-]+", "-", Path(path).stem.lower()).strip("-")
                self.gguf_name.setText(stem[:60] or "mon-modele")

    def import_gguf(self):
        path = self.gguf_path.text().strip()
        name = self.gguf_name.text().strip().lower()
        if not path:
            self.add_status.setText("Choisissez d'abord un fichier .gguf.")
            return
        if not pv.valid_model_name(name):
            self.add_status.setText("Nom invalide : minuscules, chiffres, tirets et points uniquement.")
            return
        self.set_busy(True, f"⏳ Import de {name}… (quelques minutes pour un gros fichier)")
        self.worker = FunctionWorker(pv.create_from_gguf, name, path)
        self.worker.done.connect(lambda ok, res: self.on_added(ok, "" if ok else str(res), name))
        self.worker.start()

    def on_added(self, ok: bool, error: str, name: str):
        self.set_busy(False)
        if ok:
            self.add_status.setText(f"✅ « {name} » est installé. Il apparaît dans le Chat et dans "
                                    "Modèles → Installés.")
            self.models_changed.emit()
        else:
            self.add_status.setText(f"<span style='color:{style.RED}'>❌ {error}</span>")
