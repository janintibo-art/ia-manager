"""Réglages réellement envoyés à Ollama : répartition VRAM/RAM, taille du contexte, température.

Ollama découpe un modèle en « couches ». `num_gpu` = nombre de couches placées dans la carte
graphique (VRAM) ; les autres restent en RAM et sont calculées par le processeur (plus lent).
`num_ctx` = mémoire de la conversation (en tokens) : plus grand = l'IA se souvient de plus de
choses, mais cela consomme de la VRAM/RAM.
"""

import math
from typing import Dict, Optional

import requests

from src.backend import settings

OLLAMA_URL = "http://localhost:11434"

MODES = {
    "auto": "🤖 Automatique (Ollama décide)",
    "speed": "⚡ Rapidité",
    "balanced": "⚖️ Équilibré",
    "quality": "🏆 Performance (mémoire longue)",
}
MODE_HELP = {
    "auto": "Ollama choisit seul la répartition. Simple et sûr.",
    "speed": "Contexte court (4 096 tokens) pour garder un maximum de couches dans la carte graphique.",
    "balanced": "Contexte de 8 192 tokens, le plus de couches possible en VRAM.",
    "quality": "Contexte de 16 384 tokens : l'IA suit mieux les longues discussions et les gros fichiers, "
               "quitte à déborder en RAM (plus lent).",
}
MODE_CTX = {"auto": 0, "speed": 4096, "balanced": 8192, "quality": 16384}
# Ancien vocabulaire de l'onglet Analyse -> mode
PRIORITY_TO_MODE = {"Rapidité maximale": "speed", "Équilibré": "balanced", "Qualité maximale": "quality"}

_meta_cache: Dict[str, Dict] = {}


def default_options() -> Dict:
    return {"mode": settings.get("default_mode") or "balanced", "num_ctx": 0,
            "temperature": 0.7, "gpu_layers": -1, "custom": False}


def get_options(ref: str) -> Dict:
    """Réglages d'un modèle (ceux du modèle s'il en a, sinon les réglages par défaut)"""
    opts = default_options()
    saved = (settings.get("model_options") or {}).get(ref)
    if saved:
        opts.update(saved)
        opts["custom"] = True
    return opts


def set_options(ref: str, opts: Dict) -> None:
    all_opts = dict(settings.get("model_options") or {})
    all_opts[ref] = {k: opts[k] for k in ("mode", "num_ctx", "temperature", "gpu_layers") if k in opts}
    settings.set("model_options", all_opts)


def reset_options(ref: str) -> None:
    all_opts = dict(settings.get("model_options") or {})
    all_opts.pop(ref, None)
    settings.set("model_options", all_opts)


def fetch_meta(model: str, timeout: int = 10) -> Dict:
    """Taille (Go), nombre de couches et contexte maximum d'un modèle Ollama (mis en cache)"""
    if model in _meta_cache:
        return _meta_cache[model]
    meta = {"size_gb": 0.0, "layers": 0, "max_ctx": 0}
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout).json().get("models", [])
        for m in tags:
            if m.get("name") == model or m.get("model") == model:
                meta["size_gb"] = m.get("size", 0) / (1024 ** 3)
        info = requests.post(f"{OLLAMA_URL}/api/show", json={"model": model, "name": model},
                             timeout=timeout).json().get("model_info", {}) or {}
        for key, value in info.items():
            if key.endswith(".block_count") and isinstance(value, int):
                meta["layers"] = value
            elif key.endswith(".context_length") and isinstance(value, int):
                meta["max_ctx"] = value
    except Exception:
        return meta  # pas de cache : on réessaiera
    if meta["size_gb"]:
        _meta_cache[model] = meta
    return meta


def plan(opts: Dict, meta: Dict, info: Optional[Dict], vram_percent: Optional[int] = None) -> Dict:
    """Calcule la répartition. Renvoie num_gpu (None = Ollama décide), num_ctx, estimation VRAM/RAM."""
    mode = opts.get("mode", "balanced")
    ctx = int(opts.get("num_ctx") or 0) or MODE_CTX.get(mode, 8192)
    if meta.get("max_ctx"):
        ctx = min(ctx, meta["max_ctx"]) if ctx else 0
    size = float(meta.get("size_gb") or 0)
    layers_total = int(meta.get("layers") or 0) + 1 if meta.get("layers") else 0  # + couche de sortie
    est_ctx = ctx or 4096
    kv = size * 0.2 * est_ctx / 8192          # estimation de la mémoire de conversation
    total = size + kv + 0.3 if size else 0.0

    vram = float((info or {}).get("vram_gb") or 0)
    pct = vram_percent if vram_percent is not None else int(settings.get("vram_percent") or 90)
    budget = max(0.0, vram * pct / 100 - 0.5)

    num_gpu: Optional[int] = None
    manual = int(opts.get("gpu_layers", -1))
    if manual >= 0 and layers_total:
        num_gpu = min(manual, layers_total)
    elif mode == "auto" or not layers_total or not total:
        num_gpu = None
    elif budget <= 0:
        num_gpu = 0
    else:
        ratio = min(1.0, budget / total)
        num_gpu = layers_total if ratio >= 1 else int(math.floor(layers_total * ratio))

    if num_gpu is None or not layers_total or not total:
        vram_used = min(total, budget) if total else 0.0
    else:
        vram_used = total * num_gpu / layers_total
    ram_used = max(0.0, total - vram_used)

    if not total:
        summary = "Taille du modèle inconnue (Ollama est-il lancé ?) : Ollama décidera de la répartition."
    elif num_gpu is None:
        summary = f"Ollama décide · environ {total:.1f} Go nécessaires · contexte {ctx or 'par défaut'}"
    else:
        where = ("tout en VRAM (rapide)" if num_gpu >= layers_total else
                 "tout en RAM (processeur, lent)" if num_gpu == 0 else "réparti VRAM + RAM")
        summary = (f"{num_gpu}/{layers_total} couches en VRAM · ~{vram_used:.1f} Go VRAM + "
                   f"~{ram_used:.1f} Go RAM · contexte {ctx} tokens · {where}")

    return {"num_gpu": num_gpu, "num_ctx": ctx, "temperature": float(opts.get("temperature", 0.7)),
            "layers_total": layers_total, "vram_gb": vram_used, "ram_gb": ram_used,
            "total_gb": total, "summary": summary}


def ollama_options(model: str, ref: str, info: Optional[Dict] = None) -> Dict:
    """Dictionnaire `options` à envoyer à l'API Ollama pour ce modèle"""
    opts = get_options(ref)
    if info is None:
        try:
            from src.backend.system_analyzer import SystemAnalyzer
            info = SystemAnalyzer.get_system_info()
        except Exception:
            info = None
    p = plan(opts, fetch_meta(model), info)
    out: Dict = {"temperature": p["temperature"]}
    if p["num_ctx"]:
        out["num_ctx"] = p["num_ctx"]
    if p["num_gpu"] is not None:
        out["num_gpu"] = p["num_gpu"]
    return out
