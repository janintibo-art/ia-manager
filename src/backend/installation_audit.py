"""Audit v184 des modèles/outils : niveau d'intégration dans IA Manager."""
from __future__ import annotations

from typing import Dict, List
from src.backend import studio_catalog

# Modèles pour lesquels le parcours d'installation/lancement est réellement intégré.
FULL = {
    "qwen25-coder-7b", "qwen25-coder-14b", "qwen25-coder-32b",
    "deepseek-coder-v2-lite", "qwen25-14b", "mistral-small",
    "sdxl-base", "flux-schnell", "flux-dev", "sd35-medium", "controlnet", "ip-adapter",
    "musicgen-small", "musicgen-melody", "audiogen", "whisper-large-v3", "kokoro", "xtts-v2",
    "wan21-t2v", "ltx-video", "cogvideox-2b",
    "triposr", "hunyuan3d2", "instantmesh",
    "qwen2-vl-7b", "llava", "bge-m3", "nomic-embed",
}

# Modèles présents dans le catalogue mais dont l'installation n'est pas encore
# entièrement automatisée de bout en bout.
PARTIAL = {
    "stable-audio-open",
    "trellis",
}

ROUTE = {
    "Texte & code": "models",
    "Vision": "models",
    "Documents & RAG": "models",
    "Image": "image",
    "Audio & musique": "media",
    "Voix": "audio_voice",
    "Vidéo": "media",
    "3D": "media",
}

DIRECT_ROUTE = {
    "stable-audio-open": "final_blockers",
    "whisper-large-v3": "audio_voice",
    "kokoro": "audio_voice",
    "xtts-v2": "audio_voice",
    "cogvideox-2b": "advanced_video3d",
    "instantmesh": "advanced_video3d",
    "trellis": "final_blockers",
}


def level(model_id: str) -> str:
    if model_id in FULL:
        return "automatic"
    if model_id in PARTIAL:
        return "partial"
    return "todo"


def rows() -> List[Dict]:
    output = []
    for model in studio_catalog.MODELS:
        lvl = level(model["id"])
        output.append({
            "id": model["id"],
            "name": model["name"],
            "category": model["category"],
            "engine": model["engine"],
            "level": lvl,
            "route": DIRECT_ROUTE.get(model["id"], ROUTE.get(model["category"], "search")),
            "url": model.get("url", ""),
        })
    return output


def summary() -> Dict[str, int]:
    result = {"automatic": 0, "partial": 0, "todo": 0}
    for row in rows():
        result[row["level"]] += 1
    return result


def next_targets() -> List[Dict]:
    """Priorité : modèles partiels, puis non intégrés."""
    order = {"partial": 0, "todo": 1, "automatic": 2}
    return sorted(rows(), key=lambda r: (order[r["level"]], r["category"], r["name"]))
