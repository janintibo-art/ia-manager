"""v183 : assistants pour Stable Audio Open et TRELLIS."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from src.backend import audio_voice_installer, advanced_video3d_installer, settings


def stable_audio_status():
    spec = audio_voice_installer.spec_for("stable-audio-open")
    st = audio_voice_installer.state("stable-audio-open")
    access = audio_voice_installer.huggingface_access_status(spec["repo"])
    return {"engine": st, "access": access}


def save_hf_token(token: str):
    settings.set("huggingface_token", str(token or "").strip())


def trellis_status():
    p = advanced_video3d_installer.paths("trellis")
    wsl = shutil.which("wsl") or shutil.which("wsl.exe")
    nvidia = shutil.which("nvidia-smi") or shutil.which("nvidia-smi.exe")
    nvcc = shutil.which("nvcc") or shutil.which("nvcc.exe")
    installed_distros = []
    wsl2 = False
    if wsl:
        try:
            r = subprocess.run([wsl, "-l", "-v"], capture_output=True, text=True, timeout=20)
            text = (r.stdout or "") + "\n" + (r.stderr or "")
            for line in text.splitlines():
                clean = line.replace("\x00", "").strip()
                if clean and not clean.lower().startswith("name") and not clean.lower().startswith("windows"):
                    installed_distros.append(clean)
                if " 2" in clean or clean.endswith("2"):
                    wsl2 = True
        except Exception:
            pass
    return {
        "windows": os.name == "nt",
        "wsl": bool(wsl),
        "wsl_path": wsl or "",
        "wsl2": wsl2,
        "distros": installed_distros,
        "nvidia": nvidia or "",
        "nvcc": nvcc or "",
        "source": str(p["source"]),
        "source_ready": (p["source"] / ".git").is_dir(),
    }


def wsl_install_command():
    if os.name != "nt":
        raise ValueError("WSL2 concerne uniquement Windows.")
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")
    if not powershell:
        raise ValueError("PowerShell introuvable.")
    args = [
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "Start-Process wsl.exe -Verb RunAs -ArgumentList '--install -d Ubuntu' -Wait"
    ]
    return {"program": powershell, "args": args, "cwd": str(Path.home())}


def trellis_wsl_bootstrap_command():
    st = trellis_status()
    if not st["wsl"]:
        raise ValueError("Installez d'abord WSL2.")
    script = (
        "set -e\n"
        "sudo apt-get update\n"
        "sudo apt-get install -y git python3.10 python3.10-venv python3-pip build-essential ninja-build\n"
        "mkdir -p \"$HOME/ia-manager\"\n"
        "cd \"$HOME/ia-manager\"\n"
        "if [ ! -d TRELLIS/.git ]; then\n"
        "  git clone --recursive https://github.com/microsoft/TRELLIS.git\n"
        "else\n"
        "  cd TRELLIS\n"
        "  git pull --ff-only\n"
        "  git submodule update --init --recursive\n"
        "fi\n"
        "echo IA_MANAGER_TRELLIS_WSL_READY\n"
    )
    return {"program": st["wsl_path"], "args": ["bash", "-lc", script], "cwd": str(Path.home())}
