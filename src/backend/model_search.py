"""Moteur de recherche d'IA : explore les modèles GGUF publiés sur Hugging Face
(plus de 100 000 modèles), puis les télécharge dans Ollama (hf.co/depot:quantification)."""

import re
from datetime import datetime
from typing import Dict, List, Optional

import requests

HF_API = "https://huggingface.co/api/models"
HF_SITE = "https://huggingface.co"

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
