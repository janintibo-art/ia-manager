"""Moteur de recherche d'IA : explore les modèles GGUF publiés sur Hugging Face
(plus de 100 000 modèles), puis les télécharge dans Ollama (hf.co/depot:quantification)."""

import hashlib
import re
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import requests
from src.backend import settings, storage

HF_API = "https://huggingface.co/api/models"
HF_SITE = "https://huggingface.co"
GITHUB_API = "https://api.github.com"
GITHUB_SITE = "https://github.com"
MODELSCOPE_API = "https://modelscope.cn/openapi/v1/models"
MODELSCOPE_SITE = "https://modelscope.cn/models"
CIVITAI_API = "https://civitai.com/api/v1/models"
CIVITAI_SITE = "https://civitai.com/models"
_DETAIL_CACHE = {}
_DETAIL_TTL = 60
_SEARCH_CACHE = {}
_SEARCH_TTL = 120
_SEARCH_CACHE_FILE = Path.home() / ".ia_manager" / "cache" / "search_results.json"


def clear_detail_cache():
    _DETAIL_CACHE.clear()


def clear_search_cache():
    _SEARCH_CACHE.clear()
    try:
        _SEARCH_CACHE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _load_search_disk():
    try:
        data = json.loads(_SEARCH_CACHE_FILE.read_text(encoding="utf-8")) if _SEARCH_CACHE_FILE.exists() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_search_disk(key, value):
    try:
        _SEARCH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = _load_search_disk()
        data["|".join(map(str, key))] = {"saved": time.time(), "results": value}
        # Limite de taille : les métadonnées de recherche ne doivent jamais grossir sans limite.
        entries = list(data.items())[-100:]
        _SEARCH_CACHE_FILE.write_text(json.dumps(dict(entries), ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def search_source(source: str, query: str, category=None, sort="trendingScore", french=False):
    """Recherche unifiée avec cache court et réutilisation en mode hors ligne."""
    key = (source, query.strip(), category, sort, bool(french))
    now = time.monotonic()
    previous = _SEARCH_CACHE.get(key)
    if previous and (now - previous[0] < _SEARCH_TTL or settings.get("offline_mode")):
        return list(previous[1])
    if settings.get("offline_mode"):
        saved = _load_search_disk().get("|".join(map(str, key)))
        if saved and isinstance(saved.get("results"), list):
            _SEARCH_CACHE[key] = (now, saved["results"])
            return list(saved["results"])
        raise RuntimeError("Mode hors ligne : aucune recherche en cache pour cette requête.")
    loaders = {"github": lambda: search_github(query), "modelscope": lambda: search_modelscope(query),
               "civitai": lambda: search_civitai(query),
               "huggingface": lambda: search_hf(query, category, sort, french)}
    value = loaders[source]()
    _SEARCH_CACHE[key] = (now, value)
    _save_search_disk(key, value)
    return value


def export_details(path: str, details: Dict) -> str:
    """Exporte une fiche sans clé, jeton ou contenu sensible."""
    safe = {k: v for k, v in details.items() if k not in {"readme"}}
    target = __import__("pathlib").Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def cached_details(source: str, repo: str, timeout: int = 20) -> Dict:
    """Fiche mise en cache 60 secondes pour éviter les requêtes répétées."""
    key = (source, repo)
    now = time.monotonic()
    previous = _DETAIL_CACHE.get(key)
    if previous and now - previous[0] < _DETAIL_TTL:
        return dict(previous[1])
    loaders = {"github": github_details, "modelscope": modelscope_details,
               "civitai": civitai_details, "huggingface": model_details}
    value = loaders[source](repo, timeout)
    _DETAIL_CACHE[key] = (now, value)
    return value


def github_headers() -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = str(settings.get("github_token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def civitai_headers() -> Dict[str, str]:
    token = str(settings.get("civitai_token") or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def modelscope_headers() -> Dict[str, str]:
    token = str(settings.get("modelscope_token") or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}

SORTS = {
    "🔥 Tendances": "trendingScore",
    "⬇ Plus téléchargés": "downloads",
    "♥ Plus aimés": "likes",
    "🆕 Plus récents": "lastModified",
}
CATEGORIES = {
    "Toutes": None,
    "💬 Texte / discussion": "text-generation",
    "🖼️ Images (vision)": "image-text-to-text",
}
SUGGESTIONS = [
    ("💻 Code", "coder"),
    ("🧠 Raisonnement", "r1"),
    ("🇫🇷 Français", "french"),
    ("🪶 Petits", "1b"),
    ("🦙 Llama", "llama"),
    ("🌬️ Mistral", "mistral"),
    ("💎 Gemma", "gemma"),
    ("🐉 Qwen", "qwen"),
    ("🔓 Sans censure", "uncensored"),
    ("✍️ Roman / rôle", "roleplay"),
]

QUANT_RE = re.compile(r"(?<![A-Za-z0-9])((?:UD-)?IQ\d_[A-Z0-9]+(?:_[A-Z]+)?|(?:UD-)?Q\d_K(?:_[SML]|_XL)?|Q\d_\d|Q\d|BF16|F16|F32|FP16)(?![A-Za-z0-9])",
                      re.IGNORECASE)
SPLIT_RE = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)

# Qualité relative des quantifications (plus grand = plus fidèle, mais plus lourd)
QUANT_QUALITY = {"Q2_K": 1, "IQ2": 1, "Q3_K_S": 2, "Q3_K_M": 2, "Q3_K_L": 3, "IQ3": 2, "IQ4_XS": 4,
                 "IQ4_NL": 4, "Q4_0": 4, "Q4_K_S": 4, "Q4_K_M": 5, "Q4_K_XL": 5, "Q5_0": 5, "Q5_K_S": 6,
                 "Q5_K_M": 6, "Q6_K": 7, "Q8_0": 8, "BF16": 9, "F16": 9, "FP16": 9, "F32": 10}


def human_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n / 1_000:.0f} k"
    return str(n)


def fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        return ""


def search_hf(query: str = "", category: Optional[str] = None, sort: str = "trendingScore",
              french: bool = False, limit: int = 40, timeout: int = 20) -> List[Dict]:
    """Recherche des modèles GGUF (lève une exception si le réseau échoue)"""
    params: List[tuple] = [("filter", "gguf"), ("sort", sort), ("direction", "-1"), ("limit", str(limit))]
    if query.strip():
        params.append(("search", query.strip()))
    if category:
        params.append(("pipeline_tag", category))
    if french:
        params.append(("filter", "fr"))
    r = requests.get(HF_API, params=params, timeout=timeout)
    r.raise_for_status()
    return [parse_listing(m) for m in r.json()]


def search_github(query: str = "", limit: int = 30, timeout: int = 20) -> List[Dict]:
    """Recherche des dépôts GitHub qui publient des modèles ou des fichiers GGUF."""
    terms = (query.strip() + " gguf").strip() if query.strip() else "gguf language model"
    r = requests.get(f"{GITHUB_API}/search/repositories",
                     params={"q": terms, "sort": "stars", "order": "desc", "per_page": limit},
                     headers=github_headers(), timeout=timeout)
    if r.status_code == 403:
        raise RuntimeError("Limite GitHub atteinte. Ajoutez un jeton facultatif dans Connexions, puis réessayez.")
    r.raise_for_status()
    return [parse_github_listing(item) for item in r.json().get("items", [])]


def search_modelscope(query: str = "", limit: int = 30, timeout: int = 20) -> List[Dict]:
    """Recherche publique ModelScope. Les modèles non-GGUF restent consultables mais non installés dans Ollama."""
    r = requests.get(MODELSCOPE_API, params={"search": query.strip(), "sort": "downloads", "page_size": limit},
                     headers=modelscope_headers(), timeout=timeout)
    r.raise_for_status()
    payload = r.json().get("data") or {}
    return [parse_modelscope_listing(item) for item in (payload.get("models") or payload.get("Models") or [])]


def parse_modelscope_listing(item: Dict) -> Dict:
    repo = item.get("id") or item.get("Path") or item.get("path") or ""
    return {"id": repo, "name": repo.split("/")[-1], "author": repo.split("/")[0] if "/" in repo else "",
            "downloads": int(item.get("downloads") or item.get("Downloads") or 0),
            "likes": int(item.get("likes") or item.get("Likes") or 0),
            "updated": item.get("last_modified") or item.get("LastModified") or "",
            "description": item.get("description") or item.get("Description") or "",
            "pipeline": "modelscope", "gated": False, "tags": item.get("tags") or []}


def modelscope_details(repo: str, timeout: int = 20) -> Dict:
    r = requests.get(f"{MODELSCOPE_API}/{repo}", headers=modelscope_headers(), timeout=timeout)
    r.raise_for_status()
    data = r.json().get("data") or {}
    if isinstance(data, list):
        data = data[0] if data else {}
    item = parse_modelscope_listing(data)
    item.update({"license": data.get("license", ""), "base_model": "", "architecture": "",
                 "context": 0, "params": 0, "languages": [], "readme": data.get("description", ""),
                 "quants": [], "html_url": f"{MODELSCOPE_SITE}/{repo}"})
    return item


def search_civitai(query: str = "", limit: int = 30, timeout: int = 20) -> List[Dict]:
    """Recherche publique Civitai pour modèles image, LoRA, VAE et embeddings."""
    r = requests.get(CIVITAI_API, params={"query": query.strip(), "limit": min(limit, 100),
                                          "sort": "Most Downloaded", "nsfw": "false"},
                     headers=civitai_headers(), timeout=timeout)
    r.raise_for_status()
    return [parse_civitai_listing(item) for item in (r.json().get("items") or [])]


def parse_civitai_listing(item: Dict) -> Dict:
    model_id = str(item.get("id", ""))
    return {"id": model_id, "name": item.get("name", model_id), "author": (item.get("creator") or {}).get("username", ""),
            "downloads": int(item.get("stats", {}).get("downloadCount") or 0),
            "likes": int(item.get("stats", {}).get("favoriteCount") or 0), "updated": item.get("updatedAt", ""),
            "description": item.get("description", "") or "", "type": item.get("type", ""),
            "pipeline": "civitai", "gated": False, "tags": item.get("tags") or []}


def civitai_details(model_id: str, timeout: int = 20) -> Dict:
    r = requests.get(f"{CIVITAI_API}/{model_id}", headers=civitai_headers(), timeout=timeout)
    r.raise_for_status()
    item = parse_civitai_listing(r.json())
    files = []
    for version in r.json().get("modelVersions", []) or []:
        for file in version.get("files", []) or []:
            name = file.get("name", "")
            if name.lower().endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".zip")):
                files.append({"quant": name, "asset": name, "size": int(file.get("sizeKB") or 0) * 1024,
                              "split": False, "download_url": file.get("downloadUrl", ""),
                              "version": version.get("name", "")})
    item.update({"license": "", "base_model": "", "architecture": "", "context": 0, "params": 0,
                 "languages": [], "readme": item.get("description", ""), "quants": files,
                 "html_url": f"{CIVITAI_SITE}/{model_id}"})
    return item


def download_civitai_file(asset: Dict, timeout: int = 60, on_progress=None, should_stop=None) -> str:
    from pathlib import Path
    target_dir = storage.app_models() / "image_downloads"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", asset.get("asset", "model.bin"))
    target = target_dir / safe
    if target.exists() and asset.get("size") and target.stat().st_size == asset["size"]:
        return str(target)
    part = target.with_suffix(target.suffix + ".part")
    current = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={current}-"} if current else {}
    headers.update(civitai_headers())
    with requests.get(asset["download_url"], stream=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()
        append = current > 0 and r.status_code == 206
        if not append: current = 0
        total = current + int(r.headers.get("Content-Length") or asset.get("size") or 0)
        with part.open("ab" if append else "wb") as out:
            done = current
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if should_stop and should_stop():
                    raise InterruptedError("Téléchargement annulé. Relancez pour reprendre.")
                if chunk:
                    out.write(chunk); done += len(chunk)
                    if on_progress: on_progress(done, total)
    if asset.get("size") and part.stat().st_size != asset["size"]:
        raise RuntimeError("Téléchargement Civitai incomplet.")
    part.replace(target)
    return str(target)


def parse_github_listing(item: Dict) -> Dict:
    return {"id": item.get("full_name", ""), "name": item.get("name", ""),
            "author": (item.get("owner") or {}).get("login", ""),
            "downloads": int(item.get("stargazers_count") or 0),
            "likes": int(item.get("forks_count") or 0), "updated": item.get("updated_at", ""),
            "description": item.get("description") or "", "html_url": item.get("html_url", ""),
            "pipeline": "github", "gated": False, "tags": item.get("topics", [])}


def github_details(repo: str, timeout: int = 20) -> Dict:
    """Retourne les assets GGUF des releases GitHub, installables dans Ollama."""
    headers = github_headers()
    rr = requests.get(f"{GITHUB_API}/repos/{repo}/releases", params={"per_page": 10},
                      headers=headers, timeout=timeout)
    rr.raise_for_status()
    assets = []
    for release in rr.json():
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".gguf") and "mmproj" not in name.lower():
                assets.append({"quant": quant_of(name) or "GGUF", "size": int(asset.get("size") or 0),
                               "files": [name], "split": bool(SPLIT_RE.search(name)),
                               "download_url": asset.get("browser_download_url", ""),
                               "asset": name, "release": release.get("tag_name", ""),
                               "digest": asset.get("digest", "")})
    return {"id": repo, "author": repo.split("/")[0], "license": "", "base_model": "",
            "architecture": "", "context": 0, "params": 0, "languages": [], "pipeline": "github",
            "downloads": 0, "likes": 0, "updated": "", "gated": False, "readme": "",
            "quants": assets, "html_url": f"{GITHUB_SITE}/{repo}"}


def download_github_gguf(repo: str, asset: Dict, timeout: int = 60, on_progress=None, should_stop=None) -> str:
    """Télécharge un asset GGUF dans le cache local et renvoie son chemin."""
    from pathlib import Path
    target_dir = storage.app_models() / "downloads"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{repo.replace('/', '_')}_{asset['asset']}")
    target = target_dir / safe
    expected = int(asset.get("size") or 0)
    part = target.with_suffix(target.suffix + ".part")
    current = part.stat().st_size if part.exists() else 0
    if target.exists() and (not expected or target.stat().st_size == expected):
        return str(target)
    headers = {"Accept": "application/octet-stream"}
    if current:
        headers["Range"] = f"bytes={current}-"
    with requests.get(asset["download_url"], stream=True, timeout=timeout, headers=headers) as r:
            r.raise_for_status()
            # Certains serveurs ignorent Range et renvoient 200 : on repart alors proprement.
            append = current > 0 and r.status_code == 206
            if not append:
                current = 0
            total = current + int(r.headers.get("Content-Length") or expected or 0)
            mode = "ab" if append else "wb"
            with part.open(mode) as out:
                done = current
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if should_stop and should_stop():
                        raise InterruptedError("Téléchargement annulé. Relancez pour reprendre.")
                    if chunk:
                        out.write(chunk)
                        done += len(chunk)
                        if on_progress:
                            on_progress(done, total)
            if expected and part.stat().st_size != expected:
                raise RuntimeError(f"Téléchargement incomplet : {part.stat().st_size} / {expected} octets.")
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:"):
                checksum = hashlib.sha256(part.read_bytes()).hexdigest()
                if checksum.lower() != digest.split(":", 1)[1].lower():
                    raise RuntimeError("Vérification SHA-256 échouée : fichier supprimé.")
            part.replace(target)
    return str(target)


def parse_listing(m: Dict) -> Dict:
    repo = m.get("id") or m.get("modelId", "")
    return {
        "id": repo,
        "name": repo.split("/")[-1],
        "author": m.get("author") or repo.split("/")[0],
        "downloads": int(m.get("downloads") or 0),
        "likes": int(m.get("likes") or 0),
        "updated": m.get("lastModified", ""),
        "pipeline": m.get("pipeline_tag") or "",
        "gated": bool(m.get("gated")),
        "tags": m.get("tags", []),
    }


def quant_of(filename: str) -> Optional[str]:
    base = SPLIT_RE.sub(".gguf", filename)
    matches = QUANT_RE.findall(base)
    return matches[-1].upper() if matches else None


def group_gguf_files(siblings: List[Dict]) -> List[Dict]:
    """Regroupe les fichiers .gguf par quantification (les fichiers découpés sont additionnés)"""
    groups: Dict[str, Dict] = {}
    for s in siblings:
        name = s.get("rfilename", "")
        low = name.lower()
        if not low.endswith(".gguf") or "mmproj" in low or "/imatrix" in low or "imatrix" in low.split("/")[-1]:
            continue
        q = quant_of(name.split("/")[-1])
        if not q:
            continue
        size = int(s.get("size") or (s.get("lfs") or {}).get("size") or 0)
        split = bool(SPLIT_RE.search(name))
        g = groups.setdefault(q, {"quant": q, "size": 0, "files": [], "split": False})
        g["size"] += size
        g["files"].append(name)
        g["split"] = g["split"] or split
    ordered = sorted(groups.values(), key=lambda g: (g["size"] or 0))
    for g in ordered:
        plain = g["quant"].replace("UD-", "")
        g["quality"] = QUANT_QUALITY.get(plain) or next(
            (v for k, v in QUANT_QUALITY.items() if plain.startswith(k)), 4)
    return ordered


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def model_details(repo: str, timeout: int = 20) -> Dict:
    """Fiche détaillée : versions GGUF disponibles (taille), contexte, licence, extrait du README"""
    r = requests.get(f"{HF_API}/{repo}", params={"blobs": "true"}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    gguf = data.get("gguf") or {}
    card = data.get("cardData") or {}
    base = card.get("base_model")
    if isinstance(base, list):
        base = ", ".join(base[:2])
    details = {
        "id": data.get("id", repo),
        "author": data.get("author", repo.split("/")[0]),
        "downloads": int(data.get("downloads") or 0),
        "likes": int(data.get("likes") or 0),
        "updated": data.get("lastModified", ""),
        "pipeline": data.get("pipeline_tag") or "",
        "license": card.get("license") or "",
        "base_model": base or "",
        "languages": card.get("language") or [],
        "architecture": gguf.get("architecture", ""),
        "context": gguf.get("context_length") or 0,
        "params": gguf.get("total") or 0,
        "gated": bool(data.get("gated")),
        "quants": group_gguf_files(data.get("siblings", [])),
        "readme": "",
    }
    if isinstance(details["languages"], str):
        details["languages"] = [details["languages"]]
    try:
        rr = requests.get(f"{HF_SITE}/{repo}/raw/main/README.md", timeout=timeout)
        if rr.status_code == 200:
            details["readme"] = strip_front_matter(rr.text)[:2500]
    except requests.RequestException:
        pass
    return details


def fit_for_size(size_bytes: int, info: Optional[Dict]) -> str:
    """'gpu', 'mixed', 'cpu' ou 'no' (même logique que le catalogue)"""
    need = size_bytes / (1024 ** 3) * 1.2
    if not info:
        return "mixed"
    vram = max(0.0, info.get("vram_gb", 0.0) - 0.5)
    ram = info.get("ram_gb", 0.0) * 0.6
    if vram > 0 and need <= vram:
        return "gpu"
    if need <= vram + ram:
        return "mixed" if vram > 0 else "cpu"
    return "no"


def best_quant(quants: List[Dict], info: Optional[Dict]) -> Optional[str]:
    """Version conseillée : la plus fidèle qui tient en VRAM, sinon Q4_K_M, sinon la plus petite qui tourne"""
    usable = [q for q in quants if not q["split"] and q["size"]]
    if not usable:
        return None
    in_gpu = [q for q in usable if fit_for_size(q["size"], info) == "gpu" and 4 <= q["quality"] <= 8]
    if in_gpu:
        return max(in_gpu, key=lambda q: (q["quality"], q["size"]))["quant"]
    q4 = next((q for q in usable if q["quant"] == "Q4_K_M" and fit_for_size(q["size"], info) != "no"), None)
    if q4:
        return q4["quant"]
    runnable = [q for q in usable if fit_for_size(q["size"], info) != "no"]
    return min(runnable, key=lambda q: q["size"])["quant"] if runnable else None


def ollama_name(repo: str, quant: str) -> str:
    return f"hf.co/{repo}:{quant}"


def readable_params(n: int) -> str:
    if not n:
        return ""
    if n >= 1e9:
        return f"{n / 1e9:.1f} milliards".replace(".0 ", " ")
    return f"{n / 1e6:.0f} millions"
