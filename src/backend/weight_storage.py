"""Gestion des poids et du stockage v106.

Toutes les opérations de suppression sont limitées aux fichiers temporaires connus.
Les modèles complets ne sont jamais supprimés automatiquement.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.backend import settings, storage, studio_advisor

MODEL_SUFFIXES = {
    ".gguf", ".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx",
}
PARTIAL_SUFFIXES = {
    ".part", ".tmp", ".ia-manager-part",
}
PARTIAL_NAMES = {
    "download.tmp", "incomplete", ".partial",
}


def human_size(size: int) -> str:
    value = float(max(0, int(size)))
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if value < 1024.0 or unit == "To":
            return f"{value:.1f} {unit}" if unit != "o" else f"{int(value)} o"
        value /= 1024.0
    return f"{value:.1f} To"


def folder_size(path: Path) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    total = 0
    for current, dirs, files in os.walk(path):
        current_path = Path(current)
        dirs[:] = [d for d in dirs if not (current_path / d).is_symlink()]
        for name in files:
            file = current_path / name
            try:
                if not file.is_symlink():
                    total += file.stat().st_size
            except OSError:
                pass
    return total


def free_space(path: Path) -> int:
    path = Path(path).expanduser()
    probe = path if path.exists() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return 0


def known_locations() -> List[Dict[str, Any]]:
    """Zones de poids connues sans inventer de chemin externe."""
    rows = [
        {"id": "downloads", "name": "Téléchargements IA Manager", "path": storage.app_models()},
        {"id": "ollama", "name": "Modèles Ollama", "path": storage.ollama_models()},
    ]
    tools_root = str(settings.get("creative_tools_root") or "").strip()
    if tools_root:
        base = Path(tools_root).expanduser()
        rows.extend([
            {"id": "comfy-cache", "name": "Cache ComfyUI", "path": base / "comfyui" / "cache"},
            {"id": "audio-cache", "name": "Cache AudioCraft", "path": base / "audiocraft" / "cache"},
            {"id": "triposr-cache", "name": "Cache TripoSR", "path": base / "triposr" / "cache"},
            {"id": "hunyuan-cache", "name": "Cache Hunyuan3D", "path": base / "hunyuan3d" / "cache"},
        ])
    return rows


def location_report() -> List[Dict[str, Any]]:
    report = []
    for item in known_locations():
        path = Path(item["path"]).expanduser()
        report.append({
            **item,
            "path": str(path),
            "exists": path.exists(),
            "size": folder_size(path),
            "free": free_space(path),
        })
    return report


def _is_partial(path: Path) -> bool:
    low = path.name.lower()
    if low in PARTIAL_NAMES:
        return True
    return any(low.endswith(suffix) for suffix in PARTIAL_SUFFIXES)


def inventory(max_files: int = 5000) -> List[Dict[str, Any]]:
    """Inventorie les fichiers de modèles/poids et temporaires dans les zones connues."""
    result: List[Dict[str, Any]] = []
    seen = set()
    for location in known_locations():
        root = Path(location["path"]).expanduser()
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            dirs[:] = [d for d in dirs if not (current_path / d).is_symlink()]
            for name in files:
                if len(result) >= max_files:
                    return sorted(result, key=lambda x: x["size"], reverse=True)
                path = current_path / name
                try:
                    if path.is_symlink():
                        continue
                    suffix = path.suffix.lower()
                    partial = _is_partial(path)
                    if suffix not in MODEL_SUFFIXES and not partial:
                        continue
                    resolved = str(path.resolve())
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    result.append({
                        "location": location["name"],
                        "path": resolved,
                        "name": path.name,
                        "size": path.stat().st_size,
                        "partial": partial,
                        "kind": "incomplet" if partial else (suffix.lstrip(".") or "poids"),
                    })
                except OSError:
                    continue
    return sorted(result, key=lambda x: x["size"], reverse=True)


def partial_files(max_files: int = 5000) -> List[Dict[str, Any]]:
    return [item for item in inventory(max_files) if item["partial"]]


def clean_partials(paths: Iterable[str]) -> Dict[str, int]:
    """Supprime uniquement les fichiers reconnus incomplets dans les zones gérées."""
    allowed_roots = []
    for location in known_locations():
        try:
            allowed_roots.append(Path(location["path"]).expanduser().resolve())
        except OSError:
            pass
    deleted = 0
    freed = 0
    for raw in paths:
        path = Path(raw)
        try:
            resolved = path.resolve()
            if not _is_partial(resolved):
                continue
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                continue
            if resolved.is_file() and not resolved.is_symlink():
                size = resolved.stat().st_size
                resolved.unlink()
                deleted += 1
                freed += size
        except OSError:
            continue
    return {"deleted": deleted, "freed": freed}


def pack_storage_estimate(pack_id: str) -> Dict[str, Any]:
    """Estimation prudente : poids catalogue + 25 % de marge pour caches/fichiers temporaires."""
    studio_advisor.extend_catalog()
    pack = studio_advisor.pack_by_id(pack_id)
    model_map = {m["id"]: m for m in studio_advisor.catalog.MODELS}
    models = []
    raw = 0.0
    for mid in pack.get("models", ()):
        model = model_map.get(mid)
        if not model:
            continue
        size = float(model.get("size_gb") or 0.0)
        raw += size
        models.append({"id": mid, "name": model["name"], "size_gb": size})
    recommended = raw * 1.25
    return {
        "pack": pack,
        "models": models,
        "raw_gb": raw,
        "recommended_gb": recommended,
    }


def validate_and_set_storage_root(directory: str) -> str:
    path = storage.validate_root(directory)
    settings.set("storage_root", str(path))
    storage.app_models().mkdir(parents=True, exist_ok=True)
    return str(path)


def preflight(pack_id: str, target: str) -> Dict[str, Any]:
    estimate = pack_storage_estimate(pack_id)
    target_path = storage.validate_root(target)
    free = free_space(target_path)
    need = int(estimate["recommended_gb"] * 1024 ** 3)
    return {
        **estimate,
        "target": str(target_path),
        "free": free,
        "need": need,
        "enough": free >= need if free else False,
    }
