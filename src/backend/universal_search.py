"""Recherche universelle v109.

Normalise les résultats de plusieurs catalogues déjà intégrés à IA Manager.
Chaque source peut être interrogée indépendamment afin qu'une panne n'empêche
pas les autres sources de répondre.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.backend import extra_sources, model_search, pinokio_integration

SOURCES = (
    ("huggingface", "Hugging Face GGUF"),
    ("hf-spaces", "Hugging Face Spaces"),
    ("pinokio", "Pinokio"),
    ("github", "GitHub"),
    ("civitai", "Civitai"),
    ("modelscope", "ModelScope"),
)

TYPE_FILTERS = (
    "Tous",
    "Texte & code",
    "Image",
    "Audio & musique",
    "Vidéo",
    "3D",
    "Voix",
    "RAG / documents",
    "Application / outil",
)

TYPE_KEYWORDS = {
    "Texte & code": ("llm", "language", "chat", "coder", "code", "reasoning", "qwen", "llama", "mistral", "gemma", "gguf"),
    "Image": ("image", "stable diffusion", "sdxl", "flux", "comfy", "lora", "checkpoint", "upscale", "super-resolution"),
    "Audio & musique": ("audio", "music", "sound", "musicgen", "demucs", "stem", "song"),
    "Vidéo": ("video", "wan", "ltx", "cogvideo", "frame", "interpolation"),
    "3D": ("3d", "mesh", "blender", "triposr", "hunyuan3d", "trellis", "gaussian"),
    "Voix": ("voice", "tts", "speech", "whisper", "rvc", "bark", "xtts"),
    "RAG / documents": ("rag", "embedding", "vector", "document", "ocr", "retrieval", "chroma", "faiss"),
    "Application / outil": ("app", "tool", "space", "gradio", "webui", "launcher", "node", "workflow"),
}

LOCAL_SOURCES = {"huggingface", "pinokio", "github", "civitai", "modelscope"}
SOURCE_LABELS = dict(SOURCES)


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def classify(text: str, preferred: str = "") -> str:
    hay = str(text or "").lower()
    if preferred in TYPE_KEYWORDS:
        return preferred
    scores = []
    for category, words in TYPE_KEYWORDS.items():
        score = sum(1 for word in words if word in hay)
        scores.append((score, category))
    score, category = max(scores)
    return category if score else "Application / outil"


def _result(source: str, rid: str, name: str, author: str, description: str,
            tags, url: str, popularity=0, preferred_type: str = "",
            local: bool | None = None, install_ref: str = "") -> Dict[str, Any]:
    tags = [str(t) for t in (tags or []) if str(t).strip()]
    searchable = " ".join([name, author, description, " ".join(tags)])
    return {
        "key": source + ":" + str(rid),
        "source": source,
        "source_label": source_label(source),
        "id": str(rid),
        "name": str(name or rid),
        "author": str(author or ""),
        "description": str(description or ""),
        "tags": tags[:15],
        "url": str(url or ""),
        "popularity": popularity or 0,
        "type": classify(searchable, preferred_type),
        "local": source in LOCAL_SOURCES if local is None else bool(local),
        "install_ref": str(install_ref or ""),
    }


def search_one(source: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Saisissez un mot-clé.")
    limit = max(1, min(int(limit), 30))

    if source == "huggingface":
        rows = model_search.search_hf(query, limit=limit)
        return [
            _result(
                source, m["id"], m["name"], m["author"], "",
                m.get("tags", []), model_search.HF_SITE + "/" + m["id"],
                m.get("downloads", 0), "Texte & code", True, m["id"]
            ) for m in rows
        ]

    if source == "github":
        rows = model_search.search_github(query, limit=limit)
        return [
            _result(
                source, m["id"], m.get("name") or m["id"], m.get("author", ""),
                m.get("description", ""), m.get("tags", []),
                m.get("html_url") or (model_search.GITHUB_SITE + "/" + m["id"]),
                m.get("downloads", 0), "", True, m["id"]
            ) for m in rows
        ]

    if source == "civitai":
        rows = model_search.search_civitai(query, limit=limit)
        return [
            _result(
                source, m["id"], m.get("name") or m["id"], m.get("author", ""),
                m.get("description", ""), m.get("tags", []),
                model_search.CIVITAI_SITE + "/" + m["id"],
                m.get("downloads", 0), "Image", True, m["id"]
            ) for m in rows
        ]

    if source == "modelscope":
        rows = model_search.search_modelscope(query, limit=limit)
        return [
            _result(
                source, m["id"], m.get("name") or m["id"], m.get("author", ""),
                m.get("description", ""), m.get("tags", []),
                model_search.MODELSCOPE_SITE + "/" + m["id"],
                m.get("downloads", 0), "", True, m["id"]
            ) for m in rows
        ]

    if source == "pinokio":
        rows = pinokio_integration.search_registry(query, limit=limit)
        return [
            _result(
                source, m["id"], m["name"], m["author"], m["description"],
                m.get("tags", []), m.get("url") or m.get("repo") or "",
                m.get("popularity", 0), "Application / outil", True,
                m.get("install_uri", "")
            ) for m in rows
        ]

    if source == "hf-spaces":
        rows = extra_sources.search_hf_spaces(query, limit=limit)
        return [
            _result(
                source, m["id"], m["name"], m["author"],
                "Hugging Face Space · SDK " + (m.get("sdk") or "non indiqué"),
                m.get("tags", []), m["url"], m.get("likes", 0),
                "Application / outil", False, m.get("clone_url", "")
            ) for m in rows if not m.get("private")
        ]

    raise ValueError("Source inconnue : " + source)


def filter_results(results: List[Dict[str, Any]], source: str = "Toutes",
                   type_name: str = "Tous", local_only: bool = False,
                   favorites=None) -> List[Dict[str, Any]]:
    fav = set(favorites or [])
    output = []
    for item in results:
        if source != "Toutes" and item["source"] != source:
            continue
        if type_name != "Tous" and item["type"] != type_name:
            continue
        if local_only and not item["local"]:
            continue
        if favorites is not None and fav and item["key"] not in fav:
            continue
        output.append(item)
    return output


def merge_results(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = {item["key"]: item for item in existing}
    for item in incoming:
        merged[item["key"]] = item
    return sorted(
        merged.values(),
        key=lambda x: (int(x.get("popularity") or 0), x.get("name", "").lower()),
        reverse=True,
    )
