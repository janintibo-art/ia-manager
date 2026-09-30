"""Centre d'installation v170 : audit et installation guidée des prérequis Windows."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, List

from src.backend import settings, creative_tools
from src.backend import pinokio_integration


def _which(*names):
    for name in names:
        hit = shutil.which(name)
        if hit:
            return hit
    return ""


def _exists(*paths):
    for value in paths:
        if value and Path(value).expanduser().is_file():
            return str(Path(value).expanduser())
    return ""


def winget_path():
    return _which("winget", "winget.exe")


def detection() -> Dict[str, str]:
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    out = {
        "ollama": _which("ollama", "ollama.exe") or _exists(Path(local)/"Programs"/"Ollama"/"ollama.exe"),
        "git": _which("git", "git.exe") or _exists(Path(program_files)/"Git"/"cmd"/"git.exe"),
        "gh": _which("gh", "gh.exe") or _exists(Path(program_files)/"GitHub CLI"/"gh.exe"),
        "node": _which("node", "node.exe") or _exists(Path(program_files)/"nodejs"/"node.exe"),
        "npm": pinokio_integration.npm_path() or _which("npm", "npm.cmd", "npm.exe"),
        "pterm": pinokio_integration.pterm_path() or "",
        "python": _which("python", "python.exe", "py", "py.exe"),
        "blender": _which("blender", "blender.exe"),
    }
    # Cherche quelques emplacements Blender courants sans dépendre du registre.
    if not out["blender"]:
        base = Path(program_files)/"Blender Foundation"
        if base.is_dir():
            candidates = sorted(base.glob("Blender */blender.exe"), reverse=True)
            if candidates:
                out["blender"] = str(candidates[0])
    # ComfyUI installé par IA Manager.
    root = str(settings.get("creative_tools_root") or "").strip()
    comfy = ""
    if root:
        try:
            source = creative_tools.paths(root, "comfyui")["source"]
            if (source/"main.py").is_file():
                comfy = str(source)
        except Exception:
            pass
    out["comfyui"] = comfy
    try:
        out["pinokio_running"] = "oui" if pinokio_integration.local_status().get("running") else ""
    except Exception:
        out["pinokio_running"] = ""
    return out


COMPONENTS = (
    dict(id="ollama", name="Ollama", kind="winget", package="Ollama.Ollama", detect="ollama",
         role="Chat et modèles locaux", fallback="https://ollama.com/download/windows"),
    dict(id="git", name="Git", kind="winget", package="Git.Git", detect="git",
         role="Dépôts et installations d'outils", fallback="https://git-scm.com/download/win"),
    dict(id="gh", name="GitHub CLI", kind="winget", package="GitHub.cli", detect="gh",
         role="GitHub depuis IA Manager", fallback="https://cli.github.com/"),
    dict(id="node", name="Node.js LTS", kind="winget", package="OpenJS.NodeJS.LTS", detect="node",
         role="Prérequis de pterm / Pinokio", fallback="https://nodejs.org/"),
    dict(id="pterm", name="pterm", kind="npm", package="pterm", detect="pterm",
         role="Téléchargement et lancement des apps Pinokio", fallback="https://github.com/pinokiocomputer/pterm"),
    dict(id="python", name="Python 3.11", kind="winget", package="Python.Python.3.11", detect="python",
         role="Moteurs créatifs locaux", fallback="https://www.python.org/downloads/windows/"),
    dict(id="blender", name="Blender", kind="winget", package="BlenderFoundation.Blender", detect="blender",
         role="3D, conversion, rig et export", fallback="https://www.blender.org/download/"),
    dict(id="comfyui", name="ComfyUI", kind="internal", package="", detect="comfyui",
         role="Images et workflows vidéo", fallback="https://www.comfy.org/download"),
    dict(id="pinokio", name="Pinokio", kind="manual", package="", detect="pinokio_running",
         role="Catalogue d'applications IA locales", fallback="https://pinokio.computer/"),
)


def status_rows() -> List[Dict[str, str]]:
    found = detection()
    rows = []
    for item in COMPONENTS:
        value = found.get(item["detect"], "")
        rows.append({**item, "installed": bool(value), "path": value})
    return rows


def install_command(component_id: str):
    item = next((x for x in COMPONENTS if x["id"] == component_id), None)
    if not item:
        raise ValueError("Composant inconnu.")
    if item["kind"] == "winget":
        exe = winget_path()
        if not exe:
            raise ValueError("WinGet n'est pas disponible sur ce PC.")
        return {"program": exe, "args": ["install", "--id", item["package"], "--exact", "--source", "winget",
                                                "--accept-source-agreements", "--accept-package-agreements"]}
    if item["kind"] == "npm":
        npm = pinokio_integration.npm_path()
        if not npm:
            raise ValueError("Node.js/npm doit être installé avant pterm.")
        return {"program": npm, "args": ["install", "-g", item["package"]]}
    raise ValueError("Ce composant utilise une installation interne ou manuelle.")
