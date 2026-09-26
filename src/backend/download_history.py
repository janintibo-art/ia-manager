"""Historique léger des téléchargements de modèles et nettoyage du cache."""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from threading import RLock

ROOT = Path.home() / ".ia_manager" / "models"
HISTORY = ROOT / "download_history.json"
_LOCK = RLock()


def list_entries():
    with _LOCK:
        try:
            data = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
            return data if isinstance(data, list) else []
        except Exception:
            return []


def _save(data):
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="history_", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data[:100], stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, HISTORY)
    finally:
        if os.path.exists(name): os.unlink(name)


def record(name: str, source: str, path: str = "", size: int = 0):
    with _LOCK:
        data = [item for item in list_entries() if not (item.get("name") == name and item.get("source") == source)]
        data.insert(0, {"name": name, "source": source, "path": path, "size": int(size or 0),
                        "installed_at": datetime.now().isoformat(timespec="seconds")})
        _save(data)


def cleanup_cache(keep_history: bool = True) -> int:
    """Supprime les téléchargements temporaires et les GGUF non référencés par l'historique."""
    with _LOCK:
        entries = list_entries()
        referenced = {str(item.get("path")) for item in entries} if keep_history else set()
        removed = 0
        if ROOT.exists():
            for path in ROOT.glob("downloads/*"):
                if path.is_file() and (path.name.endswith(".part") or str(path) not in referenced):
                    try:
                        path.unlink(); removed += 1
                    except OSError:
                        pass
        return removed
