"""Installateurs isolés v181 pour Audio / Voix avancés."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from src.backend import settings


SPECS = {
    "stable-audio-open": {
        "name": "Stable Audio Open 1.0",
        "python": (3, 10),
        "packages": ["stable-audio-tools[ui]", "huggingface_hub"],
        "repo": "stabilityai/stable-audio-open-1.0",
        "note": (
            "Moteur local Stable Audio Tools. Le modèle Hugging Face est soumis à une validation "
            "d'accès : l'installation du moteur est automatique, mais le téléchargement des poids "
            "nécessite un compte Hugging Face autorisé."
        ),
        "gated": True,
    },
    "whisper-large-v3": {
        "name": "Whisper large-v3",
        "python": (3, 11),
        "packages": [
            "transformers>=4.46", "accelerate", "safetensors",
            "soundfile", "huggingface_hub", "torch", "torchaudio"
        ],
        "repo": "openai/whisper-large-v3",
        "note": "Transcription multilingue locale via Transformers.",
        "gated": False,
    },
    "kokoro": {
        "name": "Kokoro 82M",
        "python": (3, 11),
        "packages": ["kokoro>=0.9.4", "soundfile", "huggingface_hub"],
        "repo": "hexgrad/Kokoro-82M",
        "note": "Synthèse vocale légère. Sous Windows, eSpeak NG est installé via WinGet si disponible.",
        "gated": False,
        "winget": "eSpeak-NG.eSpeak-NG",
    },
    "xtts-v2": {
        "name": "XTTS-v2",
        "python": (3, 11),
        "packages": ["coqui-tts", "huggingface_hub"],
        "repo": "coqui/XTTS-v2",
        "note": "Synthèse vocale multilingue et clonage de voix via Coqui TTS.",
        "gated": False,
    },
}


def spec_for(model_id):
    return SPECS.get(str(model_id or ""))


def root_dir():
    parent = str(settings.get("creative_tools_root") or Path.home() / "IA Manager" / "Outils")
    return Path(parent).expanduser().resolve() / "audio_voice"


def paths(model_id):
    if model_id not in SPECS:
        raise ValueError("Modèle Audio/Voix inconnu.")
    base = root_dir() / model_id
    env = base / "venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return {
        "base": base,
        "env": env,
        "python": python,
        "cache": base / "cache",
        "marker": base / "ia_manager_model.json",
    }


def _candidate_pythons():
    candidates = []
    py = shutil.which("py")
    if py:
        candidates.append(("launcher", py))
    for name in ("python", "python3", "python.exe"):
        hit = shutil.which(name)
        if hit:
            candidates.append(("exe", hit))
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        for folder in ("Python310", "Python311"):
            p = Path(local) / "Programs" / "Python" / folder / "python.exe"
            if p.is_file():
                candidates.append(("exe", str(p)))
    return candidates


def _version_of(exe, launcher_version=None):
    try:
        if launcher_version:
            cmd = [exe, f"-{launcher_version[0]}.{launcher_version[1]}", "-c", "import sys;print(sys.executable);print(sys.version_info[0],sys.version_info[1])"]
        else:
            cmd = [exe, "-c", "import sys;print(sys.executable);print(sys.version_info[0],sys.version_info[1])"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return None
        lines = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        if len(lines) < 2:
            return None
        major, minor = [int(x) for x in lines[-1].split()[:2]]
        return lines[0], (major, minor)
    except Exception:
        return None


def resolve_python(model_id):
    spec = spec_for(model_id)
    wanted = tuple(spec["python"])
    for kind, exe in _candidate_pythons():
        result = _version_of(exe, wanted if kind == "launcher" else None)
        if result and result[1] == wanted:
            return result[0]
    return ""


def state(model_id):
    spec = spec_for(model_id)
    if not spec:
        return {"supported": False}
    p = paths(model_id)
    installed = p["python"].is_file()
    ready = False
    marker_data = {}
    try:
        marker_data = json.loads(p["marker"].read_text(encoding="utf-8"))
        ready = bool(marker_data.get("weights_ready"))
    except Exception:
        pass
    return {
        "supported": True,
        "installed": installed,
        "ready": installed and ready,
        "python": str(p["python"]) if installed else resolve_python(model_id),
        "base": str(p["base"]),
        "name": spec["name"],
        "note": spec["note"],
        "gated": bool(spec.get("gated")),
    }


def _cmd(label, program, args, cwd):
    return {"label": label, "program": str(program), "args": [str(x) for x in args], "cwd": str(cwd)}


def install_plan(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Modèle inconnu.")
    source_python = resolve_python(model_id)
    if not source_python:
        wanted = ".".join(map(str, spec["python"]))
        raise ValueError(f"Python {wanted} est requis. Installez-le depuis le Centre d'installation.")

    p = paths(model_id)
    p["base"].mkdir(parents=True, exist_ok=True)
    p["cache"].mkdir(parents=True, exist_ok=True)

    steps = []
    if spec.get("winget") and os.name == "nt":
        winget = shutil.which("winget")
        if winget:
            steps.append(_cmd(
                "Installer eSpeak NG",
                winget,
                ["install", "--id", spec["winget"], "--exact", "--source", "winget",
                 "--accept-source-agreements", "--accept-package-agreements",
                 "--disable-interactivity"],
                p["base"],
            ))

    if not p["python"].is_file():
        steps.append(_cmd("Créer l'environnement isolé", source_python, ["-m", "venv", p["env"]], p["base"]))

    steps.append(_cmd("Mettre pip à jour", p["python"], ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], p["base"]))
    steps.append(_cmd("Installer le moteur et ses dépendances", p["python"], ["-m", "pip", "install", *spec["packages"]], p["base"]))

    verify_code = {
        "stable-audio-open": "import stable_audio_tools, huggingface_hub; print('Stable Audio Tools OK')",
        "whisper-large-v3": "import transformers, torch, huggingface_hub; print('Whisper runtime OK')",
        "kokoro": "import kokoro, soundfile, huggingface_hub; print('Kokoro runtime OK')",
        "xtts-v2": "import TTS, huggingface_hub; print('Coqui TTS runtime OK')",
    }[model_id]
    steps.append(_cmd("Vérifier le moteur", p["python"], ["-c", verify_code], p["base"]))
    return steps


def preload_command(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Modèle inconnu.")
    p = paths(model_id)
    if not p["python"].is_file():
        raise ValueError("Installez d'abord le moteur.")

    marker = p["marker"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    repo = json.dumps(spec["repo"])
    marker_json = json.dumps(str(marker))
    cache_json = json.dumps(str(p["cache"]))
    gated = bool(spec.get("gated"))

    code = f"""
