"""v153 : ComfyUI Doctor + catalogue gratuit/local vs API partenaire."""
from pathlib import Path
import shutil

from PyQt6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.backend import creative_tools as tools, settings

FREE_CATALOG = [
    ("✅ LOCAL", "ComfyUI + modèles locaux", "Pas de crédit par génération", "Calcul sur votre PC ; licences des modèles à respecter."),
    ("✅ LOCAL", "Stable Diffusion / SDXL", "Pas de crédit par génération", "Poids locaux dans ComfyUI."),
    ("✅ LOCAL", "Wan / LTX Video / HunyuanVideo", "Pas de crédit par génération", "Vidéo locale ; besoins GPU variables."),
    ("✅ LOCAL", "Hunyuan3D / TripoSR", "Pas de crédit par génération", "3D locale ; modèles et dépendances à télécharger."),
    ("✅ LOCAL", "AudioCraft / MusicGen / AudioGen", "Pas de crédit par génération", "Audio local via IA Manager."),
    ("✅ LOCAL", "ACE-Step et autres modèles audio ouverts", "Pas de crédit par génération", "Quand exécutés localement dans ComfyUI."),
    ("💳 API", "ByteDance Seed Audio", "Crédits / facturation API", "Partner Node ComfyUI ; pas 100 % local."),
    ("💳 API", "ByteDance Seedance", "Crédits / facturation API", "Partner Node vidéo ; pas 100 % local."),
    ("💳 API", "Autres Partner Nodes fermés", "Selon fournisseur", "Toujours vérifier le badge/prix affiché par ComfyUI."),
]

def _comfy_paths(tab):
    return tools.paths(tab.directory.text(), "comfyui")

def _doctor_rows(tab):
    p = _comfy_paths(tab)
    source = p["source"]
    py = p["python"]
    byte_file = source / "comfy_api_nodes" / "nodes_bytedance.py"
    has_byte = False
    try:
        has_byte = byte_file.is_file() and "ByteDanceSeedAudio" in byte_file.read_text(
            encoding="utf-8", errors="ignore"
        )
    except Exception:
        pass
    manager_req = source / "manager_requirements.txt"
    return [
        ("Installation ComfyUI", source.joinpath("main.py").is_file(), str(source)),
        ("Python isolé", py.is_file(), str(py)),
        ("Git", shutil.which("git") is not None, shutil.which("git") or "introuvable"),
        ("Manager officiel disponible", manager_req.is_file(), str(manager_req)),
        ("ByteDance SeedAudio présent", has_byte, str(byte_file)),
        ("Nœuds API partenaires",
         settings.get("comfyui_partner_nodes") is True,
         "activés" if settings.get("comfyui_partner_nodes") is True else "désactivés (mode local par défaut)"),
        ("ComfyUI Manager au démarrage",
         settings.get("comfyui_manager_enabled") is True,
         "activé" if settings.get("comfyui_manager_enabled") is True else "désactivé"),
    ]

def _patch_launch():
    if getattr(tools, "_v153_launch_patched", False):
        return
    original = tools.launch_command
    def launch_command(root, key, hardware="nvidia", windows=None):
        cmd = original(root, key, hardware, windows)
        if key != "comfyui":
            return cmd
        args = [a for a in list(cmd["args"]) if a not in ("--disable-api-nodes", "--enable-manager")]
        if settings.get("comfyui_partner_nodes") is not True:
            args.append("--disable-api-nodes")
        if settings.get("comfyui_manager_enabled") is True:
            args.append("--enable-manager")
        result = dict(cmd)
        result["args"] = args
        return result
    tools.launch_command = launch_command
    tools._v153_launch_patched = True

