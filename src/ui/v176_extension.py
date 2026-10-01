"""v176 : panneau AudioCraft unifié pour MusicGen et AudioGen."""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.backend import media_setup, media_weights, settings, creative_tools


AUDIO_IDS = {"musicgen-small", "musicgen-melody", "audiogen"}


class _AudioOneClick:
    def __init__(self, window):
        self.window = window
        self.tab = window.media_studio_tab
        self.tools = window.creative_tools_tab

        box = QGroupBox("AudioCraft — installation, poids et lancement")
        lay = QVBoxLayout(box)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        row = QHBoxLayout()
        self.install = QPushButton("⬇ Installer / réparer AudioCraft")
        self.install.setObjectName("Primary")
        self.weights = QPushButton("📦 Préparer les poids")
        self.start = QPushButton("▶ Démarrer AudioCraft")
        self.verify = QPushButton("🔎 Vérifier")
        self.open = QPushButton("🎵 Ouvrir l’interface")
        for b in (self.install, self.weights, self.start, self.verify, self.open):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

        # Insère juste après le guide de démarrage rapide.
        self.tab.layout().insertWidget(2, box)
        self.box = box

        self.install.clicked.connect(self.install_engine)
        self.weights.clicked.connect(self.prepare_weights)
        self.start.clicked.connect(self.start_engine)
        self.verify.clicked.connect(self.refresh)
        self.open.clicked.connect(self.open_engine)

        try:
            self.tab.models.currentItemChanged.connect(lambda *_: self.refresh())
        except Exception:
            pass

        self.refresh()

    def current_id(self):
        model = getattr(self.tab, "current_model", None) or {}
        return str(model.get("id") or "")

    def is_audio_model(self):
        return self.current_id() in AUDIO_IDS

    def engine_state(self):
        try:
            return media_setup.tool_state("audiocraft")
        except Exception:
            return {"installed": False, "state": "inconnu"}

    def weights_state(self):
        mid = self.current_id()
        try:
            return media_weights.state(mid)
        except Exception:
            return {"supported": False, "installed": False, "ready": False, "state": "inconnu"}

    def select_tool(self):
        idx = self.tools.choice.findData("audiocraft")
        if idx >= 0:
            self.tools.choice.setCurrentIndex(idx)
        root = str(settings.get("creative_tools_root") or "")
        if root:
            self.tools.directory.setText(root)

    def install_engine(self):
        self.select_tool()
        self.window.tabs.setCurrentWidget(self.tools)
        self.tools.refresh_status()
        self.tools.status.setText(
            "AudioCraft sélectionné. Choisissez Python 3.9 si nécessaire puis cliquez sur « 1 · Installer / reprendre »."
        )

    def prepare_weights(self):
        # Réutilise le bloc v172 déjà branché au modèle courant.
        btn = getattr(self.tab, "v172_weights_prepare", None)
        if btn is None:
            self.state.setText("❌ Le préparateur de poids v172 n'est pas disponible.")
            return
        if not self.engine_state().get("installed"):
            self.install_engine()
            return
        if btn.isEnabled():
            btn.click()
            self.state.setText("⏳ Préparation des poids lancée…")
            QTimer.singleShot(1200, self.refresh)
        else:
            self.refresh()

    def start_engine(self):
        if not self.engine_state().get("installed"):
            self.install_engine()
            return
        self.select_tool()
        try:
            self.tools.start_tool()
            self.state.setText("⏳ Démarrage d’AudioCraft…")
            QTimer.singleShot(1800, self.refresh)
        except Exception as exc:
            self.state.setText("❌ Démarrage impossible : " + str(exc))

    def open_engine(self):
        # Utilise l'adresse synchronisée par MainWindow quand le moteur démarre.
        if not self.tab.address.text().strip():
            self.start_engine()
            return
        self.tab.open_engine()

    def refresh(self):
        visible = self.is_audio_model()
        self.box.setVisible(visible)
        if not visible:
            return

        eng = self.engine_state()
        w = self.weights_state()
        address = self.tab.address.text().strip()

        installed = bool(eng.get("installed"))
        ready = bool(w.get("ready"))
        running = bool(address)

        self.install.setVisible(not installed)
        self.weights.setVisible(installed and not ready)
        self.start.setVisible(installed and ready and not running)
        self.open.setEnabled(running)

        if not installed:
            self.state.setText(
                "⚠️ AudioCraft n'est pas installé. Commencez par « Installer / réparer AudioCraft »."
            )
        elif not ready:
            self.state.setText(
                "🟠 AudioCraft est installé, mais les poids du modèle sélectionné ne sont pas encore prêts. "
                "Cliquez sur « Préparer les poids »."
            )
        elif not running:
            self.state.setText(
                "✅ AudioCraft et les poids sont prêts. Démarrez le moteur pour ouvrir l'interface locale."
            )
        else:
            self.state.setText(
                "✅ AudioCraft est prêt et l’interface locale est configurée. "
                "Vous pouvez ouvrir l’interface et générer votre audio."
            )

        # Synchronise le guide rapide existant pour éviter les informations contradictoires.
        try:
            self.tab.update_quick_guide()
        except Exception:
            pass


def install_v176(window):
    if getattr(window, "_v176_audio_one_click", False):
        return
    window.v176_audio_one_click = _AudioOneClick(window)
    window._v176_audio_one_click = True
