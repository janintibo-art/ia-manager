"""LM Studio sur ce PC : détection automatique, liste des modèles, déchargement.

LM Studio expose un serveur local (port 1234 par défaut) :
  - /api/v1/models          API native (LM Studio 0.4+) : modèles, quantification, instances chargées
  - /api/v0/models          ancienne API native (versions précédentes)
  - /v1/models              API compatible OpenAI (liste simple, toujours présente)
On essaie dans cet ordre et on ramène tout au même format.
"""

from typing import Dict, List, Optional

import requests

from src.backend import providers

BASE_URL = "http://localhost:1234"
PROVIDER_ID = "lmstudio"


def _get(path: str, timeout: float) -> Optional[Dict]:
    try:
        r = requests.get(f"{BASE_URL}{path}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _from_v1(m: Dict) -> Dict:
    quant = m.get("quantization") or {}
    if isinstance(quant, str):
        quant = {"name": quant}
    instances = m.get("loaded_instances") or []
    caps = m.get("capabilities") or {}
    return {
        "key": m.get("key") or m.get("id", ""),
        "name": m.get("display_name") or m.get("key") or m.get("id", ""),
        "type": m.get("type", "llm"),
        "arch": m.get("architecture", ""),
        "quant": quant.get("name", ""),
        "bits": quant.get("bits_per_weight"),
        "size_bytes": m.get("size_bytes") or 0,
        "params": m.get("params_string", ""),
        "max_ctx": m.get("max_context_length") or 0,
        "format": m.get("format", ""),
        "vision": bool(caps.get("vision")),
        "tools": bool(caps.get("trained_for_tool_use")),
        "loaded": bool(instances),
        "instances": [{"id": i.get("id", ""), "ctx": (i.get("config") or {}).get("context_length", 0)}
                      for i in instances],
    }


def _from_v0(m: Dict) -> Dict:
    loaded = m.get("state") == "loaded"
    return {
        "key": m.get("id", ""), "name": m.get("id", ""), "type": m.get("type", "llm"),
        "arch": m.get("arch", ""), "quant": m.get("quantization", "") or "", "bits": None,
        "size_bytes": 0, "params": "", "max_ctx": m.get("max_context_length") or 0,
        "format": m.get("compatibility_type", ""), "vision": m.get("type") == "vlm", "tools": False,
        "loaded": loaded,
        "instances": [{"id": m.get("id", ""), "ctx": m.get("loaded_context_length", 0)}] if loaded else [],
    }


def list_models(timeout: float = 1.5) -> Optional[List[Dict]]:
    """Modèles de LM Studio, ou None si LM Studio n'est pas lancé (serveur arrêté)."""
    data = _get("/api/v1/models", timeout)
    if data and isinstance(data.get("models"), list):
        return [_from_v1(m) for m in data["models"]]
    data = _get("/api/v0/models", timeout)
    if data and isinstance(data.get("data"), list):
        return [_from_v0(m) for m in data["data"]]
    data = _get("/v1/models", timeout)
    if data and isinstance(data.get("data"), list):
        return [{"key": m.get("id", ""), "name": m.get("id", ""), "type": "llm", "arch": "", "quant": "",
                 "bits": None, "size_bytes": 0, "params": "", "max_ctx": 0, "format": "", "vision": False,
                 "tools": False, "loaded": False, "instances": []} for m in data["data"]]
    return None


def chat_models(models: List[Dict]) -> List[str]:
    """Identifiants des modèles de discussion (sans les modèles d'embedding)"""
    return [m["key"] for m in models if m["key"] and "embed" not in (m.get("type") or "").lower()
            and "embed" not in m["key"].lower()]


def find_provider() -> Optional[Dict]:
    """Fournisseur déjà configuré qui pointe vers LM Studio (même port, sur ce PC), s'il existe"""
    port = BASE_URL.rsplit(":", 1)[-1]
    for p in providers.get_providers():
        url = (p.get("base_url") or "").lower()
        if f":{port}" in url and ("localhost" in url or "127.0.0.1" in url):
            return p
    return None


def apply_models(models: Optional[List[Dict]]) -> bool:
    """Crée ou met à jour le fournisseur LM Studio avec ses modèles. True si quelque chose a changé.
    Appelé dans le fil principal (écrit les réglages)."""
    if models is None:
        return False
    keys = chat_models(models)
    p = find_provider()
    if p is None:
        if not keys:
            return False
        p = {"id": PROVIDER_ID if not providers.get_provider(PROVIDER_ID) else providers.unique_id(PROVIDER_ID),
             "name": "LM Studio", "kind": "openai_compat", "base_url": f"{BASE_URL}/v1",
             "api_key": "", "models": keys, "enabled": True}
        providers.save_provider(p)
        return True
    if sorted(p.get("models") or []) == sorted(keys):
        return False
    p = dict(p)
    p["models"] = keys
    providers.save_provider(p)
    return True


def unload(instance_id: str) -> bool:
    """Décharge une instance de modèle (LM Studio 0.4+). Les versions plus anciennes ne le permettent pas."""
    try:
        r = requests.post(f"{BASE_URL}/api/v1/models/unload", json={"instance_id": instance_id}, timeout=15)
        return r.status_code == 200
    except Exception:
        return False
