"""Intégration Pinokio v107.

Recherche le registre officiel Pinokio et expose des commandes pterm explicites.
Aucun script Pinokio n'est exécuté automatiquement.
"""
from __future__ import annotations

import json
import shutil
from typing import Any, Dict, List, Optional

import requests

REGISTRY_API = "https://api.pinokio.co/v1/search"
PINOKIO_LOCAL = "http://127.0.0.1:42000"


def pterm_path() -> Optional[str]:
    return shutil.which("pterm") or shutil.which("pterm.cmd") or shutil.which("pterm.exe")


def local_status(timeout: int = 2) -> Dict[str, Any]:
    result = {"pterm": pterm_path(), "running": False, "version": {}}
    try:
        response = requests.get(
            PINOKIO_LOCAL + "/pinokio/version",
            timeout=timeout,
            headers={"x-pinokio-client": "ia-manager"},
        )
        if response.ok:
            result["running"] = True
            data = response.json()
            result["version"] = data if isinstance(data, dict) else {}
    except (requests.RequestException, ValueError):
        pass
    return result


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "apps", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            for subkey in ("results", "items", "apps"):
                nested = value.get(subkey)
                if isinstance(nested, list):
                    return [x for x in nested if isinstance(x, dict)]
    return []


def _first(item: Dict[str, Any], keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    app_id = str(_first(item, ("id", "slug", "app_id", "name", "repo"), "")).strip()
    name = str(_first(item, ("title", "display_name", "name", "id"), app_id)).strip() or app_id
    description = str(_first(item, ("description", "summary", "tagline"), "")).strip()
    repo = str(_first(item, ("repo", "repository", "repository_url", "git", "github"), "")).strip()
    url = str(_first(item, ("url", "web_url", "homepage", "page", "href"), "")).strip()
    install_uri = str(_first(item, ("install_url", "launcher", "uri", "git_url"), repo or url)).strip()
    author = _first(item, ("author", "publisher", "owner", "creator"), "")
    if isinstance(author, dict):
        author = _first(author, ("name", "login", "username"), "")
    tags = item.get("tags") or item.get("categories") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        tags = []
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    popularity = _first(item, ("checkins", "downloads", "stars", "popularity"),
                        _first(stats, ("checkins", "downloads", "stars"), 0))
    return {
        "id": app_id,
        "name": name,
        "description": description,
        "repo": repo,
        "url": url,
        "install_uri": install_uri,
        "author": str(author or ""),
        "tags": [str(x) for x in tags[:12]],
        "popularity": popularity or 0,
        "raw": item,
    }


def search_registry(query: str, limit: int = 30, sort: str = "relevance",
                    platform: str = "windows", gpu: str = "") -> List[Dict[str, Any]]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Saisissez un nom, une spécialité ou un mot-clé.")
    params = {"q": query, "limit": max(1, min(int(limit), 50)), "sort": sort}
    if platform in ("windows", "linux", "mac"):
        params["platform"] = platform
    if gpu in ("nvidia", "amd", "apple"):
        params["gpu"] = gpu
    response = requests.get(REGISTRY_API, params=params, timeout=20)
    response.raise_for_status()
    return [normalize_item(item) for item in _rows(response.json())]


def download_command(item: Dict[str, Any]):
    pterm = pterm_path()
    if not pterm:
        raise ValueError("pterm n'est pas installé. Installez Pinokio/pterm puis relancez la détection.")
    uri = str(item.get("install_uri") or "").strip()
    if not uri:
        raise ValueError("Cette entrée du registre ne fournit pas d'adresse d'installation.")
    return {"program": pterm, "args": ["download", uri]}


def run_command(item: Dict[str, Any]):
    pterm = pterm_path()
    if not pterm:
        raise ValueError("pterm n'est pas installé.")
    uri = str(item.get("install_uri") or "").strip()
    if not uri:
        raise ValueError("Cette entrée ne fournit pas d'adresse de lancement.")
    return {
        "program": pterm,
        "args": ["run", uri, "--default", "run.js", "--default", "start.js",
                 "--default", "install.js", "--open"],
    }


def safe_export(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k != "raw"}
