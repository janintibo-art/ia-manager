"""v171 : packs ComfyUI téléchargeables directement depuis Audio · Vidéo · 3D."""
from __future__ import annotations

import threading
import re

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout,
)

from src.backend import media_model_packs as packs


class _PackBridge(QObject):
    progress = pyqtSignal(str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)


def install_v171(window):
    if getattr(window, "_v171_comfy_packs", False):
        return

    tab = getattr(window, "media_studio_tab", None)
    if tab is None:
        return

    box = QGroupBox("Téléchargement des poids du modèle")
    lay = QVBoxLayout(box)

    info = QLabel(
        "Pour les modèles ComfyUI pris en charge, IA Manager télécharge tous les fichiers "
        "nécessaires directement dans les bons sous-dossiers de ComfyUI."
    )
    info.setWordWrap(True)
    lay.addWidget(info)

    row = QHBoxLayout()
    button = QPushButton("⬇ Télécharger le pack dans ComfyUI")
    button.setObjectName("Primary")
    check = QPushButton("🔎 Vérifier le pack")
    row.addWidget(button)
    row.addWidget(check)
    row.addStretch(1)
    lay.addLayout(row)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setVisible(False)
    lay.addWidget(progress)

    state = QLabel()
    state.setWordWrap(True)
    lay.addWidget(state)

    # Le bloc est compact et placé juste après le guide de démarrage rapide.
    tab.layout().insertWidget(2, box)

    bridge = _PackBridge(tab)
    tab.v171_pack_bridge = bridge
    tab.v171_pack_box = box
    tab.v171_pack_button = button
    tab.v171_pack_check = check
    tab.v171_pack_progress = progress
    tab.v171_pack_state = state
    tab.v171_pack_busy = False

    def current_pack():
        model = getattr(tab, "current_model", None) or {}
        return packs.pack_for(model.get("id")), model

    def resolve_root(ask=False):
        managed = packs.managed_comfy_root()
        if managed is not None:
            return managed
        if not ask:
            return None
        selected = QFileDialog.getExistingDirectory(
            tab,
            "Choisissez le dossier racine de ComfyUI",
        )
        if not selected:
            return None
        return packs.validate_comfy_root(selected)

    def refresh():
        pack, model = current_pack()
        busy = bool(getattr(tab, "v171_pack_busy", False))
        if not pack:
            box.setVisible(False)
            return
        box.setVisible(True)
        info.setText("<b>" + pack["name"] + "</b><br>" + pack["note"])
        button.setEnabled(not busy)
        check.setEnabled(not busy)

        root = resolve_root(False)
        if root is None:
            state.setText("ComfyUI n'est pas installé par IA Manager : le dossier vous sera demandé au téléchargement.")
            return
        try:
            s = packs.pack_state(model.get("id"), root)
            if s["complete"]:
                state.setText(f"✅ Pack complet : {s['present']}/{s['total']} fichiers présents.")
            else:
                state.setText(f"📦 Pack : {s['present']}/{s['total']} fichiers présents · {len(s['missing'])} à télécharger.")
        except Exception as exc:
            state.setText("Vérification impossible : " + str(exc))

    def on_progress(message):
        state.setText(message)
        match = re.search(r"·\s*(\d+)%\s*·", message)
        if match:
            progress.setVisible(True)
            progress.setValue(int(match.group(1)))

    def on_done(paths):
        tab.v171_pack_busy = False
        progress.setVisible(True)
        progress.setValue(100)
        button.setEnabled(True)
        check.setEnabled(True)
        state.setText(
            "✅ Pack installé dans ComfyUI : "
            + str(len(paths))
            + " fichier(s). Redémarrez ou actualisez ComfyUI puis chargez le workflow correspondant."
        )
        refresh()

    def on_failed(message):
        tab.v171_pack_busy = False
        button.setEnabled(True)
        check.setEnabled(True)
        state.setText("❌ " + message)

    bridge.progress.connect(on_progress)
    bridge.done.connect(on_done)
    bridge.failed.connect(on_failed)

    def verify():
        pack, model = current_pack()
        if not pack:
            return
        root = resolve_root(True)
        if root is None:
            return
        try:
            s = packs.pack_state(model.get("id"), root)
            if s["complete"]:
                state.setText(f"✅ Pack complet : {s['present']}/{s['total']} fichiers.")
            else:
                state.setText(f"⚠️ Pack incomplet : {s['present']}/{s['total']} fichiers présents.")
        except Exception as exc:
            state.setText("❌ " + str(exc))

    def download():
        pack, model = current_pack()
        if not pack or getattr(tab, "v171_pack_busy", False):
            return
        root = resolve_root(True)
        if root is None:
            return

        if model.get("id") == "ltx-video":
            answer = QMessageBox.question(
                tab,
                "Pack LTX-2 très lourd",
                "Le pack FP8 dépasse 30 Go. Le téléchargement peut être long et ce modèle reste "
                "très exigeant en VRAM.\n\nContinuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        tab.v171_pack_busy = True
        button.setEnabled(False)
        check.setEnabled(False)
        progress.setValue(0)
        progress.setVisible(True)
        state.setText("Préparation du pack…")

        def worker():
            try:
                result = packs.install_pack(model.get("id"), root, bridge.progress.emit)
                bridge.done.emit(result)
            except Exception as exc:
                bridge.failed.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    button.clicked.connect(download)
    check.clicked.connect(verify)

    # Met à jour le bloc à chaque changement de fiche.
    try:
        tab.models.currentItemChanged.connect(lambda *_args: refresh())
    except Exception:
        pass

    refresh()
    window._v171_comfy_packs = True
