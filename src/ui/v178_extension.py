"""v178 : parcours 3D unifié TripoSR / Hunyuan3D."""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.backend import media_setup, media_weights, settings


THREED_IDS = {"triposr", "hunyuan3d"}


class _ThreeDOneClick:
    def __init__(self, window):
        self.window = window
        self.tab = window.media_studio_tab
        self.tools = window.creative_tools_tab

        box = QGroupBox("3D — moteur, poids et lancement")
        lay = QVBoxLayout(box)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        row = QHBoxLayout()
        self.install = QPushButton("⬇ Installer / réparer le moteur 3D")
        self.install.setObjectName("Primary")
        self.weights = QPushButton("📦 Préparer les poids")
        self.start = QPushButton("▶ Démarrer le moteur")
        self.verify = QPushButton("🔎 Vérifier")
        self.open = QPushButton("🧊 Ouvrir l’interface 3D")
        for b in (self.install, self.weights, self.start, self.verify, self.open):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

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

    def is_3d(self):
        return self.current_id() in THREED_IDS

    def tool_key(self):
        return media_setup.tool_for_model(getattr(self.tab, "current_model", None))

    def tool_state(self):
        key = self.tool_key()
        try:
            return media_setup.tool_state(key) if key else {"installed": False, "state": "non géré"}
        except Exception:
            return {"installed": False, "state": "inconnu"}

    def weights_state(self):
        try:
            return media_weights.state(self.current_id())
        except Exception:
            return {"supported": False, "installed": False, "ready": False, "state": "inconnu"}

    def select_tool(self):
        key = self.tool_key()
        idx = self.tools.choice.findData(key)
        if idx >= 0:
            self.tools.choice.setCurrentIndex(idx)
        root = str(settings.get("creative_tools_root") or "")
        if root:
            self.tools.directory.setText(root)
        return key

    def install_engine(self):
        key = self.select_tool()
        if not key:
            self.state.setText("❌ Aucun moteur 3D associé à cette fiche.")
            return
        self.window.tabs.setCurrentWidget(self.tools)
        self.tools.refresh_status()
        self.tools.status.setText(
            "Moteur 3D sélectionné. Choisissez Python 3.10/3.11 si nécessaire puis cliquez sur « 1 · Installer / reprendre »."
        )

    def prepare_weights(self):
        if not self.tool_state().get("installed"):
            self.install_engine()
            return

        btn = getattr(self.tab, "v172_weights_prepare", None)
        if btn is None:
            self.state.setText("❌ Le préparateur de poids v172 n'est pas disponible.")
            return

        if btn.isEnabled():
            btn.click()
            self.state.setText("⏳ Préparation des poids 3D lancée…")
            QTimer.singleShot(1200, self.refresh)
        else:
            self.refresh()

    def start_engine(self):
        if not self.tool_state().get("installed"):
            self.install_engine()
            return
        self.select_tool()
        try:
            self.tools.start_tool()
            self.state.setText("⏳ Démarrage du moteur 3D…")
            QTimer.singleShot(1800, self.refresh)
        except Exception as exc:
            self.state.setText("❌ Démarrage impossible : " + str(exc))

    def open_engine(self):
        if not self.tab.address.text().strip():
            self.start_engine()
            return
        self.tab.open_engine()

    def refresh(self):
        visible = self.is_3d()
        self.box.setVisible(visible)
        if not visible:
            return

        key = self.tool_key()
        eng = self.tool_state()
        weights = self.weights_state()
        address = self.tab.address.text().strip()

        installed = bool(eng.get("installed"))
        ready = bool(weights.get("ready"))
        running = bool(address)

        name = {
            "triposr": "TripoSR",
            "hunyuan3d": "Hunyuan3D 2",
        }.get(key, "moteur 3D")

        self.install.setText("⬇ Installer / réparer " + name)
        self.start.setText("▶ Démarrer " + name)

        self.install.setVisible(not installed)
        self.weights.setVisible(installed and not ready)
        self.start.setVisible(installed and ready and not running)
        self.open.setEnabled(running)

        if not installed:
            self.state.setText(
                f"⚠️ {name} n'est pas installé. Commencez par « Installer / réparer {name} »."
            )
        elif not ready:
            self.state.setText(
                f"🟠 {name} est installé, mais les poids ne sont pas encore prêts. "
                "Cliquez sur « Préparer les poids »."
            )
        elif not running:
            self.state.setText(
                f"✅ {name} et ses poids sont prêts. Démarrez le moteur pour ouvrir l'interface locale."
            )
        else:
            self.state.setText(
                f"✅ {name} est prêt. Ouvrez l'interface locale pour générer ou reconstruire votre objet 3D."
            )

        try:
            self.tab.update_quick_guide()
        except Exception:
            pass


def install_v178(window):
    if getattr(window, "_v178_3d_one_click", False):
        return
    window.v178_3d_one_click = _ThreeDOneClick(window)
    window._v178_3d_one_click = True