def install_v153(window):
    if getattr(window, "_v153_comfy_doctor", False):
        return
    _patch_launch()
    tab = getattr(window, "creative_tools_tab", None)
    if tab is None:
        return

    root = tab.layout()
    box = QGroupBox("🩺 ComfyUI Doctor")
    layout = QVBoxLayout(box)

    intro = QLabel(
        "Vérifie pourquoi un workflow ComfyUI ne fonctionne pas et distingue clairement "
        "ce qui est local/gratuit de ce qui utilise une API partenaire."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    toggles = QHBoxLayout()
    tab.v153_partner = QCheckBox("Activer les nœuds API partenaires")
    tab.v153_partner.setChecked(settings.get("comfyui_partner_nodes") is True)
    tab.v153_partner.setToolTip(
        "Permet ByteDance Seed Audio/Seedance et d'autres Partner Nodes. "
        "Ces services peuvent consommer des crédits."
    )
    toggles.addWidget(tab.v153_partner)

    tab.v153_manager = QCheckBox("Activer ComfyUI Manager")
    tab.v153_manager.setChecked(settings.get("comfyui_manager_enabled") is not False)
    toggles.addWidget(tab.v153_manager)
    toggles.addStretch()
    layout.addLayout(toggles)

    warning = QLabel(
        "⚠️ Les nœuds partenaires ne sont pas 100 % locaux. "
        "Laissez l'option API désactivée si vous voulez uniquement des outils gratuits/localement calculés."
    )
    warning.setWordWrap(True)
    layout.addWidget(warning)

    buttons = QHBoxLayout()
    tab.v153_diag = QPushButton("🔎 Diagnostiquer ComfyUI")
    buttons.addWidget(tab.v153_diag)
    tab.v153_repair = QPushButton("🛠 Mettre à jour / réparer ComfyUI")
    tab.v153_repair.setObjectName("Primary")
    buttons.addWidget(tab.v153_repair)
    tab.v153_free = QPushButton("💚 Voir ce qui est gratuit")
    buttons.addWidget(tab.v153_free)
    buttons.addStretch()
    layout.addLayout(buttons)

    tab.v153_status = QLabel("Prêt.")
    tab.v153_status.setWordWrap(True)
    layout.addWidget(tab.v153_status)

    tab.v153_table = QTableWidget(0, 3)
    tab.v153_table.setHorizontalHeaderLabels(["Contrôle", "État", "Détail"])
    tab.v153_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tab.v153_table.horizontalHeader().setStretchLastSection(True)
    tab.v153_table.setMaximumHeight(250)
    layout.addWidget(tab.v153_table)

    tab.v153_free_table = QTableWidget(0, 4)
    tab.v153_free_table.setHorizontalHeaderLabels(
        ["Type", "Outil / famille", "Coût d’usage", "Remarque"]
    )
    tab.v153_free_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tab.v153_free_table.horizontalHeader().setStretchLastSection(True)
    tab.v153_free_table.setMaximumHeight(260)
    tab.v153_free_table.setVisible(False)
    layout.addWidget(tab.v153_free_table)

    root.insertWidget(6, box)

    def save_options():
        settings.set("comfyui_partner_nodes", tab.v153_partner.isChecked())
        settings.set("comfyui_manager_enabled", tab.v153_manager.isChecked())
        tab.v153_status.setText(
            "✅ Options enregistrées. Redémarrez ComfyUI avec « 2 · Démarrer » pour les appliquer."
        )

    tab.v153_partner.toggled.connect(lambda _v: save_options())
    tab.v153_manager.toggled.connect(lambda _v: save_options())

    def diagnose():
        rows = _doctor_rows(tab)
        tab.v153_table.setRowCount(len(rows))
        problems = 0
        for r, (name, ok, detail) in enumerate(rows):
            if not ok:
                problems += 1
            tab.v153_table.setItem(r, 0, QTableWidgetItem(name))
            tab.v153_table.setItem(r, 1, QTableWidgetItem("✅ OK" if ok else "⚠️ À vérifier"))
            tab.v153_table.setItem(r, 2, QTableWidgetItem(detail))
        tab.v153_table.resizeColumnsToContents()

        p = _comfy_paths(tab)
        byte_file = p["source"] / "comfy_api_nodes" / "nodes_bytedance.py"
        try:
            has_byte = byte_file.is_file() and "ByteDanceSeedAudio" in byte_file.read_text(
                encoding="utf-8", errors="ignore"
            )
        except Exception:
            has_byte = False

        if has_byte and not tab.v153_partner.isChecked():
            tab.v153_status.setText(
                "ByteDance SeedAudio est présent, mais les nœuds API partenaires sont désactivés. "
                "Activez-les uniquement si vous acceptez l'usage de crédits."
            )
        elif not has_byte:
            tab.v153_status.setText(
                "Votre ComfyUI semble ancien : ByteDance SeedAudio n'est pas présent. "
                "Cliquez sur « Mettre à jour / réparer ComfyUI »."
            )
        else:
            tab.v153_status.setText(f"Diagnostic terminé · {problems} point(s) à vérifier.")

    tab.v153_diag.clicked.connect(diagnose)

    def show_free():
        table = tab.v153_free_table
        table.setVisible(not table.isVisible())
        if not table.isVisible():
            return
        table.setRowCount(len(FREE_CATALOG))
        for r, row in enumerate(FREE_CATALOG):
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(value))
        table.resizeColumnsToContents()

    tab.v153_free.clicked.connect(show_free)

    def repair():
        if tab.active:
            tab.v153_status.setText("Arrêtez d'abord l'opération en cours.")
            return
        try:
            root_dir, key, _python, hardware = tab.config()
            if key != "comfyui":
                idx = tab.choice.findData("comfyui")
                if idx >= 0:
                    tab.choice.setCurrentIndex(idx)
                root_dir, key, _python, hardware = tab.config()

            p = tools.paths(root_dir, "comfyui")
            if not p["source"].is_dir() or not p["python"].is_file():
                tab.v153_status.setText(
                    "ComfyUI n'est pas encore installé complètement. "
                    "Utilisez d'abord « Installer / reprendre »."
                )
                return

            git = shutil.which("git")
            if not git:
                tab.v153_status.setText("Git est requis pour mettre à jour ComfyUI.")
                return

            steps = [
                tools.command("Mettre à jour ComfyUI", git,
                              ["-C", p["source"], "pull", "--ff-only"], p["source"]),
                tools.command("Mettre à jour les dépendances ComfyUI", p["python"],
                              ["-m", "pip", "install", "-r", p["source"] / "requirements.txt"],
                              p["source"]),
            ]

            manager_req = p["source"] / "manager_requirements.txt"
            check_code = (
                "from pathlib import Path,subprocess,sys;"
                f"p=Path({str(manager_req)!r});"
                "print('manager_requirements',p.exists());"
                "subprocess.check_call([sys.executable,'-m','pip','install','-r',str(p)]) if p.exists() else None"
            )
            steps.append(
                tools.command("Installer / réparer ComfyUI Manager", p["python"],
                              ["-c", check_code], p["source"])
            )
            steps.append(tools.diagnostic_command(root_dir, "comfyui"))

            tab.acquire(root_dir, "comfyui")
            tab.begin(root_dir, "comfyui", hardware, "diagnostic", steps, False)
            tab.v153_status.setText("Mise à jour/réparation en cours…")
        except Exception as exc:
            tab.v153_status.setText("Réparation impossible : " + str(exc))

    tab.v153_repair.clicked.connect(repair)
    diagnose()
    window._v153_comfy_doctor = True
