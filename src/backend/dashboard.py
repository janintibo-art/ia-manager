"""Instantané pour le tableau de bord en direct : RAM, VRAM, IA chargées en mémoire par Ollama.

Tout est regroupé dans une seule fonction pour ne faire qu'un aller-retour réseau/système
par rafraîchissement, lancé dans un fil séparé (ai_manager, psutil et nvidia-smi bloquent un peu)."""

from datetime import datetime, timezone
from typing import Dict

import psutil

from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import gpu_usage


def format_expiry(expires_at: str) -> str:
    """Temps restant avant déchargement automatique par Ollama, en texte court (« 4 min », « 1.2 h »)."""
    if not expires_at:
        return ""
    try:
        s = expires_at.replace("Z", "+00:00")
        if "." in s:
            head, rest = s.split(".", 1)
            frac, tz = rest, ""
            for i, ch in enumerate(rest):
                if ch in "+-":
                    frac, tz = rest[:i], rest[i:]
                    break
            s = f"{head}.{(frac + '000000')[:6]}{tz}"
        dt = datetime.fromisoformat(s)
        now = datetime.now(dt.tzinfo or timezone.utc)
        delta = (dt - now).total_seconds()
        if delta <= 0:
            return "va se décharger"
        if delta < 60:
            return f"{int(delta)} s"
        if delta < 3600:
            return f"{int(delta // 60)} min"
        return f"{delta / 3600:.1f} h"
    except Exception:
        return ""


def snapshot(ai_manager: AIManager) -> Dict:
    """RAM/VRAM du PC et IA actuellement chargées en mémoire (à appeler hors du fil principal)."""
    mem = psutil.virtual_memory()
    up = ai_manager.is_ollama_running()
    running = ai_manager.list_running() if up else []
    for m in running:
        m["expiry_text"] = format_expiry(m.get("expires_at", ""))
    return {
        "ollama_up": up,
        "ram_used_gb": (mem.total - mem.available) / (1024 ** 3),
        "ram_total_gb": mem.total / (1024 ** 3),
        "gpu": gpu_usage(),
        "running": running,
    }
