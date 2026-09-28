"""Actions adaptées aux résultats de la recherche universelle v110."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from src.backend import pinokio_integration


SEARCH_SOURCES = {
    "huggingface": 0,
    "github": 1,
    "modelscope": 2,
    "civitai": 3,
}


def action_for(item: Dict[str, Any]) -> Dict[str, Any]:
    source = str(item.get("source") or "")
    if source in SEARCH_SOURCES:
        labels = {
            "huggingface": "Installer / choisir la version",
            "github": "Voir les fichiers GGUF",
            "modelscope": "Ouvrir dans Recherche",
            "civitai": "Choisir et télécharger le fichier",
        }
        return {
            "kind": "search",
            "label": labels[source],
            "source_index": SEARCH_SOURCES[source],
            "query": str(item.get("id") or item.get("name") or ""),
        }
    if source == "pinokio":
        return {
            "kind": "pinokio-download",
            "label": "Télécharger dans Pinokio",
            "install_ref": str(item.get("install_ref") or ""),
        }
    if source == "hf-spaces":
        return {
            "kind": "clone-space",
            "label": "Cloner ce Space",
            "clone_url": str(item.get("install_ref") or item.get("url") or ""),
            "name": str(item.get("id") or item.get("name") or "space"),
        }
    return {"kind": "open", "label": "Ouvrir la source", "url": str(item.get("url") or "")}


def safe_folder_name(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/").split("/")[-1]
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-_")
    return value[:80] or "huggingface-space"


def clone_command(item: Dict[str, Any], parent: str, git: str) -> Dict[str, Any]:
    action = action_for(item)
    if action["kind"] != "clone-space":
        raise ValueError("Ce résultat n'est pas un Hugging Face Space.")
    url = action["clone_url"].strip()
    if not url.startswith("https://huggingface.co/spaces/"):
        raise ValueError("Adresse du Space non reconnue.")
    parent_path = Path(parent).expanduser().resolve()
    if not parent_path.is_dir():
        raise ValueError("Choisissez un dossier parent existant.")
    target = parent_path / safe_folder_name(action["name"])
    if target.exists():
        raise ValueError("Le dossier cible existe déjà : " + str(target))
    return {
        "program": str(git),
        "args": ["clone", "--depth", "1", url, str(target)],
        "cwd": str(parent_path),
        "target": str(target),
    }


def pinokio_download_command(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "install_uri": str(item.get("install_ref") or ""),
    }
    return pinokio_integration.download_command(normalized)
