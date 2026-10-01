"""v184 : grand check-up visuel, navigation et suppression des doublons."""
from __future__ import annotations

from PyQt6.QtCore import QObject, QEvent, QTimer
from PyQt6.QtWidgets import QGroupBox, QPushButton


class _KeepHidden(QObject):
    """Empêche un ancien bloc technique de réapparaître après son propre refresh."""
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show:
            QTimer.singleShot(0, watched.hide)
        return False


def _dedupe_groups(groups):
    seen = set()
    cleaned = []
    for section, entries in groups:
        unique = []
        for entry in entries:
            attr = entry[0]
            if attr in seen:
                continue
            seen.add(attr)
            unique.append(entry)
        cleaned.append((section, tuple(unique)))
    return tuple(cleaned)


def _fix_navigation(window):
    from src.ui import v149_extension as nav

    groups = []
    for section, entries in nav.GROUPS:
        entries = [e for e in entries if e[0] not in {
            "audio_voice_install_tab", "advanced_video3d_tab", "final_blockers_tab"
        }]

        if section == "CRÉER":
            for entry in (
                ("audio_voice_install_tab", "Audio & Voix avancés", "Whisper, Kokoro, XTTS et Stable Audio."),
                ("advanced_video3d_tab", "Vidéo & 3D avancés", "CogVideoX, InstantMesh et TRELLIS."),
            ):
                if getattr(window, entry[0], None) is not None:
                    entries.append(entry)

        if section == "SYSTÈME" and getattr(window, "final_blockers_tab", None) is not None:
            entries.append((
                "final_blockers_tab",
                "Derniers blocages",
                "Accès Hugging Face et environnement TRELLIS/WSL2."
            ))

        groups.append((section, tuple(entries)))

    nav.GROUPS = _dedupe_groups(tuple(groups))

    # Le Mode Simple doit rester réellement simple.
    try:
        from src.ui import v165_extension as mode
        for attr in (
            "audio_voice_install_tab",
            "advanced_video3d_tab",
            "final_blockers_tab",
            "installation_audit_tab",
        ):
            mode.SIMPLE_ATTRS.discard(attr)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()

    try:
        from src.ui import v165_extension as mode
        from src.backend import settings
        mode._apply_navigation_mode(window, str(settings.get("interface_mode") or "advanced"))
    except Exception:
        pass


def _hide_legacy_media_blocks(window, keeper):
    tab = getattr(window, "media_studio_tab", None)
    if tab is None:
        return

    # v171/v172 restent utilisés par les panneaux 1-clic mais ne doivent plus
    # encombrer l'interface.
    for attr in ("v171_pack_box", "v172_weights_box"):
        box = getattr(tab, attr, None)
        if box is not None:
            box.installEventFilter(keeper)
            box.hide()

    managed = {
        "musicgen-small", "musicgen-melody", "audiogen",
        "wan21", "ltx-video", "triposr", "hunyuan3d",
    }

    quick_box = None
    for box in tab.findChildren(QGroupBox):
        if box.title() == "Démarrage rapide":
            quick_box = box
            break

    def refresh_visibility(*_args):
        model = getattr(tab, "current_model", None) or {}
        if quick_box is not None:
            quick_box.setVisible(str(model.get("id") or "") not in managed)
        for attr in ("v171_pack_box", "v172_weights_box"):
            legacy = getattr(tab, attr, None)
            if legacy is not None:
                legacy.hide()

    try:
        tab.models.currentItemChanged.connect(refresh_visibility)
    except Exception:
        pass
    refresh_visibility()


def _clean_image_page(window):
    tab = getattr(window, "image_studio_tab", None)
    if tab is None:
        return

    # Remplacés par le panneau ComfyUI intégré.
    obsolete = {
        "Installer ComfyUI",
        "Installer / démarrer les outils locaux",
    }
    for button in tab.findChildren(QPushButton):
        if button.text().strip() in obsolete:
            button.hide()


def _audit_runtime(window):
    audit = getattr(window, "installation_audit_tab", None)
    shell = getattr(window, "studio_shell", None)

    if audit is not None:
        try:
            audit.refresh()
            module = __import__("src.backend.installation_audit", fromlist=["summary"])
            s = module.summary()
            audit.details.setText(
                f"Check-up v184 : navigation nettoyée, doublons visuels masqués · "
                f"{s['automatic']} automatiques / {s['partial']} partiels / {s['todo']} à intégrer."
            )
        except Exception:
            pass

    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v184(window):
    if getattr(window, "_v184_final_cleanup", False):
        return

    keeper = _KeepHidden(window)
    window.v184_keep_hidden = keeper

    _fix_navigation(window)
    _hide_legacy_media_blocks(window, keeper)
    _clean_image_page(window)
    _audit_runtime(window)

    window._v184_final_cleanup = True
