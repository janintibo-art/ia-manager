"""Favoris de modèles, indépendants de la source."""
from datetime import datetime
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
