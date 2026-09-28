"""Planificateur d'installation de packs v105.

Deux familles sont distinguées :
- engine:<clé> : moteurs lourds gérés par Outils locaux ;
- utility:<clé> : utilitaires v105 installés dans un venv séparé.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.backend import creative_tools, local_utilities, studio_advisor
from src.backend.studio_pack_v105 import extend_packs_v105

extend_packs_v105()

SCHEMA = 2

ENGINE_ALIASES = {
    "comfyui": "comfyui",
    "audiocraft": "audiocraft",
    "triposr": "triposr",
    "hunyuan3d": "hunyuan3d",
}
UTILITY_ALIASES = {
    "ffmpeg": "ffmpeg",
    "rembg": "rembg",
    "realesrgan": "realesrgan",
    "faster-whisper": "faster-whisper",
    "demucs": "demucs",
    "chromadb": "chromadb",
    "faiss": "faiss",
}


def token(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def split_token(value: str):
    if ":" not in str(value):
        return "engine", str(value)
    kind, key = str(value).split(":", 1)
    return kind, key


def build_plan(pack_id: str) -> Dict[str, Any]:
    pack = studio_advisor.pack_by_id(pack_id)
    managed: List[str] = []
    manual: List[str] = []
    for tool_id in pack.get("tools", ()):
        if tool_id in ENGINE_ALIASES and ENGINE_ALIASES[tool_id] in creative_tools.TOOLS:
            entry = token("engine", ENGINE_ALIASES[tool_id])
            if entry not in managed:
                managed.append(entry)
        elif tool_id in UTILITY_ALIASES and UTILITY_ALIASES[tool_id] in local_utilities.UTILITIES:
            entry = token("utility", UTILITY_ALIASES[tool_id])
            if entry not in managed:
                managed.append(entry)
        elif tool_id not in manual:
            manual.append(tool_id)
    return {
        "schema": SCHEMA,
        "pack_id": pack["id"],
        "pack_name": pack["name"],
        "managed": managed,
        "manual": manual,
        "index": 0,
        "state": "prêt",
        "last_error": "",
    }


def sanitize(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    pack_id = str(value.get("pack_id") or "")
    if not pack_id:
        return {}
    try:
        fresh = build_plan(pack_id)
    except Exception:
        return {}
    # Migration v104 -> v105 : on repart au premier item non installé,
    # les manifests servent de source de vérité et permettent de sauter le reste.
    if value.get("schema") not in (1, SCHEMA):
        return {}
    index = 0 if value.get("schema") == 1 else max(
        0, min(int(value.get("index") or 0), len(fresh["managed"]))
    )
    fresh.update(
        index=index,
        state=str(value.get("state") or "prêt")[:40],
        last_error=str(value.get("last_error") or "")[:500],
    )
    return fresh


def current_key(plan: Dict[str, Any]):
    index = int(plan.get("index") or 0)
    items = plan.get("managed") or []
    return items[index] if 0 <= index < len(items) else None


def advance(plan: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(plan)
    result["index"] = min(len(result.get("managed") or []), int(result.get("index") or 0) + 1)
    result["state"] = "terminé" if result["index"] >= len(result.get("managed") or []) else "prêt"
    result["last_error"] = ""
    return result


def mark_error(plan: Dict[str, Any], message: str) -> Dict[str, Any]:
    result = dict(plan)
    result["state"] = "erreur"
    result["last_error"] = str(message)[:500]
    return result


def reset(plan: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(plan)
    result.update(index=0, state="prêt", last_error="")
    return result


def python_kind(entry: str) -> str:
    kind, key = split_token(entry)
    if kind == "engine" and key == "audiocraft":
        return "py39"
    return "py310"


def display(entry: str) -> str:
    kind, key = split_token(entry)
    if kind == "engine":
        return creative_tools.TOOLS[key]["name"]
    return local_utilities.UTILITIES[key]["name"]
