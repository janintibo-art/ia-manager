"""Favoris de modèles, indépendants de la source."""
from datetime import datetime
import json
from pathlib import Path
from src.backend import settings


def list_favorites():
    items = settings.get("model_favorites") or []
    return [item for item in items if isinstance(item, dict) and item.get("id")]


def is_favorite(source: str, model_id: str) -> bool:
    return any(x.get("source") == source and x.get("id") == model_id for x in list_favorites())


def toggle(source: str, model_id: str, name: str = "") -> bool:
    items = list_favorites()
    found = next((x for x in items if x.get("source") == source and x.get("id") == model_id), None)
    if found:
        items.remove(found); state = False
    else:
        items.insert(0, {"source": source, "id": model_id, "name": name or model_id,
                         "saved_at": datetime.now().isoformat(timespec="seconds")}); state = True
    settings.set("model_favorites", items[:200])
    return state


def export_file(path: str) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"format": 1, "favorites": list_favorites()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def import_file(path: str) -> int:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if data.get("format") != 1 or not isinstance(data.get("favorites"), list):
        raise ValueError("Fichier de favoris invalide.")
    valid = [x for x in data["favorites"] if isinstance(x, dict) and x.get("id") and x.get("source")]
    settings.set("model_favorites", valid[:200])
    return len(valid[:200])


def clear() -> int:
    count = len(list_favorites())
    settings.set("model_favorites", [])
    return count
