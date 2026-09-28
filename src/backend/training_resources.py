"""Profils prudents et estimations explicites : aucune garantie de compatibilité."""
import math
import shutil
from pathlib import Path

# Budgets indicatifs QLoRA, pas des mesures ni des minima universels.
PROFILES = (
    {'label': 'Léger · 1,5B', 'model': 'Qwen/Qwen2.5-1.5B-Instruct', 'size': 1.5,
     'context': 1024, 'rank': 8, 'batch': 1, 'vram': 4.0},
    {'label': 'Prudent · 3B', 'model': 'Qwen/Qwen2.5-3B-Instruct', 'size': 3,
     'context': 1024, 'rank': 8, 'batch': 1, 'vram': 6.0},
    {'label': 'Étendu · 7B', 'model': 'Qwen/Qwen2.5-7B-Instruct', 'size': 7,
     'context': 2048, 'rank': 8, 'batch': 1, 'vram': 10.0},
    {'label': 'Grande mémoire · 14B', 'model': 'Qwen/Qwen2.5-14B-Instruct', 'size': 14,
     'context': 2048, 'rank': 8, 'batch': 1, 'vram': 18.0},
)


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def recommend(info):
    """Un seul GPU. Ne jamais additionner RAM et VRAM pour conseiller QLoRA."""
    if not info or info.get('gpu_vendor') != 'NVIDIA' or not info.get('vram_exact'):
        return None
    vram, ram = number(info.get('vram_gb')), number(info.get('ram_gb'))
    if vram >= 30 and ram >= 60:
        return dict(PROFILES[3])
    if vram >= 15 and ram >= 28:
        return dict(PROFILES[2])
    if vram >= 8 and ram >= 14:
        return dict(PROFILES[1])
    if vram >= 5 and ram >= 10:
        return dict(PROFILES[0])
    return None


def requirements(model, context=1024, rank=8, batch=1, action='train'):
    profile = next((p for p in PROFILES if p['model'] == model.strip()), None)
    if not profile:
        return None  # Pas de déduction hasardeuse d'après le nom d'un modèle arbitraire.
    size = profile['size']
    if action == 'merge':
        return dict(vram_gb=0, ram_gb=4+size*2, disk_gb=8+size*7,
                    estimated=True, basis='Deux sources FP16 + résultat ; chargement progressif sur CPU.')
    # Approximation volontairement visible ; les kernels et le jeu de données comptent aussi.
    extra = max(0, context/profile['context']-1)*1.5 + max(0, rank/8-1)*.3
    vram = profile['vram'] + extra + max(0, batch-1)*1.5
    return dict(vram_gb=round(vram, 1), ram_gb=round(6+size*2, 1),
                disk_gb=round(8+size*6, 1), estimated=True,
                basis='QLoRA + marge indicative ; RAM et disque incluent un export complet.')


def disk_free(path):
    path = Path(path).expanduser().resolve()
    while not path.exists() and path != path.parent:
        path = path.parent
    return shutil.disk_usage(path).free / 2**30


def advisory(info, model, context=1024, rank=8, batch=1):
    req = requirements(model, context, rank, batch)
    if req is None:
        return 'Modèle personnalisé : budget inconnu. Le diagnostic CUDA et l’essai court restent nécessaires.'
    message = (f"Budgets indicatifs : VRAM {req['vram_gb']:.1f} Go · RAM disponible {req['ram_gb']:.1f} Go · "
               f"disque {req['disk_gb']:.0f} Go. Ce ne sont pas des mesures garanties.")
    if info:
        if info.get('vram_exact') and number(info.get('vram_gb')) < req['vram_gb']:
            message += ' La VRAM détectée est sous le budget : choisissez un profil plus léger.'
        if number(info.get('ram_available_gb')) < req['ram_gb']:
            message += ' RAM libre sous le budget indicatif : fermez des applications ou réduisez le modèle.'
    return message
