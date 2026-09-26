"""IA externes : Claude (API Anthropic), ChatGPT (API OpenAI) et serveurs compatibles OpenAI
(LM Studio, llama.cpp, Jan, OpenRouter, Mistral…). Plus l'ajout manuel de modèles dans Ollama.

Un modèle est désigné par une « référence » :  fournisseur::modèle
    ollama::qwen3:8b          claude::claude-sonnet-5          lmstudio::mon-modele
Une référence sans « :: » est un modèle Ollama (compatibilité avec les anciennes sauvegardes).
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from src.backend import settings

SEP = "::"
OLLAMA_URL = "http://localhost:11434"

BUILTIN = [
    {"id": "claude", "name": "Claude (Anthropic)", "kind": "anthropic",
     "base_url": "https://api.anthropic.com/v1", "api_key": "", "models": [], "enabled": True,
     "key_url": "https://console.anthropic.com/settings/keys", "web_url": "https://claude.ai"},
    {"id": "chatgpt", "name": "ChatGPT (OpenAI)", "kind": "openai",
     "base_url": "https://api.openai.com/v1", "api_key": "", "models": [], "enabled": True,
     "key_url": "https://platform.openai.com/api-keys", "web_url": "https://chatgpt.com"},
]

# Serveurs compatibles OpenAI proposés en un clic
PRESETS = {
    "LM Studio (sur ce PC)": ("lmstudio", "http://localhost:1234/v1", False),
    "llama.cpp server (sur ce PC)": ("llamacpp", "http://localhost:8080/v1", False),
    "Jan (sur ce PC)": ("jan", "http://localhost:1337/v1", False),
    "GPT4All (sur ce PC)": ("gpt4all", "http://localhost:4891/v1", False),
    "OpenRouter (en ligne, des centaines de modèles)": ("openrouter", "https://openrouter.ai/api/v1", True),
    "Mistral AI (en ligne)": ("mistral", "https://api.mistral.ai/v1", True),
    "Groq (en ligne, très rapide)": ("groq", "https://api.groq.com/openai/v1", True),
    "Autre serveur compatible OpenAI": ("perso", "http://localhost:8000/v1", False),
}

OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")
OPENAI_EXCLUDE = ("audio", "realtime", "tts", "transcribe", "embedding", "image", "search",
                  "moderation", "dall-e", "whisper", "davinci", "babbage", "instruct")


# ------------------------------------------------------------ configuration
def get_providers() -> List[Dict]:
    saved = {p["id"]: p for p in (settings.get("providers") or [])}
    result = []
    for b in BUILTIN:
        p = dict(b)
        p.update({k: v for k, v in saved.get(b["id"], {}).items() if k in ("api_key", "models", "enabled")})
        result.append(p)
    for pid, p in saved.items():
        if pid not in {b["id"] for b in BUILTIN}:
            p = dict(p)
            p.setdefault("kind", "openai_compat")
            p.setdefault("models", [])
            p.setdefault("enabled", True)
            p.setdefault("api_key", "")
            result.append(p)
    return result


def get_provider(pid: str) -> Optional[Dict]:
    return next((p for p in get_providers() if p["id"] == pid), None)


def save_provider(provider: Dict) -> None:
    saved = [p for p in (settings.get("providers") or []) if p["id"] != provider["id"]]
    keep = {k: provider.get(k) for k in ("id", "name", "kind", "base_url", "api_key", "models", "enabled")}
    saved.append(keep)
    settings.set("providers", saved)


def delete_provider(pid: str) -> None:
    if pid in {b["id"] for b in BUILTIN}:
        p = get_provider(pid)
        if p:
            p.update(api_key="", models=[])
            save_provider(p)
        return
    settings.set("providers", [p for p in (settings.get("providers") or []) if p["id"] != pid])


def unique_id(base: str) -> str:
    ids = {p["id"] for p in get_providers()} | {"ollama"}
    pid, n = base, 2
    while pid in ids:
        pid = f"{base}{n}"
        n += 1
    return pid


def is_configured(p: Dict) -> bool:
    if not p.get("enabled", True):
        return False
    if p["kind"] in ("anthropic", "openai"):
        return bool(p.get("api_key"))
    return bool(p.get("base_url"))


def mask_key(key: str) -> str:
    return "" if not key else (key[:7] + "…" + key[-4:] if len(key) > 14 else "••••")


# ------------------------------------------------------------ références
def split_ref(ref: str) -> Tuple[str, str]:
    if SEP in ref:
        pid, model = ref.split(SEP, 1)
        return pid, model
    return "ollama", ref


def make_ref(pid: str, model: str) -> str:
    return f"{pid}{SEP}{model}"


def label_for(ref: str) -> str:
    pid, model = split_ref(ref)
    if pid == "ollama":
        return f"💻 {model}"
    p = get_provider(pid)
    return f"☁️ {(p or {}).get('name', pid)} · {model}"


def all_model_choices(ollama_models: List[str]) -> List[Tuple[str, str]]:
    """(libellé, référence) : modèles locaux puis modèles des fournisseurs configurés"""
    choices = [(f"💻 {m}", make_ref("ollama", m)) for m in ollama_models]
    for p in get_providers():
        if is_configured(p):
            icon = "🖥️" if "localhost" in p.get("base_url", "") or "127.0.0.1" in p.get("base_url", "") else "☁️"
            for m in p.get("models", []):
                choices.append((f"{icon} {p['name']} · {m}", make_ref(p["id"], m)))
    return choices


# ------------------------------------------------------------ appels HTTP
def _headers(p: Dict) -> Dict[str, str]:
    if p["kind"] == "anthropic":
        return {"x-api-key": p.get("api_key", ""), "anthropic-version": "2023-06-01",
                "content-type": "application/json"}
    h = {"Content-Type": "application/json"}
    if p.get("api_key"):
        h["Authorization"] = f"Bearer {p['api_key']}"
    return h


def _error_text(r: requests.Response) -> str:
    try:
        data = r.json()
        err = data.get("error", data)
        if isinstance(err, dict):
            err = err.get("message", str(err))
        return f"{r.status_code} : {err}"
    except Exception:
        return f"{r.status_code} : {r.text[:300]}"


def fetch_models(p: Dict) -> List[str]:
    """Liste des modèles proposés par le fournisseur (lève une exception en cas d'échec)"""
    url = p["base_url"].rstrip("/") + "/models"
    if p["kind"] == "anthropic":
        url += "?limit=100"
    r = requests.get(url, headers=_headers(p), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(_error_text(r))
    data = r.json()
    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
    if p["kind"] == "openai":
        ids = [i for i in ids if i.startswith(OPENAI_CHAT_PREFIXES) and not any(x in i for x in OPENAI_EXCLUDE)]
    return sorted(set(ids), key=str.lower) if p["kind"] != "anthropic" else ids


def test_provider(p: Dict) -> Tuple[bool, str]:
    try:
        models = fetch_models(p)
    except requests.exceptions.ConnectionError:
        return False, "Connexion impossible : le serveur ne répond pas (est-il lancé ? l'adresse est-elle bonne ?)."
    except Exception as e:
        return False, f"Échec : {e}"
    if not models:
        return True, "Connexion réussie, mais aucun modèle n'a été trouvé."
    return True, f"Connexion réussie : {len(models)} modèle(s) disponible(s)."


def _openai_messages(messages: List[Dict], system: str) -> List[Dict]:
    out = [{"role": "system", "content": system}] if system.strip() else []
    for m in messages:
        if m.get("images"):
            content = [{"type": "text", "text": m["content"]}]
            for img in m["images"]:
                content.append({"type": "image_url",
                                "image_url": {"url": f"data:{img['mime']};base64,{img['data']}"}})
            out.append({"role": m["role"], "content": content})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def _anthropic_messages(messages: List[Dict]) -> List[Dict]:
    out = []
    for m in messages:
        if m.get("images"):
            content = [{"type": "image", "source": {"type": "base64", "media_type": img["mime"],
                                                    "data": img["data"]}} for img in m["images"]]
            content.append({"type": "text", "text": m["content"] or "(image)"})
            out.append({"role": m["role"], "content": content})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def chat_remote(p: Dict, model: str, messages: List[Dict], system: str = "") -> str:
    base = p["base_url"].rstrip("/")
    try:
        if p["kind"] == "anthropic":
            body = {"model": model, "max_tokens": 8192, "messages": _anthropic_messages(messages)}
            if system.strip():
                body["system"] = system
            r = requests.post(f"{base}/messages", headers=_headers(p), json=body, timeout=600)
            if r.status_code != 200:
                return f"Erreur {p['name']} {_error_text(r)}"
            return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        body = {"model": model, "messages": _openai_messages(messages, system)}
        r = requests.post(f"{base}/chat/completions", headers=_headers(p), json=body, timeout=600)
        if r.status_code != 200:
            return f"Erreur {p['name']} {_error_text(r)}"
        choices = r.json().get("choices", [])
        return (choices[0].get("message", {}).get("content") or "") if choices else ""
    except requests.exceptions.ConnectionError:
        return f"Erreur : impossible de joindre {p['name']} ({base})."
    except Exception as e:
        return f"Erreur : {e}"


def chat_ollama(model: str, messages: List[Dict], system: str = "") -> str:
    payload = [{"role": "system", "content": system}] if system.strip() else []
    for m in messages:
        item = {"role": m["role"], "content": m["content"]}
        if m.get("images"):
            item["images"] = [img["data"] for img in m["images"]]
        payload.append(item)
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat",
                          json={"model": model, "messages": payload, "stream": False}, timeout=900)
        if r.status_code == 200:
            return r.json().get("message", {}).get("content", "")
        return f"Erreur Ollama : {r.status_code} {r.text[:200]}"
    except requests.exceptions.ConnectionError:
        return "Ollama n'est pas lancé. Installez-le depuis ollama.com puis relancez."
    except Exception as e:
        return f"Erreur : {e}"


def chat(ref: str, messages: List[Dict], system: str = "") -> str:
    """Point d'entrée unique : envoie la discussion au bon fournisseur"""
    pid, model = split_ref(ref)
    if pid == "ollama":
        return chat_ollama(model, messages, system)
    p = get_provider(pid)
    if not p:
        return f"Erreur : fournisseur « {pid} » introuvable (onglet Connexions)."
    if not is_configured(p):
        return f"Erreur : {p['name']} n'est pas configuré (onglet Connexions)."
    return chat_remote(p, model, messages, system)


# ------------------------------------------------------------ ajout manuel dans Ollama
def hf_model_name(repo: str, quant: str = "") -> str:
    """Nom Ollama d'un modèle GGUF de Hugging Face : hf.co/utilisateur/depot[:quantif]"""
    repo = repo.strip()
    for prefix in ("https://huggingface.co/", "http://huggingface.co/", "huggingface.co/", "hf.co/"):
        if repo.startswith(prefix):
            repo = repo[len(prefix):]
    repo = repo.strip("/")
    name = f"hf.co/{repo}"
    if quant.strip():
        name += f":{quant.strip()}"
    return name


def find_ollama_exe() -> Optional[str]:
    exe = shutil.which("ollama")
    if exe:
        return exe
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return str(candidate)
    return None


def create_from_gguf(name: str, gguf_path: str, system: str = "") -> str:
    """Importe un fichier .gguf dans Ollama sous le nom donné (lève une exception si échec)"""
    exe = find_ollama_exe()
    if not exe:
        raise RuntimeError("Programme Ollama introuvable. Installez Ollama depuis ollama.com.")
    modelfile = f'FROM "{Path(gguf_path).as_posix()}"\n'
    if system.strip():
        modelfile += f'SYSTEM """{system.strip()}"""\n'
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False, encoding="utf-8") as f:
        f.write(modelfile)
        mf = f.name
    try:
        flags = 0x08000000 if os.name == "nt" else 0
        out = subprocess.run([exe, "create", name, "-f", mf], capture_output=True, text=True,
                             timeout=3600, creationflags=flags, encoding="utf-8", errors="replace")
        if out.returncode != 0:
            raise RuntimeError((out.stderr or out.stdout).strip()[-800:] or "échec de la création")
        return (out.stdout or "").strip()[-400:]
    finally:
        try:
            os.unlink(mf)
        except OSError:
            pass


def valid_model_name(name: str) -> bool:
    import re
    return bool(re.match(r"^[a-z0-9][a-z0-9._\-/]*(:[a-z0-9._\-]+)?$", name))
