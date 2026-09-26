"""Sauvegarde et restauration contrôlée de la configuration IA Manager."""
import json
from pathlib import Path
from typing import Any, Dict

from src.backend import settings

FORMAT = 1
_SAFE_KEYS = {
    "projects_dir", "github_owner", "termux_script", "github_folder", "theme", "font_size",
    "web_search", "searxng_url", "offline_mode", "providers", "project_memory_enabled",
    "serialize_local_jobs",
    "model_favorites",
}


def _copy_value(value: Any, include_secrets: bool) -> Any:
    if isinstance(value, dict):
        return {k: _copy_value(v, include_secrets) for k, v in value.items()
                if include_secrets or k not in {"api_key", "brave_key"}}
    if isinstance(value, list):
        return [_copy_value(v, include_secrets) for v in value]
    return value


def snapshot(include_secrets: bool = False) -> Dict[str, Any]:
    data = settings.load()
    return {"format": FORMAT, "app": "IA Manager",
            "settings": _copy_value({k: data.get(k) for k in _SAFE_KEYS if k in data}, include_secrets)}


def export_file(path: str, include_secrets: bool = False) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot(include_secrets), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def import_file(path: str) -> int:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != FORMAT or not isinstance(data.get("settings"), dict):
        raise ValueError("Format de sauvegarde IA Manager inconnu ou invalide.")
    incoming = data["settings"]
    applied = 0
    current = settings.load()
    for key in _SAFE_KEYS:
        if key in incoming:
            if key == "providers" and not isinstance(incoming[key], list):
                raise ValueError("La liste des fournisseurs est invalide.")
            if key == "providers":
                old = {p.get("id"): p for p in (current.get("providers") or []) if isinstance(p, dict)}
                merged = []
                for provider in incoming[key]:
                    if not isinstance(provider, dict):
                        raise ValueError("Un fournisseur est invalide.")
                    item = dict(provider)
                    previous = old.get(item.get("id"), {})
                    for secret in ("api_key",):
                        if secret not in item and previous.get(secret):
                            item[secret] = previous[secret]
                    merged.append(item)
                current[key] = merged
            else:
                current[key] = incoming[key]
            applied += 1
    # Une sauvegarde sans secrets ne doit jamais effacer les clés déjà présentes.
    for key, value in current.items():
        settings.set(key, value)
    return applied
