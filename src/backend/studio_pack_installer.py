"""Planificateur d'installation de packs v104.

Ce module ne lance aucun programme. Il détermine les moteurs qu'IA Manager sait
installer de façon contrôlée et conserve un état de reprise sérialisable.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from src.backend import creative_tools, studio_advisor

SCHEMA = 1
MANAGED = tuple(creative_tools.TOOLS.keys())

# Certains packs utilisent des alias de catalogue pour le même moteur géré.
TOOL_ALIASES = {
    "comfyui": "comfyui",
    "audiocraft": "audiocraft",
    "triposr": "triposr",
    "hunyuan3d": "hunyuan3d",
}

def build_plan(pack_id: str) -> Dict[str, Any]:
    pack = studio_advisor.pack_by_id(pack_id)
    managed: List[str] = []
    manual: List[str] = []
    for tool_id in pack.get("tools", ()):
        key = TOOL_ALIASES.get(tool_id)
        if key and key in creative_tools.TOOLS:
            if key not in managed:
                managed.append(key)
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
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        return {}
    pack_id = str(value.get("pack_id") or "")
    try:
        fresh = build_plan(pack_id)
    except Exception:
        return {}
    managed = [k for k in value.get("managed", []) if k in fresh["managed"]]
    # On garde l'ordre officiel du pack, pas un ordre potentiellement corrompu.
    managed = [k for k in fresh["managed"] if k in managed or k not in value.get("managed", [])]
    index = max(0, min(int(value.get("index") or 0), len(fresh["managed"])))
    fresh.update(index=index, state=str(value.get("state") or "prêt")[:40],
                 last_error=str(value.get("last_error") or "")[:500])
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

def python_kind(tool_key: str) -> str:
    return "py39" if tool_key == "audiocraft" else "py310"
