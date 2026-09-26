"""Test de vitesse : estimations détaillées (façon llmfit) et mesures réelles.

ESTIMATION (sans lancer le modèle)
  mémoire  = poids + cache de conversation (KV) + surcoût de calcul
  mode     = GPU (tout en VRAM) · MoE (experts actifs en VRAM) · CPU+GPU (débordement en RAM)
             · CPU (tout en RAM) · Trop juste (ne tient pas)
  vitesse  = 0,55 × bande passante mémoire ÷ gigaoctets lus pour produire un token
             (le calcul d'un token relit tous les poids actifs : la vitesse dépend surtout de la
              bande passante de la mémoire où ils se trouvent)
  scores   = qualité, vitesse, ajustement, contexte (0-100) puis score global pondéré selon l'usage
Chaque estimation garde la liste de ses données de départ (« base de calcul »).

MESURE (en lançant le modèle)
  Ollama    : /api/generate renvoie durées de chargement, de lecture du message et d'écriture.
  LM Studio : /api/v1/chat renvoie tokens/s, temps avant le premier token, temps de chargement.
"""

import math
import platform
import re
import time
from datetime import datetime
from functools import lru_cache
from typing import Callable, Dict, List, Optional

import requests

from src.backend import settings

OLLAMA_URL = "http://localhost:11434"
EFFICIENCY = 0.55
OVERHEAD_GB = 0.5
GIB = 1024 ** 3

BENCH_PROMPT = (
    "Voici un court texte : « Les modèles de langage prédisent le mot suivant à partir des mots "
    "précédents. Leur vitesse dépend surtout de la mémoire de l'ordinateur et de la carte graphique. »\n"
    "Explique en français, en environ 150 mots, pourquoi la bande passante mémoire limite la vitesse "
    "d'écriture d'une IA locale."
)
BENCH_TOKENS = 200

USAGES = {
    "chat": {"label": "💬 Discussion", "ctx": 8192,
             "weights": {"quality": 0.25, "speed": 0.35, "fit": 0.25, "context": 0.15}},
    "code": {"label": "💻 Code", "ctx": 32768,
             "weights": {"quality": 0.40, "speed": 0.20, "fit": 0.20, "context": 0.20}},
    "reasoning": {"label": "🧠 Raisonnement", "ctx": 16384,
                  "weights": {"quality": 0.55, "speed": 0.15, "fit": 0.15, "context": 0.15}},
}

FIT_LABELS = {"perfect": "🟢 Parfait", "good": "🟡 Bon", "marginal": "🟠 Juste", "too_tight": "🔴 Trop juste"}
MODE_LABELS = {"gpu": "GPU", "moe": "MoE (experts en VRAM)", "cpu_gpu": "CPU+GPU", "cpu": "CPU",
               "none": "—"}

# Bits réellement stockés par poids pour chaque quantification (moyennes llama.cpp)
QUANT_BITS = {
    "F32": 32.0, "F16": 16.0, "BF16": 16.0, "Q8_0": 8.5, "Q6_K": 6.56, "Q5_K_M": 5.69, "Q5_K_S": 5.54,
    "Q5_1": 6.0, "Q5_0": 5.5, "Q4_K_M": 4.85, "Q4_K_S": 4.58, "Q4_1": 5.0, "Q4_0": 4.55,
    "IQ4_NL": 4.5, "IQ4_XS": 4.25, "Q3_K_L": 4.27, "Q3_K_M": 3.91, "Q3_K_S": 3.5, "IQ3_M": 3.66,
    "IQ3_XS": 3.3, "IQ3_XXS": 3.06, "Q2_K": 3.35, "IQ2_M": 2.7, "IQ2_XS": 2.31, "IQ1_M": 1.75,
    "MXFP4": 4.25,
}

