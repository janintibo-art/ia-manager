"""Sources complémentaires v108 pour IA Manager.

Les sources sont volontairement ouvertes via leurs interfaces officielles.
Seule la recherche Hugging Face Spaces est intégrée directement.
"""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests

SOURCES = (
    dict(
        id="stability-matrix",
        name="Stability Matrix",
        category="Launcher / package manager",
        description="Installe et gère ComfyUI, Forge, InvokeAI, Fooocus, outils d'entraînement et modèles partagés.",
        url="https://github.com/LykosAI/StabilityMatrix",
        search_mode="open",
        local_first=True,
    ),
    dict(
        id="hf-spaces",
        name="Hugging Face Spaces",
        category="Applications IA",
        description="Répertoire d'applications Gradio, Docker et Static. Les Spaces publics peuvent servir de référence ou être clonés.",
        url="https://huggingface.co/spaces",
        search_mode="integrated",
        local_first=False,
    ),
    dict(
        id="comfy-registry",
        name="Comfy Registry",
        category="ComfyUI / custom nodes",
        description="Registre officiel des nœuds personnalisés ComfyUI.",
        url="https://registry.comfy.org/",
        search_mode="browser",
        local_first=True,
    ),
    dict(
        id="openmodeldb",
        name="OpenModelDB",
        category="Upscale / restauration",
        description="Catalogue communautaire de modèles d'upscale et restauration.",
        url="https://openmodeldb.info/",
        search_mode="browser",
        local_first=True,
    ),
)

HF_SPACES_API = "https://huggingface.co/api/spaces"


def source_by_id(source_id: str) -> Dict[str, Any]:
    return next((s for s in SOURCES if s["id"] == source_id), SOURCES[0])


def browser_search_url(source_id: str, query: str) -> str:
    q = quote_plus(str(query or "").strip())
    if source_id == "hf-spaces":
        return f"https://huggingface.co/search/full-text?q={q}&type=space"
    if source_id == "comfy-registry":
        return "https://registry.comfy.org/"
    if source_id == "openmodeldb":
        return "https://openmodeldb.info/"
    return source_by_id(source_id)["url"]


def search_hf_spaces(query: str, limit: int = 30, timeout: int = 20) -> List[Dict[str, Any]]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Saisissez un mot-clé pour rechercher les Spaces.")
    params = {"search": query, "limit": max(1, min(int(limit), 50)), "full": "true"}
    response = requests.get(HF_SPACES_API, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    result = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or item.get("_id") or "").strip()
        if not sid:
            continue
        card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
        result.append({
            "id": sid,
            "name": card.get("title") or sid.split("/")[-1],
            "author": sid.split("/")[0] if "/" in sid else "",
            "sdk": item.get("sdk") or card.get("sdk") or "",
            "likes": int(item.get("likes") or 0),
            "tags": [str(t) for t in (item.get("tags") or [])[:12]],
            "private": bool(item.get("private")),
            "url": "https://huggingface.co/spaces/" + sid,
            "clone_url": "https://huggingface.co/spaces/" + sid,
        })
    return result
