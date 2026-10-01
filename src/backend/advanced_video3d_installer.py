"""Installateurs v182 : CogVideoX-2B, InstantMesh et diagnostic TRELLIS."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from src.backend import settings


SPECS = {
    "cogvideox-2b": {
        "name": "CogVideoX-2B",
        "kind": "diffusers",
        "python": (3, 11),
        "repo": "zai-org/CogVideoX-2b",
        "packages": [
            "torch", "torchvision", "torchaudio",
            "diffusers>=0.31", "transformers>=4.46", "accelerate",
            "sentencepiece", "safetensors", "imageio[ffmpeg]",
            "huggingface_hub",
        ],
        "note": "Pipeline Diffusers officiel. Le modèle complet représente environ 13,8 Go.",
    },
    "instantmesh": {
        "name": "InstantMesh",
        "kind": "git",
        "python": (3, 10),
        "repo_git": "https://github.com/TencentARC/InstantMesh.git",
        "packages_before": [
            "torch==2.1.0", "torchvision==0.16.0", "torchaudio==2.1.0",
        ],
        "torch_index": "https://download.pytorch.org/whl/cu121",
        "packages_after": [
            "xformers==0.0.22.post7", "ninja",
        ],
        "note": "Installation officielle Python 3.10 / PyTorch 2.1 / CUDA 12.1. Les poids sont récupérés au premier lancement.",
    },
    "trellis": {
        "name": "TRELLIS",
        "kind": "guided",
        "python": (3, 10),
        "repo_git": "https://github.com/microsoft/TRELLIS.git",
        "note": (
            "TRELLIS reste recommandé sous Linux/WSL2. Sous Windows natif, plusieurs extensions CUDA "
            "sont difficiles à compiler ; IA Manager fournit donc diagnostic et préparation guidée."
        ),
    },
}


def spec_for(model_id):
    return SPECS.get(str(model_id or ""))


def root_dir():
    parent = str(settings.get("creative_tools_root") or Path.home() / "IA Manager" / "Outils")
    return Path(parent).expanduser().resolve() / "advanced_video_3d"


def paths(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Modèle inconnu.")
    base = root_dir() / model_id
    env = base / "venv"
    py = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return {
        "base": base,
        "source": base / "source",
        "env": env,
        "python": py,
        "cache": base / "cache",
        "marker": base / "ia_manager_model.json",
    }


def _which_python(wanted):
    launcher = shutil.which("py")
    if launcher:
        try:
            r = subprocess.run(
                [launcher, f"-{wanted[0]}.{wanted[1]}", "-c", "import sys;print(sys.executable)"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().splitlines()[-1]
        except Exception:
            pass
    for exe in filter(None, [shutil.which("python"), shutil.which("python3")]):
        try:
            r = subprocess.run(
                [exe, "-c", "import sys;print(sys.version_info[0],sys.version_info[1]);print(sys.executable)"],
                capture_output=True, text=True, timeout=10
            )
            lines = [x.strip() for x in r.stdout.splitlines() if x.strip()]
            if r.returncode == 0 and len(lines) >= 2:
                major, minor = map(int, lines[0].split()[:2])
                if (major, minor) == tuple(wanted):
                    return lines[1]
        except Exception:
            pass
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        p = Path(local) / "Programs" / "Python" / f"Python{wanted[0]}{wanted[1]}" / "python.exe"
        if p.is_file():
            return str(p)
    return ""


def _marker(model_id, **extra):
    p = paths(model_id)
    p["marker"].parent.mkdir(parents=True, exist_ok=True)
    data = {"model": model_id, **extra}
    p["marker"].write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def state(model_id):
    spec = spec_for(model_id)
    if not spec:
        return {"supported": False}
    p = paths(model_id)
    installed = p["python"].is_file() if spec["kind"] != "guided" else p["source"].is_dir()
    ready = False
    try:
        data = json.loads(p["marker"].read_text(encoding="utf-8"))
        ready = bool(data.get("ready"))
    except Exception:
        pass
    return {
        "supported": True,
        "installed": installed,
        "ready": ready,
        "kind": spec["kind"],
        "name": spec["name"],
        "note": spec["note"],
        "python": str(p["python"]) if p["python"].is_file() else _which_python(spec["python"]),
        "base": str(p["base"]),
    }


def _cmd(label, program, args, cwd):
    return {"label": label, "program": str(program), "args": [str(x) for x in args], "cwd": str(cwd)}


def install_plan(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Modèle inconnu.")
    p = paths(model_id)
    p["base"].mkdir(parents=True, exist_ok=True)
    p["cache"].mkdir(parents=True, exist_ok=True)

    if spec["kind"] == "guided":
        git = shutil.which("git")
        if not git:
            raise ValueError("Git est requis.")
        steps = []
        if not (p["source"] / ".git").is_dir():
            steps.append(_cmd(
                "Cloner TRELLIS avec ses sous-modules",
                git,
                ["clone", "--recursive", spec["repo_git"], str(p["source"])],
                p["base"],
            ))
        code = (
            "import platform,shutil; "
            "print('Systeme',platform.system(),platform.release()); "
            "print('WSL', 'microsoft' in platform.release().lower()); "
            "print('nvidia-smi', shutil.which('nvidia-smi')); "
            "print('nvcc', shutil.which('nvcc'))"
        )
        py = _which_python(spec["python"]) or shutil.which("python") or shutil.which("py")
        if py:
            steps.append(_cmd("Diagnostic plateforme TRELLIS", py, ["-c", code], p["base"]))
        return steps

    source_python = _which_python(spec["python"])
    if not source_python:
        wanted = ".".join(map(str, spec["python"]))
        raise ValueError(f"Python {wanted} est requis. Installez-le depuis le Centre d'installation.")

    steps = []
    if spec["kind"] == "git":
        git = shutil.which("git")
        if not git:
            raise ValueError("Git est requis pour InstantMesh.")
        if not (p["source"] / ".git").is_dir():
            steps.append(_cmd("Télécharger InstantMesh", git, ["clone", "--depth", "1", spec["repo_git"], str(p["source"])], p["base"]))

    if not p["python"].is_file():
        steps.append(_cmd("Créer l'environnement isolé", source_python, ["-m", "venv", p["env"]], p["base"]))

    steps.append(_cmd("Mettre pip à jour", p["python"], ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], p["base"]))

    if model_id == "cogvideox-2b":
        steps.append(_cmd("Installer CogVideoX / Diffusers", p["python"], ["-m", "pip", "install", *spec["packages"]], p["base"]))
        verify = "import diffusers,transformers,torch;print('CogVideoX runtime OK',torch.cuda.is_available())"
        steps.append(_cmd("Vérifier le moteur", p["python"], ["-c", verify], p["base"]))
    elif model_id == "instantmesh":
        steps.append(_cmd(
            "Installer PyTorch CUDA 12.1",
            p["python"],
            ["-m", "pip", "install", *spec["packages_before"], "--index-url", spec["torch_index"]],
            p["source"],
        ))
        steps.append(_cmd("Installer xformers / Ninja", p["python"], ["-m", "pip", "install", *spec["packages_after"]], p["source"]))
        steps.append(_cmd("Installer les dépendances InstantMesh", p["python"], ["-m", "pip", "install", "-r", "requirements.txt"], p["source"]))
        verify = "import torch,gradio,diffusers;print('InstantMesh runtime OK',torch.cuda.is_available())"
        steps.append(_cmd("Vérifier InstantMesh", p["python"], ["-c", verify], p["source"]))
    return steps


def prepare_command(model_id):
    spec = spec_for(model_id)
    p = paths(model_id)
    if spec["kind"] == "guided":
        raise ValueError("TRELLIS reste guidé : utilisez le diagnostic et suivez la configuration WSL2/Linux.")
    if not p["python"].is_file():
        raise ValueError("Installez d'abord le moteur.")

    if model_id == "cogvideox-2b":
        repo = json.dumps(spec["repo"])
        cache = json.dumps(str(p["cache"]))
        marker = json.dumps(str(p["marker"]))
        code = f"""
