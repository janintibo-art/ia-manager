"""Réglages de l'application, enregistrés dans ~/.ia_manager/config/settings.json"""

import json
import os
import tempfile
from threading import RLock
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".ia_manager" / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

_LOCK = RLock()
_CACHE = None
_CACHE_MTIME = None

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
    global _CACHE, _CACHE_MTIME
    with _LOCK:
        try:
            mtime = SETTINGS_FILE.stat().st_mtime_ns if SETTINGS_FILE.exists() else None
            if _CACHE is not None and mtime == _CACHE_MTIME:
                return dict(_CACHE)
            data = dict(DEFAULTS)
            if SETTINGS_FILE.exists():
                data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
            _CACHE, _CACHE_MTIME = data, mtime
            return dict(data)
        except Exception:
            return dict(_CACHE or DEFAULTS)


def get(key: str) -> Any:
    return load().get(key, DEFAULTS.get(key))


def set(key: str, value: Any) -> None:  # noqa: A001 - nom volontairement simple
    with _LOCK:
        data = load()
        data[key] = value
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Remplacement atomique : une interruption conserve le précédent JSON.
        fd, name = tempfile.mkstemp(prefix="settings_", suffix=".tmp", dir=CONFIG_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, SETTINGS_FILE)
            global _CACHE, _CACHE_MTIME
            _CACHE = dict(data)
            _CACHE_MTIME = SETTINGS_FILE.stat().st_mtime_ns
        finally:
            if os.path.exists(name):
                os.unlink(name)
