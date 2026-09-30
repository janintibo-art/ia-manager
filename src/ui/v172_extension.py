"""v172 : téléchargement direct des poids AudioCraft, TripoSR et Hunyuan3D."""
from __future__ import annotations

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout,
)

from src.backend import media_weights


def install_v172(window):
    if getattr(window, "_v172_media_weights", False):
        return

    tab = getattr(window, "media_studio_tab", None)
    if tab is None:
        return

    box = QGroupBox("Poids du moteur")
    layout = QVBoxLayout(box)

    info = QLabel()
    info.setWordWrap(True)
    layout.addWidget(info)

    row = QHBoxLayout()
    prepare = QPushButton("⬇ Télécharger / préparer les poids")
    prepare.setObjectName("Primary")
    verify = QPushButton("🔎 Vérifier")
    folder = QPushButton("📁 Ouvrir le cache")
    row.addWidget(prepare)
    row.addWidget(verify)
    row.addWidget(folder)
    row.addStretch(1)
    layout.addLayout(row)

    progress = QProgressBar()
    progress.setRange(0, 0)
    progress.setVisible(False)
    layout.addWidget(progress)

    status = QLabel()
    status.setWordWrap(True)
    layout.addWidget(status)

    # Après le guide rapide et, si présente, la zone packs ComfyUI v171.
    tab.layout().insertWidget(3, box)

    tab.v172_weights_box = box
    tab.v172_weights_info = info
    tab.v172_weights_prepare = prepare
    tab.v172_weights_verify = verify
    tab.v172_weights_folder = folder
    tab.v172_weights_progress = progress
    tab.v172_weights_status = status
    tab.v172_weights_process = None

    def model_id():
        model = getattr(tab, "current_model", None) or {}
        return str(model.get("id") or "")

    def refresh():
        mid = model_id()
        spec = media_weights.spec_for(mid)
        if not spec:
            box.setVisible(False)
            return

        box.setVisible(True)
        st = media_weights.state(mid)
        info.setText("<b>" + spec["name"] + "</b><br>" + spec["note"])

        busy = tab.v172_weights_process is not None
        prepare.setEnabled(not busy and st["installed"])
        verify.setEnabled(not busy)
        folder.setEnabled(st["installed"])

        if st["ready"]:
            status.setText("✅ Poids déjà préparés. Le moteur peut les utiliser depuis son cache local.")
            prepare.setText("✅ Poids prêts")
        elif st["installed"]:
            status.setText("📦 Moteur installé. Les poids ne sont pas encore préchargés.")
            prepare.setText("⬇ Télécharger / préparer les poids")
        else:
            status.setText("⚠️ Installez d'abord le moteur recommandé dans Outils locaux.")
            prepare.setText("⬇ Télécharger / préparer les poids")

    def verify_state():
        refresh()

    def open_cache():
        mid = model_id()
        spec = media_weights.spec_for(mid)
        if not spec:
            return
        try:
            p = media_weights.engine_paths(mid)
            cache = p["cache"]
            cache.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(cache.resolve())))
        except Exception as exc:
            status.setText("❌ " + str(exc))

    def stop_process_ref(p):
        if tab.v172_weights_process is p:
            tab.v172_weights_process = None
            progress.setVisible(False)
            refresh()

    def finished(p, code, exit_status):
        if tab.v172_weights_process is not p:
            return
        data = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        tab.v172_weights_process = None
        progress.setVisible(False)
        p.deleteLater()
        if code == 0:
            status.setText("✅ Téléchargement terminé. Les poids sont prêts dans le cache local du moteur.")
        else:
            tail = data[-1200:] if data else "Aucun détail disponible."
            status.setText("❌ Préparation des poids échouée.\n" + tail)
        refresh()

    def read_output(p):
        if tab.v172_weights_process is not p:
            return
        text = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
        if text.strip():
            # Garde la dernière ligne utile visible sans saturer l'écran.
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                status.setText("⏳ " + lines[-1][-600:])

    def start():
        mid = model_id()
        spec = media_weights.spec_for(mid)
        if not spec or tab.v172_weights_process is not None:
            return

        st = media_weights.state(mid)
        if not st["installed"]:
            status.setText("⚠️ Installez d'abord le moteur recommandé dans Outils locaux.")
            return

        if mid in ("musicgen-melody", "audiogen", "hunyuan3d"):
            reply = QMessageBox.question(
                tab,
                "Téléchargement volumineux",
                "Ce modèle peut télécharger plusieurs gigaoctets de données.\n"
                "Le téléchargement peut être repris par Hugging Face en cas de coupure.\n\nContinuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            cmd = media_weights.prepare_command(mid)
        except Exception as exc:
            status.setText("❌ " + str(exc))
            return

        p = QProcess(tab)
        tab.v172_weights_process = p
        env = QProcessEnvironment.systemEnvironment()
        for key, value in cmd["env"].items():
            env.insert(str(key), str(value))
        p.setProcessEnvironment(env)
        p.setWorkingDirectory(cmd["cwd"])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: read_output(p))
        p.finished.connect(lambda code, state: finished(p, code, state))
        p.errorOccurred.connect(lambda _err: status.setText("❌ Impossible de lancer le téléchargement : " + p.errorString()))

        progress.setVisible(True)
        status.setText("⏳ Préparation du cache Hugging Face…")
        prepare.setEnabled(False)
        verify.setEnabled(False)
        p.start(cmd["program"], cmd["args"])

    prepare.clicked.connect(start)
    verify.clicked.connect(verify_state)
    folder.clicked.connect(open_cache)

    try:
        tab.models.currentItemChanged.connect(lambda *_args: refresh())
    except Exception:
        pass

    refresh()
    window._v172_media_weights = True