# Bande passante mémoire des cartes graphiques courantes (Go/s, fiches constructeur)
GPU_BANDWIDTH = {
    "rtx 5090": 1792, "rtx 5080": 960, "rtx 5070 ti": 896, "rtx 5070": 672, "rtx 5060 ti": 448,
    "rtx 5060": 448, "rtx 4090": 1008, "rtx 4080 super": 736, "rtx 4080": 717,
    "rtx 4070 ti super": 672, "rtx 4070 ti": 504, "rtx 4070 super": 504, "rtx 4070": 504,
    "rtx 4060 ti": 288, "rtx 4060": 272, "rtx 3090 ti": 1008, "rtx 3090": 936, "rtx 3080 ti": 912,
    "rtx 3080": 760, "rtx 3070 ti": 608, "rtx 3070": 448, "rtx 3060 ti": 448, "rtx 3060": 360,
    "rtx 3050": 224, "rtx 2080 ti": 616, "rtx 2080 super": 496, "rtx 2080": 448,
    "rtx 2070 super": 448, "rtx 2070": 448, "rtx 2060 super": 448, "rtx 2060": 336,
    "gtx 1660 ti": 288, "gtx 1660 super": 336, "gtx 1660": 192, "gtx 1650": 128,
    "gtx 1080 ti": 484, "gtx 1080": 320, "gtx 1070": 256, "gtx 1060": 192,
    "rtx a6000": 768, "rtx a5000": 768, "rtx a4000": 448, "tesla t4": 320, "a100": 1555,
    "rx 9070 xt": 640, "rx 9070": 640, "rx 9060 xt": 320, "rx 7900 xtx": 960, "rx 7900 xt": 800,
    "rx 7900 gre": 576, "rx 7800 xt": 624, "rx 7700 xt": 432, "rx 7600 xt": 288, "rx 7600": 288,
    "rx 6950 xt": 576, "rx 6900 xt": 512, "rx 6800 xt": 512, "rx 6800": 512, "rx 6750 xt": 432,
    "rx 6700 xt": 384, "rx 6650 xt": 280, "rx 6600 xt": 256, "rx 6600": 224, "rx 6500 xt": 144,
    "rx 5700 xt": 448, "rx 580": 256, "arc b580": 456, "arc b570": 380, "arc a770": 560,
    "arc a750": 512, "arc a580": 512, "arc a380": 186,
}
VENDOR_FALLBACK_BW = {"NVIDIA": 300, "AMD": 250, "Intel": 150}


# ------------------------------------------------------------------ matériel
def gpu_bandwidth(name: str, vendor: str) -> Dict:
    low = (name or "").lower()
    for key in sorted(GPU_BANDWIDTH, key=len, reverse=True):
        if key in low:
            bw = float(GPU_BANDWIDTH[key])
            if "laptop" in low or "mobile" in low or " max-q" in low:
                return {"gbps": bw * 0.7, "source": f"table ({key.upper()}, version portable ≈ 70 %)"}
            return {"gbps": bw, "source": f"table ({key.upper()})"}
    fb = VENDOR_FALLBACK_BW.get(vendor)
    if fb:
        return {"gbps": float(fb), "source": f"carte inconnue : valeur moyenne {vendor}"}
    return {"gbps": 0.0, "source": "aucune carte graphique utilisable"}


@lru_cache(maxsize=1)
def ram_bandwidth() -> Dict:
    """Bande passante de la RAM : vitesse des barrettes × 8 octets × nombre de canaux"""
    if platform.system() == "Windows":
        from src.backend.system_analyzer import _run
        out = _run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_PhysicalMemory | ForEach-Object { "
                    "\"$($_.ConfiguredClockSpeed)|$($_.Speed)|$($_.SMBIOSMemoryType)\" }"])
        speeds, types = [], []
        for line in out.splitlines():
            parts = line.strip().split("|")
            if len(parts) == 3:
                try:
                    speeds.append(int(parts[0] or 0) or int(parts[1] or 0))
                    types.append(int(parts[2] or 0))
                except ValueError:
                    pass
        speeds = [s for s in speeds if s > 0]
        if speeds:
            mts = min(speeds)
            channels = 2 if len(speeds) >= 2 else 1
            kind = {34: "DDR5", 26: "DDR4", 24: "DDR3"}.get(max(types) if types else 0, "DDR")
            gbps = mts * 8 * channels / 1000
            return {"gbps": gbps, "source": f"{kind}-{mts} × {channels} canal{'aux' if channels > 1 else ''} "
                                            f"({len(speeds)} barrette{'s' if len(speeds) > 1 else ''})"}
    return {"gbps": 40.0, "source": "valeur par défaut (DDR4 double canal)"}


