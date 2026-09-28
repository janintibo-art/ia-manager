"""Utilitaires locaux v105 installables dans des environnements séparés.

Aucune recette n'est exécutée par ce module : il produit uniquement des commandes
explicites sous forme programme + liste d'arguments, consommées par l'UI Qt.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

UTILITIES = {
    "ffmpeg": dict(
        name="FFmpeg privé", python="Python 3.10 ou 3.11", needs_git=False,
        note="Installe un binaire FFmpeg privé via imageio-ffmpeg. N'altère pas le FFmpeg système.",
        packages=("imageio-ffmpeg",), import_test="import imageio_ffmpeg",
    ),
    "rembg": dict(
        name="rembg", python="Python 3.10 ou 3.11", needs_git=False,
        note="Détourage local. Le premier usage peut récupérer un modèle U2Net si le cache ne le contient pas.",
        packages=("rembg[cli]", "onnxruntime"), import_test="import rembg, onnxruntime",
    ),
    "realesrgan": dict(
        name="Real-ESRGAN", python="Python 3.10 ou 3.11", needs_git=True,
        repo="https://github.com/xinntao/Real-ESRGAN.git",
        note="Upscale local. Les poids restent à télécharger séparément selon le modèle choisi.",
        packages=("basicsr", "facexlib", "gfpgan"), import_test="import realesrgan",
    ),
    "faster-whisper": dict(
        name="faster-whisper", python="Python 3.10 ou 3.11", needs_git=False,
        note="Transcription locale optimisée avec CTranslate2. Les poids Whisper restent séparés.",
        packages=("faster-whisper",), import_test="import faster_whisper",
    ),
    "demucs": dict(
        name="Demucs", python="Python 3.10 ou 3.11", needs_git=False,
        note="Séparation locale en stems. Les modèles sont récupérés lors du premier usage.",
        packages=("demucs",), import_test="import demucs",
    ),
    "chromadb": dict(
        name="ChromaDB", python="Python 3.10 ou 3.11", needs_git=False,
        note="Base vectorielle locale pour RAG.",
        packages=("chromadb",), import_test="import chromadb",
    ),
    "faiss": dict(
        name="FAISS CPU", python="Python 3.10 ou 3.11", needs_git=False,
        note="Recherche vectorielle CPU. La disponibilité de la roue Python dépend de la plateforme.",
        packages=("faiss-cpu",), import_test="import faiss",
    ),
}


def paths(root, key, windows=None):
    if key not in UTILITIES:
        raise ValueError("Utilitaire inconnu.")
    if not str(root).strip():
        raise ValueError("Choisissez un dossier d'installation.")
    base = Path(root).expanduser().resolve() / ("util_" + key.replace("-", "_"))
    windows = os.name == "nt" if windows is None else windows
    return {
        "base": base,
        "source": base / "source",
        "env": base / "venv",
        "python": base / "venv" / ("Scripts/python.exe" if windows else "bin/python"),
        "cache": base / "cache",
        "outputs": base / "resultats",
        "manifest": base / "ia_manager_utility.json",
        "log": base / "journal.log",
    }


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_manifest(root, key):
    p = paths(root, key)["manifest"]
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
        if value.get("managed_by") == "IA Manager" and value.get("utility") == key:
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def prepare(root, key):
    p = paths(root, key)
    if p["base"].exists() and any(p["base"].iterdir()) and not read_manifest(root, key):
        raise ValueError(
            "Ce dossier d'utilitaire contient des fichiers non gérés. "
            "Choisissez un autre dossier parent ; aucun fichier n'a été remplacé."
        )
    if p["source"].exists() and UTILITIES[key].get("repo") and not (p["source"] / ".git").is_dir():
        raise ValueError("Le dossier source est incomplet. Choisissez un nouveau dossier parent.")
    for name in ("base", "cache", "outputs"):
        p[name].mkdir(parents=True, exist_ok=True)
    write_json(p["manifest"], {
        "managed_by": "IA Manager", "utility": key, "state": "installation en cours"
    })
    return p


def command(label, program, args, cwd):
    return {"label": label, "program": str(program), "args": [str(a) for a in args], "cwd": str(cwd)}


def install_plan(root, key, python, git=None, windows=None):
    if key not in UTILITIES:
        raise ValueError("Utilitaire inconnu.")
    if not python:
        raise ValueError("Sélectionnez Python 3.10 ou 3.11.")
    tool = UTILITIES[key]
    if tool.get("needs_git") and not git:
        raise ValueError("Git est nécessaire pour cet utilitaire.")
    p = paths(root, key, windows)
    version = "sys.version_info[:2] in ((3,10),(3,11))"
    code = (
        "import sys; print(sys.version); assert " + version +
        ", 'Python 3.10 ou 3.11 requis'"
    )
    steps = [command("Vérifier Python", python, ["-c", code], p["base"])]
    if tool.get("repo") and not (p["source"] / ".git").is_dir():
        steps.append(command("Télécharger le code officiel", git,
                             ["clone", "--depth", "1", tool["repo"], p["source"]], p["base"]))
    steps.append(command("Créer l'environnement isolé", python, ["-m", "venv", p["env"]], p["base"]))
    exe = p["python"]
    steps.append(command("Préparer pip", exe,
                         ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], p["base"]))
    if key == "realesrgan":
        steps.append(command("Installer les dépendances Real-ESRGAN", exe,
                             ["-m", "pip", "install", *tool["packages"]], p["source"]))
        steps.append(command("Installer Real-ESRGAN", exe,
                             ["-m", "pip", "install", "-e", "."], p["source"]))
    else:
        steps.append(command("Installer " + tool["name"], exe,
                             ["-m", "pip", "install", *tool["packages"]], p["base"]))
    if key == "ffmpeg":
        copy_code = (
            "import imageio_ffmpeg,shutil,sys,pathlib;"
            "dst=pathlib.Path(sys.executable).parent/('ffmpeg.exe' if sys.platform=='win32' else 'ffmpeg');"
            "shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(),dst);print(dst)"
        )
        steps.append(command("Préparer le binaire FFmpeg privé", exe, ["-c", copy_code], p["base"]))
    steps.append(command("Contrôler les dépendances", exe, ["-m", "pip", "check"], p["base"]))
    steps.append(diagnostic_command(root, key, windows))
    return steps


def diagnostic_command(root, key, windows=None):
    p = paths(root, key, windows)
    test = UTILITIES[key]["import_test"]
    if key == "ffmpeg":
        test += "; import shutil; assert shutil.which('ffmpeg')"
    code = "import sys; print('Python',sys.version); " + test + "; print('Diagnostic OK')"
    return command("Diagnostic " + UTILITIES[key]["name"], p["python"], ["-c", code], p["base"])


def environment(root, key):
    p = paths(root, key)
    return {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "HF_HOME": str(p["cache"] / "huggingface"),
        "TORCH_HOME": str(p["cache"] / "torch"),
        "U2NET_HOME": str(p["cache"] / "rembg"),
        "PATH": str(p["python"].parent) + os.pathsep + os.environ.get("PATH", ""),
    }


def set_state(root, key, success):
    record = read_manifest(root, key) or {"managed_by": "IA Manager", "utility": key}
    record["state"] = "installé — prêt" if success else "installation incomplète"
    write_json(paths(root, key)["manifest"], record)
