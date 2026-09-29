"""v154 : import automatique des modèles téléchargés vers ComfyUI."""
import json
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.backend import creative_tools as tools, settings


KNOWN = {
    "qwen_3_4b.safetensors": "text_encoders",
    "z_image_turbo_bf16.safetensors": "diffusion_models",
}

PATTERNS = (
    ("text_encoder", "text_encoders"),
    ("qwen", "text_encoders"),
    ("clip", "clip"),
    ("vae", "vae"),
    ("lora", "loras"),
    ("controlnet", "controlnet"),
    ("diffusion", "diffusion_models"),
    ("unet", "diffusion_models"),
)


def _downloads_default():
    saved = settings.get("comfyui_import_downloads")
    if saved:
        p = Path(saved).expanduser()
        if p.is_dir():
            return p
    for name in ("Downloads", "Téléchargements", "Telechargements"):
        p = Path.home() / name
        if p.is_dir():
            return p
    return Path.home()


def _models_root(tab):
    return tools.paths(tab.directory.text(), "comfyui")["source"] / "models"


def _classify(path):
    name = path.name.lower()
    if name in KNOWN:
        return KNOWN[name], "connu"
    for token, folder in PATTERNS:
        if token in name:
            return folder, "déduit"
    if path.suffix.lower() in (".safetensors", ".ckpt", ".pt", ".pth", ".bin"):
        return "checkpoints", "par défaut"
    return "", "ignoré"


def _history_file():
    p = Path.home() / ".ia_manager" / "comfyui_import_history.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_history():
    try:
        data = json.loads(_history_file().read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_history(rows):
    _history_file().write_text(
        json.dumps(rows[-300:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def install_v154(window):
    if getattr(window, "_v154_comfy_import", False):
        return

    tab = getattr(window, "creative_tools_tab", None)
    if tab is None:
        return

    root = tab.layout()

    box = QGroupBox("📥 Importer les modèles téléchargés dans ComfyUI")
    lay = QVBoxLayout(box)

    intro = QLabel(
        "Scanne votre dossier Téléchargements, reconnaît les modèles ComfyUI et propose "
        "automatiquement leur dossier de destination. Aucun fichier existant n'est écrasé."
    )
    intro.setWordWrap(True)
    lay.addWidget(intro)

    row = QHBoxLayout()
    tab.v154_downloads = QLineEdit(str(_downloads_default()))
    row.addWidget(tab.v154_downloads, 1)
    choose = QPushButton("Choisir le dossier…")
    row.addWidget(choose)
    lay.addLayout(row)

    actions = QHBoxLayout()
    tab.v154_scan = QPushButton("🔎 Scanner les téléchargements")
    actions.addWidget(tab.v154_scan)

    tab.v154_import = QPushButton("📦 Importer les fichiers reconnus")
    tab.v154_import.setObjectName("Primary")
    tab.v154_import.setEnabled(False)
    actions.addWidget(tab.v154_import)

    tab.v154_open = QPushButton("📁 Ouvrir les modèles ComfyUI")
    actions.addWidget(tab.v154_open)
    actions.addStretch()
    lay.addLayout(actions)

    tab.v154_status = QLabel("Prêt.")
    tab.v154_status.setWordWrap(True)
    lay.addWidget(tab.v154_status)

    tab.v154_table = QTableWidget(0, 5)
    tab.v154_table.setHorizontalHeaderLabels(
        ["Fichier", "Taille", "Destination", "Détection", "État"]
    )
    tab.v154_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tab.v154_table.horizontalHeader().setStretchLastSection(True)
    tab.v154_table.setMaximumHeight(300)
    lay.addWidget(tab.v154_table)

    # Sous ComfyUI Doctor, avant les logs/actions techniques.
    root.insertWidget(7, box)

    tab.v154_candidates = []

    def choose_folder():
        p = QFileDialog.getExistingDirectory(
            tab, "Choisir le dossier de téléchargements", tab.v154_downloads.text()
        )
        if p:
            tab.v154_downloads.setText(p)
            settings.set("comfyui_import_downloads", p)

    choose.clicked.connect(choose_folder)

    def scan():
        src = Path(tab.v154_downloads.text().strip()).expanduser()
        if not src.is_dir():
            tab.v154_status.setText("Le dossier de téléchargements n'existe pas.")
            return

        settings.set("comfyui_import_downloads", str(src))
        models_root = _models_root(tab)

        rows = []
        for p in sorted(src.iterdir()):
            if not p.is_file():
                continue
            folder, kind = _classify(p)
            if not folder:
                continue
            destination = models_root / folder / p.name
            rows.append((p, folder, kind, destination))

        tab.v154_candidates = rows
        tab.v154_table.setRowCount(len(rows))

        for r, (p, folder, kind, destination) in enumerate(rows):
            size_gb = p.stat().st_size / 2**30
            state = "déjà présent" if destination.exists() else "prêt à importer"
            values = [
                p.name,
                f"{size_gb:.2f} Go",
                f"models/{folder}",
                kind,
                state,
            ]
            for c, value in enumerate(values):
                tab.v154_table.setItem(r, c, QTableWidgetItem(value))

        tab.v154_table.resizeColumnsToContents()
        pending = sum(1 for _, _, _, dst in rows if not dst.exists())
        tab.v154_import.setEnabled(pending > 0)

        if rows:
            tab.v154_status.setText(
                f"{len(rows)} fichier(s) reconnu(s), dont {pending} à importer."
            )
        else:
            tab.v154_status.setText(
                "Aucun modèle reconnu dans ce dossier. Vérifiez que les téléchargements sont terminés."
            )

    tab.v154_scan.clicked.connect(scan)

    def do_import():
        imported = 0
        skipped = 0
        failed = 0
        history = _load_history()

        for p, folder, kind, destination in list(tab.v154_candidates):
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    skipped += 1
                    continue

                shutil.move(str(p), str(destination))
                imported += 1
                history.append({
                    "created": datetime.now().isoformat(timespec="seconds"),
                    "source": str(p),
                    "destination": str(destination),
                    "classification": kind,
                    "folder": folder,
                })
            except Exception:
                failed += 1

        _save_history(history)

        tab.v154_status.setText(
            f"✅ Import terminé : {imported} déplacé(s), {skipped} déjà présent(s), "
            f"{failed} échec(s). Redémarrez ou actualisez ComfyUI."
        )
        scan()

    tab.v154_import.clicked.connect(do_import)

    def open_models():
        p = _models_root(tab)
        p.mkdir(parents=True, exist_ok=True)
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    tab.v154_open.clicked.connect(open_models)

    # Premier scan automatique si on est déjà sur une installation ComfyUI.
    try:
        scan()
    except Exception:
        pass

    window._v154_comfy_import = True