def hardware_profile(info: Optional[Dict]) -> Dict:
    info = info or {}
    vram = float(info.get("vram_gb") or 0)
    gpu = gpu_bandwidth(info.get("gpu_type", ""), info.get("gpu_vendor", "")) if vram > 0 else \
        {"gbps": 0.0, "source": "aucune carte graphique utilisable"}
    ram_total = float(info.get("ram_gb") or 0)
    pct = int(settings.get("vram_percent") or 90)
    return {
        "gpu_name": info.get("gpu_type", "Aucun GPU"),
        "vram_gb": vram,
        "vram_budget_gb": max(0.0, vram * pct / 100 - 0.3) if vram else 0.0,
        "vram_percent": pct,
        "gpu_bw": gpu["gbps"], "gpu_bw_source": gpu["source"],
        "ram_gb": ram_total,
        "ram_budget_gb": max(0.0, ram_total - 4.0),  # on laisse ~4 Go à Windows et aux logiciels
        "ram_bw": ram_bandwidth()["gbps"], "ram_bw_source": ram_bandwidth()["source"],
        "cpu_count": info.get("cpu_count", 0),
    }


# ------------------------------------------------------------------ modèles
def parse_params(text) -> Dict:
    """« 8.2B », « 26B-A4B », « 3 milliards », « 135M », 8190735360 → milliards de paramètres"""
    if isinstance(text, (int, float)) and text:
        return {"total": float(text) / 1e9, "active": None}
    s = str(text or "").lower().replace(",", ".")
    moe = re.search(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*b", s)
    if moe:
        return {"total": float(moe.group(1)) * float(moe.group(2)), "active": None}
    vals = []
    for n, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(milliards?|millions?|b|m)?", s):
        v = float(n)
        if unit in ("m", "million", "millions"):
            v /= 1000
        vals.append(v)
    if not vals:
        return {"total": 0.0, "active": None}
    act = re.search(r"(\d+(?:\.\d+)?)\s*(?:milliards?\s*)?(?:actifs|effectifs)", s)
    if act:
        return {"total": vals[0], "active": float(act.group(1))}
    if len(vals) >= 2 and re.search(r"a\s*\d", s):
        return {"total": vals[0], "active": vals[1]}
    return {"total": vals[0], "active": None}


def quant_bits(quant: str, bits: Optional[float] = None) -> float:
    q = (quant or "").upper()
    if q in QUANT_BITS:
        return QUANT_BITS[q]
    for key in sorted(QUANT_BITS, key=len, reverse=True):
        if key in q:
            return QUANT_BITS[key]
    if bits:
        return float(bits) + 0.5
    return 4.85


def ollama_profile(model: str, timeout: int = 10) -> Dict:
    """Tout ce qu'Ollama sait d'un modèle installé : taille, paramètres, quantification, couches…"""
    prof = {"ref": f"ollama::{model}", "source": "ollama", "name": model, "size_gb": 0.0,
            "params_b": 0.0, "active_b": None, "quant": "", "bits": None, "layers": 0, "kv_heads": 0,
            "head_dim": 0, "max_ctx": 0, "arch": "", "experts": 0, "experts_used": 0, "installed": True}
    try:
        for m in requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout).json().get("models", []):
            if m.get("name") == model or m.get("model") == model:
                prof["size_gb"] = (m.get("size") or 0) / GIB
                d = m.get("details") or {}
                prof["quant"] = d.get("quantization_level", "")
                prof["arch"] = d.get("family", "")
                p = parse_params(d.get("parameter_size", ""))
                prof["params_b"] = p["total"]
        show = requests.post(f"{OLLAMA_URL}/api/show", json={"model": model, "name": model},
                             timeout=timeout).json()
        d = show.get("details") or {}
        prof["quant"] = d.get("quantization_level") or prof["quant"]
        info = show.get("model_info") or {}
        heads = emb = key_len = 0
        for key, value in info.items():
            if not isinstance(value, (int, float)):
                continue
            if key == "general.parameter_count":
                prof["params_b"] = value / 1e9
            elif key.endswith(".block_count"):
                prof["layers"] = int(value)
            elif key.endswith(".context_length"):
                prof["max_ctx"] = int(value)
            elif key.endswith(".attention.head_count_kv"):
                prof["kv_heads"] = int(value)
            elif key.endswith(".attention.head_count"):
                heads = int(value)
            elif key.endswith(".embedding_length"):
                emb = int(value)
            elif key.endswith(".attention.key_length"):
                key_len = int(value)
            elif key.endswith(".expert_count"):
                prof["experts"] = int(value)
            elif key.endswith(".expert_used_count"):
                prof["experts_used"] = int(value)
        prof["head_dim"] = key_len or (emb // heads if heads else 0)
        if prof["experts"] and prof["experts_used"] and prof["params_b"]:
            # approximation : ~90 % des poids sont dans les experts, le reste est partagé
            share = prof["experts_used"] / prof["experts"]
            prof["active_b"] = prof["params_b"] * (0.1 + 0.9 * share)
    except Exception:
        pass
    return prof


def lmstudio_profile(m: Dict, provider_id: str = "lmstudio") -> Dict:
    p = parse_params(m.get("params", ""))
    return {"ref": f"{provider_id}::{m['key']}", "source": "lmstudio", "name": m.get("name") or m["key"],
            "size_gb": (m.get("size_bytes") or 0) / GIB, "params_b": p["total"], "active_b": p["active"],
            "quant": m.get("quant", ""), "bits": m.get("bits"), "layers": 0, "kv_heads": 0, "head_dim": 0,
            "max_ctx": m.get("max_ctx") or 0, "arch": m.get("arch", ""), "experts": 0, "experts_used": 0,
            "installed": True, "key": m["key"]}


# Paramètres actifs par token de modèles MoE connus (milliards), quand le catalogue ne les donne pas
KNOWN_ACTIVE = {"deepseek-coder-v2": 2.4, "gpt-oss:20b": 3.6, "gpt-oss:120b": 5.1, "mixtral": 12.9,
                "qwen3:30b": 3.3, "qwen3-coder:30b": 3.3}


def catalog_profile(entry: Dict) -> Dict:
    p = parse_params(entry.get("params", ""))
    if p["active"] is None:
        for key, act in KNOWN_ACTIVE.items():
            if entry["id"].startswith(key):
                p["active"] = act
    ctx_text = str(entry.get("context", "")).lower().replace(" ", "")
    ctx = 0
    mk = re.match(r"(\d+)k", ctx_text)
    if mk:
        ctx = int(mk.group(1)) * 1024
    return {"ref": f"ollama::{entry['id']}", "source": "catalogue", "name": entry["id"],
            "size_gb": float(entry.get("size_gb") or 0), "params_b": p["total"], "active_b": p["active"],
            "quant": "Q4_K_M", "bits": None, "layers": 0, "kv_heads": 0, "head_dim": 0, "max_ctx": ctx,
            "arch": "", "experts": 0, "experts_used": 0, "installed": False,
            "stars": entry.get("quality"), "category": entry.get("category")}


# ------------------------------------------------------------------ estimation
def kv_cache_gb(prof: Dict, ctx: int) -> Dict:
    if prof.get("layers") and prof.get("kv_heads") and prof.get("head_dim"):
        gb = 2 * prof["layers"] * prof["kv_heads"] * prof["head_dim"] * 2 * ctx / GIB
        return {"gb": gb, "basis": f"{prof['layers']} couches × {prof['kv_heads']} têtes KV × "
                                   f"{prof['head_dim']} × 2 (clé+valeur) × 2 octets × {ctx} tokens"}
    gb = (prof.get("size_gb") or 0) * 0.2 * ctx / 8192
    return {"gb": gb, "basis": f"approximation : 20 % des poids pour 8192 tokens, ramené à {ctx} tokens"}


def quality_score(prof: Dict) -> float:
    params = prof.get("params_b") or 0
    base = 20 + 18 * math.log2(params + 1) if params else 40   # 1B→38 · 8B→77 · 32B→110 (plafonné)
    base = min(base, 100)
    if prof.get("stars"):
        base = 0.5 * base + 0.5 * prof["stars"] * 20
    bits = quant_bits(prof.get("quant", ""), prof.get("bits"))
    penalty = 0 if bits >= 6 else 1 if bits >= 5 else 3 if bits >= 4.2 else 8 if bits >= 3.4 else 15
    return max(0.0, min(100.0, base - penalty))


def speed_score(tps: float) -> float:
    return 0.0 if tps <= 0 else min(100.0, 100 * math.log(1 + tps) / math.log(41))


def estimate(prof: Dict, hw: Dict, ctx: int, usage: str = "chat") -> Dict:
    ctx = min(ctx, prof["max_ctx"]) if prof.get("max_ctx") else ctx
    weights = prof.get("size_gb") or 0.0
    kv = kv_cache_gb(prof, ctx)
    total = weights + kv["gb"] + OVERHEAD_GB if weights else 0.0
    active_share = 1.0
    if prof.get("active_b") and prof.get("params_b"):
        active_share = max(0.05, min(1.0, prof["active_b"] / prof["params_b"]))
    active_gb = weights * active_share

    vbud, rbud = hw["vram_budget_gb"], hw["ram_budget_gb"]
    if not total:
        mode, gpu_share = "none", 0.0
    elif vbud and total <= vbud:
        mode, gpu_share = "gpu", 1.0
    elif vbud and active_share < 1 and active_gb + kv["gb"] + OVERHEAD_GB <= vbud and total <= vbud + rbud:
        # MoE : seuls les experts utilisés sont lus à chaque token. Ollama répartit les couches
        # entre VRAM et RAM : une partie des experts lus est donc en RAM, au prorata.
        mode, gpu_share = "moe", max(0.0, min(1.0, vbud / total))
    elif vbud and total <= vbud + rbud:
        mode, gpu_share = "cpu_gpu", max(0.0, min(1.0, vbud / total))
    elif total <= rbud:
        mode, gpu_share = "cpu", 0.0
    else:
        mode, gpu_share = "none", 0.0

    fits = mode != "none"
    if not total:
        fit = "too_tight"
    elif mode == "gpu":
        fit = "perfect" if total <= vbud * 0.9 else "good"
    elif mode == "moe" or (mode == "cpu_gpu" and gpu_share >= 0.7):
        fit = "good"
    elif fits:
        fit = "marginal"
    else:
        fit = "too_tight"

    tps, speed_basis = 0.0, ""
    if fits:
        read_gpu = active_gb * gpu_share
        read_ram = active_gb * (1 - gpu_share)
        seconds = 0.0
        if read_gpu and hw["gpu_bw"]:
            seconds += read_gpu / hw["gpu_bw"]
        if read_ram and hw["ram_bw"]:
            seconds += read_ram / hw["ram_bw"]
        tps = EFFICIENCY / seconds if seconds else 0.0
        speed_basis = (f"{EFFICIENCY} × 1 ÷ ({read_gpu:.2f} Go ÷ {hw['gpu_bw']:.0f} Go/s VRAM + "
                       f"{read_ram:.2f} Go ÷ {hw['ram_bw']:.0f} Go/s RAM)")

    pool = vbud if mode == "gpu" else (vbud + rbud)
    util = total / pool if pool else 0
    fit_score = (0 if not fits else
                 100 if mode == "gpu" and 0.5 <= util <= 0.8 else
                 90 if mode == "gpu" and util < 0.5 else
                 75 if mode == "gpu" else 65 if mode == "moe" else
                 35 + 30 * gpu_share if mode == "cpu_gpu" else 25)
    need_ctx = USAGES.get(usage, USAGES["chat"])["ctx"]
    ctx_score = min(100.0, 100 * (prof.get("max_ctx") or 4096) / need_ctx)
    scores = {"quality": quality_score(prof), "speed": speed_score(tps), "fit": float(fit_score),
              "context": ctx_score}
    w = USAGES.get(usage, USAGES["chat"])["weights"]
    overall = sum(scores[k] * w[k] for k in w) if fits else 0.0

    bits = quant_bits(prof.get("quant", ""), prof.get("bits"))
    basis = [
        f"Poids : {weights:.2f} Go · {prof.get('quant') or 'quantification inconnue'} ≈ {bits:.2f} bits par "
        f"poids · {prof.get('params_b') or 0:.1f} milliards de paramètres"
        + (f" (dont {prof['active_b']:.1f} actifs par token, MoE)" if prof.get("active_b") else ""),
        f"Cache de conversation : {kv['gb']:.2f} Go ({kv['basis']})",
        f"Surcoût de calcul : {OVERHEAD_GB} Go · total nécessaire {total:.2f} Go",
        f"VRAM utilisable : {vbud:.1f} Go ({hw['vram_percent']} % de {hw['vram_gb']:.1f} Go) · "
        f"RAM utilisable : {rbud:.1f} Go (4 Go laissés au système)",
        f"Bande passante VRAM : {hw['gpu_bw']:.0f} Go/s — {hw['gpu_bw_source']}",
        f"Bande passante RAM : {hw['ram_bw']:.0f} Go/s — {hw['ram_bw_source']}",
        f"Vitesse : {speed_basis or 'ne tient pas en mémoire'}",
    ]
    return {"ctx": ctx, "weights_gb": weights, "kv_gb": kv["gb"], "total_gb": total, "mode": mode,
            "gpu_share": gpu_share, "vram_gb": total * gpu_share if fits else 0.0,
            "ram_gb": total * (1 - gpu_share) if fits else 0.0, "fit": fit, "tps": tps,
            "scores": scores, "overall": overall, "basis": basis}


# ------------------------------------------------------------------ mesures
def _ollama_unload(model: str):
    try:
        requests.post(f"{OLLAMA_URL}/api/generate", json={"model": model, "prompt": "", "keep_alive": 0},
                      timeout=30)
    except Exception:
        pass


def measure_ollama(model: str, ctx: int, cold: bool = True) -> Dict:
    """Mesure réelle avec Ollama. cold=True : décharge d'abord le modèle pour mesurer le chargement."""
    if cold:
        _ollama_unload(model)
        time.sleep(0.5)
    t0 = time.perf_counter()
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": model, "prompt": BENCH_PROMPT, "stream": False, "keep_alive": "5m",
        "options": {"num_ctx": ctx, "num_predict": BENCH_TOKENS, "temperature": 0, "seed": 1},
    }, timeout=900)
    wall = time.perf_counter() - t0
    if r.status_code != 200:
        raise RuntimeError(f"Ollama a répondu {r.status_code} : {r.text[:200]}")
    d = r.json()
    ns = 1e9
    load = (d.get("load_duration") or 0) / ns
    p_cnt, p_dur = d.get("prompt_eval_count") or 0, (d.get("prompt_eval_duration") or 0) / ns
    e_cnt, e_dur = d.get("eval_count") or 0, (d.get("eval_duration") or 0) / ns
    res = {
        "load_s": load, "prompt_tokens": p_cnt, "prompt_tps": p_cnt / p_dur if p_dur else 0.0,
        "gen_tokens": e_cnt, "gen_tps": e_cnt / e_dur if e_dur else 0.0,
        "ttft_s": load + p_dur, "total_s": (d.get("total_duration") or 0) / ns or wall,
        "vram_share": None, "ctx": ctx, "cold": cold,
    }
    try:
        for m in requests.get(f"{OLLAMA_URL}/api/ps", timeout=5).json().get("models", []):
            if m.get("name") == model or m.get("model") == model:
                if m.get("size"):
                    res["vram_share"] = (m.get("size_vram") or 0) / m["size"]
                    res["mem_gb"] = m["size"] / GIB
    except Exception:
        pass
    return res