import json, os
from pathlib import Path
from huggingface_hub import snapshot_download

repo = {repo}
marker = Path({marker_json})
cache_dir = {cache_json}

try:
    path = snapshot_download(repo_id=repo, cache_dir=cache_dir)
except Exception as exc:
    msg = str(exc)
    if {gated!r}:
        raise RuntimeError(
            "Accès Hugging Face requis pour ce modèle. Acceptez sa licence/autorisation "
            "sur Hugging Face et configurez votre jeton, puis relancez. Détail : " + msg
        )
    raise

marker.write_text(json.dumps({{
    "model": repo,
    "weights_ready": True,
    "cache": str(path),
}}, ensure_ascii=False, indent=2), encoding="utf-8")
print("IA_MANAGER_READY=" + str(path), flush=True)
"""
    cmd = _cmd("Précharger les poids", p["python"], ["-u", "-c", code], p["base"])
    token = huggingface_token()
    if token:
        cmd["env"] = {"HF_TOKEN": token, "HUGGING_FACE_HUB_TOKEN": token}
    return cmd


def diagnostic_command(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Modèle inconnu.")
    p = paths(model_id)
    if not p["python"].is_file():
        raise ValueError("Moteur non installé.")
    code = "import sys; print(sys.version); print('Python', sys.executable)"
    return _cmd("Diagnostic Python", p["python"], ["-c", code], p["base"])


def huggingface_token():
    return str(settings.get("huggingface_token") or "").strip()


def huggingface_access_status(repo_id: str):
    """Vérifie l'accès au dépôt sans télécharger les poids."""
    import requests
    token = huggingface_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.get(
            "https://huggingface.co/api/models/" + str(repo_id),
            headers=headers,
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json() if "application/json" in r.headers.get("content-type", "") else {}
            return {
                "ok": True,
                "gated": bool(data.get("gated")),
                "token": bool(token),
                "message": "Accès Hugging Face valide.",
            }
        if r.status_code in (401, 403):
            return {
                "ok": False,
                "gated": True,
                "token": bool(token),
                "message": "Accès refusé : acceptez les conditions du modèle et vérifiez le jeton Hugging Face.",
            }
        return {
            "ok": False,
            "gated": False,
            "token": bool(token),
            "message": "Hugging Face répond avec le code " + str(r.status_code) + ".",
        }
    except Exception as exc:
        return {"ok": False, "gated": False, "token": bool(token), "message": str(exc)}
