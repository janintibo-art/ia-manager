"""v174 : cycle 1 clic des modèles Ollama dans le catalogue Chat."""
from __future__ import annotations

from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.backend import installer_center


class _ChatModelActions:
    def __init__(self, window):
        self.window = window
        self.tab = window.models_tab
        self.serve_process = None

        box = QGroupBox("Installation et lancement")
        lay = QVBoxLayout(box)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        row = QHBoxLayout()
        self.prepare = QPushButton("⬇ Préparer Ollama")
        self.prepare.setObjectName("Primary")
        self.verify = QPushButton("🔎 Vérifier")
        self.start = QPushButton("▶ Démarrer Ollama")
        self.chat = QPushButton("💬 Utiliser dans le Chat")
        row.addWidget(self.prepare)
        row.addWidget(self.verify)
        row.addWidget(self.start)
        row.addWidget(self.chat)
        row.addStretch(1)
        lay.addLayout(row)

        parent = self.tab.download_btn.parentWidget()
        parent.layout().addWidget(box)
        self.box = box

        self.prepare.clicked.connect(self.prepare_ollama)
        self.verify.clicked.connect(self.refresh)
        self.start.clicked.connect(self.start_ollama)
        self.chat.clicked.connect(self.open_chat)

        try:
            self.tab.model_list.currentItemChanged.connect(lambda *_args: self.refresh())
        except Exception:
            pass

        # Remplace uniquement le clic Télécharger afin d'éviter le cul-de-sac
        # "Ollama absent -> ouvrir un site".
        try:
            self.tab.download_btn.clicked.disconnect()
        except Exception:
            pass
        self.tab.download_btn.clicked.connect(self.download_selected)

        self.refresh()

    def current_model_id(self):
        return getattr(self.tab, "current_id", None)

    def ollama_path(self):
        try:
            return installer_center.detection().get("ollama", "")
        except Exception:
            return ""

    def refresh(self):
        mid = self.current_model_id()
        installed = bool(mid and self.tab.is_installed(mid))
        running = self.tab.ai_manager.is_ollama_running()
        detected = bool(self.ollama_path())

        self.prepare.setVisible(not detected)
        self.start.setVisible(detected and not running)
        self.verify.setVisible(True)
        self.chat.setVisible(installed and running)
        self.chat.setEnabled(installed and running)

        if not mid:
            self.state.setText("Sélectionnez un modèle.")
        elif not detected:
            self.state.setText(
                "⚠️ Ollama n'est pas installé. Cliquez sur « Préparer Ollama » : "
                "IA Manager ouvrira directement le Centre d'installation sur Ollama."
            )
        elif not running:
            self.state.setText(
                "🟠 Ollama est installé mais son serveur local ne répond pas. "
                "Cliquez sur « Démarrer Ollama »."
            )
        elif installed:
            self.state.setText("✅ Ollama fonctionne et ce modèle est installé. Il est prêt pour le Chat.")
        else:
            self.state.setText("✅ Ollama fonctionne. Cliquez sur « Télécharger » pour installer ce modèle.")

    def prepare_ollama(self):
        install_tab = getattr(self.window, "installation_center_tab", None)
        if install_tab is None:
            self.state.setText("❌ Centre d'installation introuvable.")
            return

        # Sélectionne directement la ligne Ollama si elle existe.
        try:
            install_tab.refresh()
            for i in range(install_tab.tree.topLevelItemCount()):
                item = install_tab.tree.topLevelItem(i)
                row = item.data(0, 0x0100)
                if isinstance(row, dict) and row.get("id") == "ollama":
                    install_tab.tree.setCurrentItem(item)
                    break
        except Exception:
            pass

        self.window.tabs.setCurrentWidget(install_tab)

    def start_ollama(self):
        path = self.ollama_path()
        if not path:
            self.prepare_ollama()
            return

        # `ollama serve` est volontairement lancé détaché : il doit rester actif
        # quand l'utilisateur change d'onglet dans IA Manager.
        ok = QProcess.startDetached(path, ["serve"])
        if not ok:
            # Sur certaines installations Windows, lancer simplement l'exécutable
            # démarre l'application/tray qui expose ensuite l'API locale.
            ok = QProcess.startDetached(path, [])

        if not ok:
            self.state.setText("❌ Impossible de démarrer Ollama automatiquement.")
            return

        self.state.setText("⏳ Démarrage d'Ollama…")
        QTimer.singleShot(1800, self.after_start)

    def after_start(self):
        self.tab.refresh_installed_models()
        self.refresh()

    def download_selected(self):
        if not self.current_model_id():
            return
        if not self.tab.ai_manager.is_ollama_running():
            if self.ollama_path():
                self.state.setText(
                    "Ollama est installé mais arrêté. Démarrez-le puis cliquez à nouveau sur Télécharger."
                )
                self.start_ollama()
            else:
                self.prepare_ollama()
            return

        # Réutilise le téléchargement natif, déjà fiable et compatible progression.
        type(self.tab).download_model(self.tab)

    def open_chat(self):
        mid = self.current_model_id()
        if not mid:
            return
        chat = self.window.chat_tab
        chat.refresh_models()
        if chat.select_ref(mid) or chat.select_ref("ollama::" + mid):
            self.window.tabs.setCurrentWidget(chat)
            try:
                chat.status.setText("✅ Modèle prêt : " + mid)
            except Exception:
                pass
        else:
            self.state.setText("⚠️ Le modèle est installé mais n'apparaît pas encore dans le Chat. Cliquez sur Vérifier.")


def install_v174(window):
    if getattr(window, "_v174_chat_model_actions", False):
        return
    window.v174_chat_model_actions = _ChatModelActions(window)
    window._v174_chat_model_actions = True