def measure_lmstudio(key: str, ctx: int, ref: str = "") -> Dict:
    """Mesure réelle avec LM Studio (API native 0.4+, sinon mesure du flux compatible OpenAI)."""
    from src.backend import lmstudio
    try:
        r = requests.post(f"{lmstudio.BASE_URL}/api/v1/chat", json={
            "model": key, "input": BENCH_PROMPT, "stream": False, "temperature": 0,
            "max_output_tokens": BENCH_TOKENS, "context_length": ctx,
        }, timeout=900)
        if r.status_code == 200:
            st = r.json().get("stats") or {}
            if st:
                return {"load_s": st.get("model_load_time_seconds") or 0.0,
                        "prompt_tokens": st.get("input_tokens") or 0, "prompt_tps": 0.0,
                        "gen_tokens": st.get("total_output_tokens") or 0,
                        "gen_tps": st.get("tokens_per_second") or 0.0,
                        "ttft_s": st.get("time_to_first_token_seconds") or 0.0,
                        "total_s": 0.0, "vram_share": None, "ctx": ctx, "cold": False}
    except requests.exceptions.ConnectionError:
        raise RuntimeError("LM Studio n'est pas lancé (serveur local arrêté).")
    except Exception:
        pass
    # Anciennes versions : on chronomètre le flux compatible OpenAI
    from src.backend.providers import chat_stream
    first: List[float] = []
    t0 = time.perf_counter()
    text, stats = chat_stream(ref or f"lmstudio::{key}", [{"role": "user", "content": BENCH_PROMPT}], "",
                              lambda _t: first.append(time.perf_counter()) if not first else None)
    if text.startswith("Erreur"):
        raise RuntimeError(text)
    return {"load_s": 0.0, "prompt_tokens": 0, "prompt_tps": 0.0, "gen_tokens": stats.get("tokens") or 0,
            "gen_tps": stats.get("tokens_per_s") or 0.0, "ttft_s": (first[0] - t0) if first else 0.0,
            "total_s": stats.get("seconds") or 0.0, "vram_share": None, "ctx": ctx, "cold": False}


