
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List

from src.backend import settings

SUPPORTED = (".fbx", ".bvh", ".blend")

CATEGORIES = (
    "Tous", "Idle", "Walk", "Run", "Attack", "Jump", "Dance", "Hit", "Death",
    "Emote", "Other",
)

KEYWORDS = {
    "Idle": ("idle", "stand", "breath"),
    "Walk": ("walk", "walking", "marche"),
    "Run": ("run", "running", "course", "sprint"),
    "Attack": ("attack", "slash", "punch", "kick", "shoot", "fire", "combat"),
    "Jump": ("jump", "leap", "hop", "saut"),
    "Dance": ("dance", "dancing"),
    "Hit": ("hit", "damage", "hurt", "impact"),
    "Death": ("death", "die", "dead"),
    "Emote": ("emote", "wave", "clap", "point", "laugh", "cry"),
}

def classify(name: str) -> str:
    hay = str(name or "").lower().replace("_", " ").replace("-", " ")
    for cat, words in KEYWORDS.items():
        if any(word in hay for word in words):
            return cat
    return "Other"

def normalize_roots(value) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for raw in value:
        p = Path(str(raw)).expanduser()
        try:
            resolved = str(p.resolve())
        except OSError:
            continue
        if p.is_dir() and resolved not in out:
            out.append(resolved)
    return out[:20]

def saved_roots() -> List[str]:
    return normalize_roots(settings.get("animation_library_roots") or [])

def save_roots(roots: Iterable[str]) -> List[str]:
    clean = normalize_roots(list(roots))
    settings.set("animation_library_roots", clean)
    return clean

def saved_favorites() -> List[str]:
    value = settings.get("animation_library_favorites") or []
    if not isinstance(value, (list, tuple)):
        return []
    return sorted({str(x) for x in value if str(x).strip()})

def save_favorites(values: Iterable[str]) -> List[str]:
    clean = sorted({str(x) for x in values if str(x).strip()})
    settings.set("animation_library_favorites", clean)
    return clean

def scan(roots: Iterable[str], max_files: int = 10000) -> List[Dict]:
    items = []
    seen = set()
    for root in normalize_roots(list(roots)):
        base = Path(root)
        for current, dirs, files in os.walk(base):
            cur = Path(current)
            dirs[:] = [d for d in dirs if not (cur / d).is_symlink()]
            for name in files:
                if len(items) >= max_files:
                    return sorted(items, key=lambda x: (x["category"], x["name"].lower()))
                path = cur / name
                try:
                    if path.is_symlink() or path.suffix.lower() not in SUPPORTED:
                        continue
                    resolved = str(path.resolve())
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    stat = path.stat()
                    stem = path.stem
                    items.append({
                        "id": resolved,
                        "name": stem,
                        "path": resolved,
                        "format": path.suffix.lower().lstrip(".").upper(),
                        "category": classify(stem),
                        "root": root,
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                    })
                except OSError:
                    continue
    return sorted(items, key=lambda x: (x["category"], x["name"].lower()))

def filter_items(items: List[Dict], query: str = "", category: str = "Tous",
                 favorites_only: bool = False, favorites=None) -> List[Dict]:
    q = str(query or "").strip().lower()
    fav = set(favorites or [])
    out = []
    for item in items:
        if category != "Tous" and item["category"] != category:
            continue
        if favorites_only and item["id"] not in fav:
            continue
        if q:
            hay = " ".join((item["name"], item["category"], item["format"], item["path"])).lower()
            if q not in hay:
                continue
        out.append(item)
    return out

def human_size(size: int) -> str:
    value = float(max(0, int(size)))
    for unit in ("o", "Ko", "Mo", "Go"):
        if value < 1024 or unit == "Go":
            return f"{int(value)} {unit}" if unit == "o" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} Go"

def sidecar_path(item_path: str) -> Path:
    p = Path(item_path)
    return p.with_suffix(p.suffix + ".ia.json")

def load_metadata(item_path: str) -> Dict:
    p = sidecar_path(item_path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save_metadata(item_path: str, metadata: Dict) -> str:
    p = sidecar_path(item_path)
    data = {
        "category": str(metadata.get("category") or classify(Path(item_path).stem)),
        "tags": [str(x) for x in metadata.get("tags", []) if str(x).strip()][:30],
        "notes": str(metadata.get("notes") or "")[:2000],
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)

def effective_category(item: Dict) -> str:
    meta = load_metadata(item["path"])
    value = str(meta.get("category") or item.get("category") or "Other")
    return value if value in CATEGORIES else "Other"
