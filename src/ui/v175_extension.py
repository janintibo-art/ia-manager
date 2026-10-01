"""v175 : cycle 1 clic ComfyUI dans l'onglet Création d'images."""
from __future__ import annotations

import requests
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.backend import settings, creative_tools


class _ImageOneClick:
    def __init__(self, window):
        self.window = window
        self.tab = window.image_studio_tab
        self.tools = window.creative_tools_tab

        box = QGroupBox("ComfyUI — installation et lancement")
        lay = QVBoxLayout(box)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        row = QHBoxLayout()
        self.install = QPushButton("⬇ Installer / réparer ComfyUI")
        self.install.setObjectName("Primary")
        self.start = QPushButton("▶ Démarrer ComfyUI")
        self.verify = QPushButton("🔎 Vérifier")
        self.open = QPushButton("🖥 Ouvrir ComfyUI")
        row.addWidget(self.install)
        row.addWidget(self.start)
        row.addWidget(self.verify)
        row.addWidget(self.open)
        row.addStretch(1)
        lay.addLayout(row)

        # L'onglet Image contient un QScrollArea. On ajoute le panneau au contenu.
        scroll = self.tab.findChild(__import__("PyQt6.QtWidgets", fromlist=["QScrollArea"]).QScrollArea)
        host = scroll.widget() if scroll else None
        if host is not None and host.layout() is not None:
            host.layout().insertWidget(1, box)
        else:
            self.tab.layout().insertWidget(0, box)

        self.box = box
        self.install.clicked.connect(self.install_comfy)
        self.start.clicked.connect(self.start_comfy)
        self.verify.clicked.connect(self.verify_all)
        self.open.clicked.connect(self.open_comfy)

        try:
            self.tab.catalog.currentIndexChanged.connect(lambda *_: self.refresh())
        except Exception:
            pass

        self.refresh()

    def root(self):
        value = str(settings.get("creative_tools_root") or "").strip()
        if value:
            return value
        return str(Path.home() / "IA Manager" / "Outils")

    def manifest(self):
        try:
            return creative_tools.read_manifest(self.root(), "comfyui")
        except Exception:
            return {}

    def installed(self):
        record = self.manifest()
        try:
            p = creative_tools.paths(self.root(), "comfyui")
            return str(record.get("state") or "").startswith("installé") and p["python"].is_file() and (p["source"] / "main.py").is_file()
        except Exception:
            return False

    def running(self):
        try:
            url = self.tab.url.text().strip() or "http://127.0.0.1:8188"
            r = requests.get(url.rstrip("/") + "/system_stats", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def model_present(self):
        try:
            model = self.tab.catalog.currentIndex()
            spec = __import__("src.backend.image_studio", fromlist=["MODELS"]).MODELS[model]
            wanted = str(spec.get("filename") or "")
            if not wanted:
                return False
            for i in range(self.tab.checkpoint.count()):
                if self.tab.checkpoint.itemText(i) == wanted:
                    return True
            managed = __import__("src.backend.image_studio", fromlist=["managed_checkpoints_dir"]).managed_checkpoints_dir()
            return bool(managed and (managed / wanted).is_file())
        except Exception:
            return False

    def select_comfy_tool(self):
        idx = self.tools.choice.findData("comfyui")
        if idx >= 0:
            self.tools.choice.setCurrentIndex(idx)
        # Harmonise le dossier d'installation avec les réglages actuels.
        self.tools.directory.setText(self.root())

    def install_comfy(self):
        self.select_comfy_tool()
        self.window.tabs.setCurrentWidget(self.tools)
        self.tools.refresh_status()
        self.tools.status.setText(
            "ComfyUI sélectionné. Choisissez Python 3.10/3.11 si nécessaire puis cliquez sur « 1 · Installer / reprendre »."
        )

    def start_comfy(self):
        if not self.installed():
            self.install_comfy()
            return

        self.select_comfy_tool()
        try:
            self.tools.start_tool()
            self.state.setText("⏳ Démarrage de ComfyUI…")
            QTimer.singleShot(2200, self.after_start)
        except Exception as exc:
            self.state.setText("❌ Démarrage impossible : " + str(exc))

    def after_start(self):
        self.verify_all()

    def verify_all(self):
        if self.running():
            try:
                self.tab.connect_engine()
            except Exception:
                pass
            QTimer.singleShot(500, self.refresh)
        else:
            self.refresh()

    def open_comfy(self):
        if not self.running():
            self.start_comfy()
            return
        try:
            self.tab.open_engine()
        except Exception as exc:
            self.state.setText("❌ " + str(exc))

    def refresh(self):
        installed = self.installed()
        running = self.running()
        model_ok = self.model_present()

        self.install.setVisible(not installed)
        self.start.setVisible(installed and not running)
        self.open.setEnabled(running)

        if not installed:
            self.state.setText(
                "⚠️ ComfyUI n'est pas encore installé par IA Manager. "
                "Utilisez « Installer / réparer ComfyUI »."
            )
        elif not running:
            self.state.setText(
                "🟠 ComfyUI est installé mais arrêté. Cliquez sur « Démarrer ComfyUI »."
            )
        elif model_ok:
            self.state.setText(
                "✅ ComfyUI fonctionne et le modèle sélectionné est présent. Vous pouvez générer une image."
            )
        else:
            self.state.setText(
                "✅ ComfyUI fonctionne. Le modèle sélectionné n'est pas encore détecté : "
                "utilisez « Télécharger et installer ce modèle » puis Vérifier."
            )

        # Le bouton natif reste le point unique pour les checkpoints.
        try:
            if not installed:
                self.tab.install_model_btn.setToolTip("Installez d'abord ComfyUI avec le panneau ci-dessus.")
            else:
                self.tab.install_model_btn.setToolTip("Télécharge le checkpoint directement dans ComfyUI.")
        except Exception:
            pass


def install_v175(window):
    if getattr(window, "_v175_image_one_click", False):
        return
    window.v175_image_one_click = _ImageOneClick(window)
    window._v175_image_one_click = True