def measure(prof: Dict, ctx: int, cold: bool = True) -> Dict:
    if prof["source"] == "ollama":
        res = measure_ollama(prof["name"], ctx, cold)
    elif prof["source"] == "lmstudio":
        res = measure_lmstudio(prof.get("key") or prof["name"], ctx, prof["ref"])
    else:
        raise RuntimeError("Ce modèle n'est pas installé : installez-le d'abord pour le mesurer.")
    res["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return res


# ------------------------------------------------------------------ historique
def load_results() -> Dict[str, Dict]:
    return dict(settings.get("bench_results") or {})


def save_result(ref: str, result: Dict) -> None:
    allr = load_results()
    allr[ref] = result
    settings.set("bench_results", allr)


def collect_profiles(installed_ollama: List[str], lm_models: Optional[List[Dict]],
                     lm_provider_id: str = "lmstudio", catalog: Optional[List[Dict]] = None,
                     progress: Optional[Callable[[str], None]] = None) -> List[Dict]:
    """Profils de tous les modèles à comparer (à appeler hors du fil principal : réseau)"""
    out = []
    for name in installed_ollama:
        if progress:
            progress(name)
        out.append(ollama_profile(name))
    from src.backend import lmstudio
    chat_keys = set(lmstudio.chat_models(lm_models or []))
    for m in lm_models or []:
        if m["key"] in chat_keys:
            out.append(lmstudio_profile(m, lm_provider_id))
    installed = set(installed_ollama)
    for entry in catalog or []:
        if entry["id"] not in installed:
            out.append(catalog_profile(entry))
    return out