import json
from pathlib import Path
from huggingface_hub import snapshot_download
repo={repo}
cache={cache}
marker=Path({marker})
path=snapshot_download(repo_id=repo, cache_dir=cache)
marker.write_text(json.dumps({{"model":"cogvideox-2b","ready":True,"cache":str(path)}},ensure_ascii=False,indent=2),encoding="utf-8")
print("IA_MANAGER_READY="+str(path))
"""
        return _cmd("Télécharger CogVideoX-2B", p["python"], ["-u", "-c", code], p["base"])

    if model_id == "instantmesh":
        marker = json.dumps(str(p["marker"]))
        code = f"""
import json
from pathlib import Path
from huggingface_hub import snapshot_download
repos=["TencentARC/InstantMesh","sudo-ai/zero123plus-v1.2"]
done=[]
for repo in repos:
    try:
        done.append(str(snapshot_download(repo_id=repo)))
    except Exception as exc:
        print("Préchargement facultatif impossible pour",repo,":",exc,flush=True)
marker=Path({marker})
marker.write_text(json.dumps({{"model":"instantmesh","ready":True,"cache":done}},ensure_ascii=False,indent=2),encoding="utf-8")
print("IA_MANAGER_READY="+str(marker))
"""
        return _cmd("Précharger les poids InstantMesh", p["python"], ["-u", "-c", code], p["source"])

    raise ValueError("Préparation inconnue.")


def launch_command(model_id):
    spec = spec_for(model_id)
    p = paths(model_id)
    if model_id == "instantmesh":
        if not p["python"].is_file():
            raise ValueError("InstantMesh n'est pas installé.")
        return _cmd("Démarrer InstantMesh", p["python"], ["app.py"], p["source"])
    raise ValueError("Ce moteur n'a pas encore d'interface locale lancée directement par IA Manager.")
