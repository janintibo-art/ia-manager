"""Rapport de diagnostic exportable sans clés ni contenu des conversations."""
import json
from datetime import datetime
from pathlib import Path
from src.backend import settings, providers
from src.backend.system_analyzer import SystemAnalyzer


def snapshot():
    info = SystemAnalyzer.get_system_info()
    safe_providers = []
    for provider in providers.get_providers():
        safe_providers.append({"id": provider.get("id"), "name": provider.get("name"),
                               "kind": provider.get("kind"), "enabled": provider.get("enabled", True),
                               "configured": providers.is_configured(provider),
                               "models_count": len(provider.get("models", []))})
    return {"created": datetime.now().isoformat(timespec="seconds"), "app": "IA Manager",
            "settings": {"theme": settings.get("theme"), "font_size": settings.get("font_size"),
                         "project_memory_enabled": settings.get("project_memory_enabled"),
                         "serialize_local_jobs": settings.get("serialize_local_jobs"),
                         "github_token_configured": bool(settings.get("github_token"))},
            "system": info, "providers": safe_providers}


def export(folder=None):
    target = Path(folder or (Path.home() / ".ia_manager" / "diagnostics"))
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"diagnostic_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
