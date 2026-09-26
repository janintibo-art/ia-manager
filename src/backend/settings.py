"""Réglages de l'application, enregistrés dans ~/.ia_manager/config/settings.json"""

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".ia_manager" / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULTS: Dict[str, Any] = {
    "projects_dir": str(Path.home() / "IA Manager" / "Projets"),
    "github_owner": "",
    "termux_script": "~/memo-depot/mise-a-jour.sh",
    "github_folder": "",
    "theme": "sombre",
    "font_size": 13,
    "web_search": False,
    "brave_key": "",
    "searxng_url": "",
}


def load() -> Dict[str, Any]:
    data = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return data


def get(key: str) -> Any:
    return load().get(key, DEFAULTS.get(key))


def set(key: str, value: Any) -> None:  # noqa: A001 - nom volontairement simple
    data = load()
    data[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
