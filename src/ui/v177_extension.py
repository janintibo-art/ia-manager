"""v177 : parcours vidéo unifié Wan 2.1 / LTX-Video via ComfyUI."""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.backend import media_setup, media_model_packs as packs, settings


VIDEO_IDS = {"wan21", "ltx-video"}


class _VideoOneClick:
    def __init__(self, window):
        self.window = window
        self.tab = window.media_studio_tab
        self.tools = window.creative_tools_tab

        box = QGroupBox("Vidéo — ComfyUI + pack du modèle")
        lay = QVBoxLayout(box)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        row = QHBoxLayout()
        self.install = QPushButton("⬇ Installer / réparer ComfyUI")
        self.install.setObjectName("Primary")
        self.pack = QPushButton("📦 Télécharger le pack vidéo")
        self.start = QPushButton("▶ Démarrer ComfyUI")
        self.verify = QPushButton("🔎 Vérifier")
        self.open = QPushButton("🎬 Ouvrir ComfyUI")
        for b in (self.install, self.pack, self.start, self.verify, self.open):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

        # Après guide rapide et avant les blocs techniques v171/v172.
        self.tab.layout().insertWidget(2, box)
        self.box = box

        self.install.clicked.connect(self.install_comfy)
        self.pack.clicked.connect(self.download_pack)
        self.start.clicked.connect(self.start_comfy)
        self.verify.clicked.connect(self.verify_all)
        self.open.clicked.connect(self.open_comfy)

        try:
            self.tab.models.currentItemChanged.connect(lambda *_: self.refresh())
        except Exception:
            pass

        self.refresh()

    def current_id(self):
        model = getattr(self.tab, "current_model", None) or {}
        return str(model.get("id") or "")

    def is_video_model(self):
        return self.current_id() in VIDEO_IDS

    def comfy_state(self):
        try:
            return media_setup.tool_state("comfyui")
        except Exception:
            return {"installed": False, "state": "inconnu"}

    def pack_state(self):
        mid = self.current_id()
        root = packs.managed_comfy_root()
        if not root:
            return {"complete": False, "present": 0, "total": 0, "missing": []}
        try:
            return packs.pack_state(mid, root)
        except Exception:
            return {"complete": False, "present": 0, "total": 0, "missing": []}

    def select_comfy(self):
        idx = self.tools.choice.findData("comfyui")
        if idx >= 0:
            self.tools.choice.setCurrentIndex(idx)
        root = str(settings.get("creative_tools_root") or "")
        if root:
            self.tools.directory.setText(root)

    def install_comfy(self):
        self.select_comfy()
        self.window.tabs.setCurrentWidget(self.tools)
        self.tools.refresh_status()
        self.tools.status.setText(
            "ComfyUI sélectionné. Choisissez Python 3.10/3.11 si nécessaire puis cliquez sur « 1 · Installer / reprendre »."
        )

    def download_pack(self):
        if not self.comfy_state().get("installed"):
            self.install_comfy()
            return

        # Réutilise directement le téléchargement multi-fichiers v171.
        btn = getattr(self.tab, "v171_pack_button", None)
        if btn is None:
            self.state.setText("❌ Le téléchargement de packs v171 n'est pas disponible.")
            return

        if btn.isEnabled():
            btn.click()
            self.state.setText("⏳ Téléchargement du pack vidéo lancé…")
            QTimer.singleShot(1200, self.refresh)
        else:
            self.refresh()

    def start_comfy(self):
        if not self.comfy_state().get("installed"):
            self.install_comfy()
            return
        self.select_comfy()
        try:
            self.tools.start_tool()
            self.state.setText("⏳ Démarrage de ComfyUI…")
            QTimer.singleShot(1800, self.refresh)
        except Exception as exc:
            self.state.setText("❌ Démarrage impossible : " + str(exc))

    def verify_all(self):
        check = getattr(self.tab, "v171_pack_check", None)
        if check is not None and check.isEnabled():
            try:
                check.click()
            except Exception:
                pass
        self.refresh()

    def open_comfy(self):
        if not self.tab.address.text().strip():
            self.start_comfy()
            return
        self.tab.open_engine()

    def refresh(self):
        visible = self.is_video_model()
        self.box.setVisible(visible)
        if not visible:
            return

        eng = self.comfy_state()
        pack = self.pack_state()
        address = self.tab.address.text().strip()

        installed = bool(eng.get("installed"))
        complete = bool(pack.get("complete"))
        running = bool(address)

        self.install.setVisible(not installed)
        self.pack.setVisible(installed and not complete)
        self.start.setVisible(installed and complete and not running)
        self.open.setEnabled(running)

        if not installed:
            self.state.setText(
                "⚠️ ComfyUI n'est pas installé. Commencez par « Installer / réparer ComfyUI »."
            )
        elif not complete:
            present = int(pack.get("present") or 0)
            total = int(pack.get("total") or 0)
            if total:
                self.state.setText(
                    f"🟠 ComfyUI est installé. Pack vidéo incomplet : {present}/{total} fichier(s). "
                    "Cliquez sur « Télécharger le pack vidéo »."
                )
            else:
                self.state.setText(
                    "🟠 ComfyUI est installé, mais le pack vidéo n'est pas encore prêt. "
                    "Cliquez sur « Télécharger le pack vidéo »."
                )
        elif not running:
            self.state.setText(
                "✅ ComfyUI et le pack vidéo sont prêts. Démarrez ComfyUI pour charger le workflow correspondant."
            )
        else:
            self.state.setText(
                "✅ ComfyUI et le pack vidéo sont prêts. Ouvrez ComfyUI puis chargez le workflow Wan/LTX correspondant."
            )

        try:
            self.tab.update_quick_guide()
        except Exception:
            pass


def install_v177(window):
    if getattr(window, "_v177_video_one_click", False):
        return
    window.v177_video_one_click = _VideoOneClick(window)
    window._v177_video_one_click = True
