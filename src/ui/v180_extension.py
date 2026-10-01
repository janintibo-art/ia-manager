"""v180 : installation directe des packs Image avancés."""
from __future__ import annotations

import re
import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QScrollArea,
)

from src.backend import advanced_image_packs as packs


class _Bridge(QObject):
    progress = pyqtSignal(str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)


def install_v180(window):
    if getattr(window, "_v180_advanced_image_packs", False):
        return

    tab = window.image_studio_tab

    box = QGroupBox("Packs Image avancés — installation directe")
    lay = QVBoxLayout(box)

    intro = QLabel(
        "Installe directement dans ComfyUI les modèles Image avancés encore signalés comme partiels dans l’audit."
    )
    intro.setWordWrap(True)
    lay.addWidget(intro)

    selector = QComboBox()
    for pack_id, pack in packs.PACKS.items():
        selector.addItem(pack["name"], pack_id)
    lay.addWidget(selector)

    info = QLabel()
    info.setWordWrap(True)
    lay.addWidget(info)

    row = QHBoxLayout()
    download = QPushButton("⬇ Télécharger / installer le pack")
    download.setObjectName("Primary")
    verify = QPushButton("🔎 Vérifier")
    row.addWidget(download)
    row.addWidget(verify)
    row.addStretch(1)
    lay.addLayout(row)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setVisible(False)
    lay.addWidget(progress)

    state = QLabel()
    state.setWordWrap(True)
    lay.addWidget(state)

    scroll = tab.findChild(QScrollArea)
    host = scroll.widget() if scroll else None
    if host is not None and host.layout() is not None:
        host.layout().insertWidget(3, box)
    else:
        tab.layout().insertWidget(1, box)

    bridge = _Bridge(tab)
    tab.v180_advanced_bridge = bridge
    tab.v180_advanced_busy = False

    def current_id():
        return str(selector.currentData() or "")

    def resolve_root(ask=False):
        managed = packs.managed_comfy_root()
        if managed is not None:
            return managed
        if not ask:
            return None
        selected = QFileDialog.getExistingDirectory(tab, "Choisissez le dossier racine de ComfyUI")
        if not selected:
            return None
        return packs.validate_comfy_root(selected)

    def refresh():
        pack = packs.pack_for(current_id())
        if not pack:
            return
        info.setText("<b>" + pack["name"] + "</b><br>" + pack["note"])
        busy = bool(tab.v180_advanced_busy)
        download.setEnabled(not busy)
        verify.setEnabled(not busy)
        root = resolve_root(False)
        if root is None:
            state.setText("ComfyUI géré par IA Manager non détecté. Le dossier sera demandé au téléchargement.")
            return
        try:
            s = packs.pack_state(current_id(), root)
            if s["complete"]:
                state.setText(f"✅ Pack complet : {s['present']}/{s['total']} fichier(s) présents.")
            else:
                extra = "" if s["node_ready"] else " · nœud ComfyUI à installer"
                state.setText(f"📦 Pack incomplet : {s['present']}/{s['total']} fichier(s){extra}.")
        except Exception as exc:
            state.setText("Vérification impossible : " + str(exc))

    def on_progress(message):
        state.setText(message)
        match = re.search(r"·\s*(\d+)%\s*·", message)
        if match:
            progress.setVisible(True)
            progress.setValue(int(match.group(1)))

    def on_done(paths):
        tab.v180_advanced_busy = False
        progress.setVisible(True)
        progress.setValue(100)
        state.setText("✅ Installation terminée : " + str(len(paths)) + " fichier(s). Redémarrez ComfyUI si un nœud a été ajouté.")
        refresh()
        audit = getattr(window, "installation_audit_tab", None)
        if audit is not None:
            audit.refresh()

    def on_failed(message):
        tab.v180_advanced_busy = False
        download.setEnabled(True)
        verify.setEnabled(True)
        state.setText("❌ " + message)

    bridge.progress.connect(on_progress)
    bridge.done.connect(on_done)
    bridge.failed.connect(on_failed)

    def verify_pack():
        root = resolve_root(True)
        if root is None:
            return
        try:
            s = packs.pack_state(current_id(), root)
            if s["complete"]:
                state.setText(f"✅ Pack complet : {s['present']}/{s['total']} fichier(s).")
            else:
                state.setText(f"⚠️ Pack incomplet : {s['present']}/{s['total']} fichier(s).")
        except Exception as exc:
            state.setText("❌ " + str(exc))

    def download_pack():
        if tab.v180_advanced_busy:
            return
        root = resolve_root(True)
        if root is None:
            return

        pack_id = current_id()
        pack = packs.pack_for(pack_id)
        if pack_id in ("flux-dev", "sd35-medium", "ip-adapter"):
            reply = QMessageBox.question(
                tab,
                "Téléchargement volumineux",
                pack["name"] + " peut télécharger plusieurs gigaoctets de données. "
                "La reprise après coupure est prise en charge.\n\nContinuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        tab.v180_advanced_busy = True
        download.setEnabled(False)
        verify.setEnabled(False)
        progress.setValue(0)
        progress.setVisible(True)
        state.setText("Préparation du pack…")

        def worker():
            try:
                result = packs.install_pack(pack_id, root, bridge.progress.emit)
                bridge.done.emit(result)
            except Exception as exc:
                bridge.failed.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    selector.currentIndexChanged.connect(refresh)
    download.clicked.connect(download_pack)
    verify.clicked.connect(verify_pack)

    refresh()
    window._v180_advanced_image_packs = True
