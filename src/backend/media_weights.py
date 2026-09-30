"""Préchargement des poids AudioCraft / TripoSR / Hunyuan3D v172."""
from __future__ import annotations

import json
from pathlib import Path

from src.backend import creative_tools, settings


SPECS = {
    "musicgen-small": {
        "name": "MusicGen Small",
        "tool": "audiocraft",
        "note": "Télécharge à l'avance les poids officiels utilisés ensuite par AudioCraft.",
        "snapshots": [
            {"repo": "facebook/musicgen-small", "patterns": None},
        ],
    },
    "musicgen-melody": {
        "name": "MusicGen Melody",
        "tool": "audiocraft",
        "note": "Télécharge à l'avance le modèle Melody dans le cache Hugging Face d'AudioCraft.",
        "snapshots": [
            {"repo": "facebook/musicgen-melody", "patterns": None},
        ],
    },
    "audiogen": {
        "name": "AudioGen Medium",
        "tool": "audiocraft",
        "note": "Télécharge à l'avance le modèle AudioGen Medium dans le cache utilisé par AudioCraft.",
        "snapshots": [
            {"repo": "facebook/audiogen-medium", "patterns": None},
        ],
    },
    "triposr": {
        "name": "TripoSR",
        "tool": "triposr",
        "note": "Précharge config.yaml et model.ckpt depuis le dépôt officiel Stability AI.",
        "snapshots": [
            {"repo": "stabilityai/TripoSR", "patterns": ["config.yaml", "model.ckpt"]},
        ],
    },
    "hunyuan3d": {
        "name": "Hunyuan3D 2 Mini Turbo + texture",
        "tool": "hunyuan3d",
        "note": (
            "Précharge le modèle Mini Turbo utilisé par défaut par l'interface Hunyuan3D "
            "ainsi que les poids de texture. Le téléchargement est volumineux."
        ),
        "snapshots": [
            {
                "repo": "tencent/Hunyuan3D-2mini",
                "patterns": ["hunyuan3d-dit-v2-mini-turbo/*"],
            },
            {
                "repo": "tencent/Hunyuan3D-2",
                "patterns": [
                    "hunyuan3d-delight-v2-0/*",
                    "hunyuan3d-paint-v2-0-turbo/*",
                ],
            },
        ],
    },
}


def spec_for(model_id):
    return SPECS.get(str(model_id or ""))


def _root():
    return str(settings.get("creative_tools_root") or Path.home() / "IA Manager" / "Outils")


def engine_paths(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Ce modèle n'a pas de préparation automatique de poids.")
    return creative_tools.paths(_root(), spec["tool"])


def marker_path(model_id):
    p = engine_paths(model_id)
    return p["base"] / "weights" / (str(model_id) + ".json")


def state(model_id):
    spec = spec_for(model_id)
    if not spec:
        return {"supported": False, "installed": False, "ready": False, "state": "non pris en charge"}

    p = engine_paths(model_id)
    engine_record = creative_tools.read_manifest(_root(), spec["tool"])
    engine_installed = str(engine_record.get("state") or "").startswith("installé")
    marker = marker_path(model_id)
    ready = engine_installed and marker.is_file()
    return {
        "supported": True,
        "installed": engine_installed,
        "ready": ready,
        "state": "poids prêts" if ready else ("moteur installé, poids à préparer" if engine_installed else "moteur non installé"),
        "marker": str(marker),
        "tool": spec["tool"],
        "name": spec["name"],
        "note": spec["note"],
    }


def prepare_command(model_id):
    spec = spec_for(model_id)
    if not spec:
        raise ValueError("Ce modèle n'a pas de préparation automatique de poids.")

    p = engine_paths(model_id)
    if not p["python"].is_file() or not p["source"].is_dir():
        raise ValueError("Installez d'abord le moteur recommandé dans Outils locaux.")

    marker = marker_path(model_id)
    marker.parent.mkdir(parents=True, exist_ok=True)

    snapshots_json = json.dumps(spec["snapshots"], ensure_ascii=False)
    marker_json = json.dumps(str(marker), ensure_ascii=False)
    model_json = json.dumps(str(model_id), ensure_ascii=False)

    code = f"""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

snapshots = json.loads({json.dumps(snapshots_json)})
marker = Path({marker_json})
model_id = {model_json}

for index, item in enumerate(snapshots, 1):
    repo = item["repo"]
    patterns = item.get("patterns")
    print(f"SNAPSHOT {{index}}/{{len(snapshots)}} : {{repo}}", flush=True)
    kwargs = dict(repo_id=repo, resume_download=True)
    if patterns:
        kwargs["allow_patterns"] = patterns
    path = snapshot_download(**kwargs)
    print("OK : " + str(path), flush=True)

marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text(json.dumps({{"model": model_id, "snapshots": snapshots}}, ensure_ascii=False, indent=2), encoding="utf-8")
print("IA_MANAGER_WEIGHTS_READY=" + str(marker), flush=True)
"""

    return {
        "program": str(p["python"]),
        "args": ["-u", "-c", code],
        "cwd": str(p["source"]),
        "env": creative_tools.environment(_root(), spec["tool"], offline=False),
    }
