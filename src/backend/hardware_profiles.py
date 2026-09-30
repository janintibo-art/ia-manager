"""Profils matériels enregistrés pour les recommandations IA Manager."""
from copy import deepcopy
from datetime import datetime

from src.backend import settings
from src.backend.system_analyzer import SystemAnalyzer


def _profiles():
    value = settings.get("hardware_profiles")
    return [dict(x) for x in value] if isinstance(value, list) else []


def list_profiles():
    return _profiles()


def save_profiles(items):
    settings.set("hardware_profiles", [dict(x) for x in items])


def active_id():
    return str(settings.get("hardware_profile_active") or "")


def active_profile():
    aid = active_id()
    return next((dict(p) for p in _profiles() if str(p.get("id")) == aid), None)


def detect_profile(name="PC actuel"):
    info = SystemAnalyzer.get_system_info(refresh=True)
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": now.replace(":", "").replace("-", ""),
        "name": name,
        "cpu": info.get("cpu", ""),
        "cpu_count": int(info.get("cpu_count") or 1),
        "gpu_type": info.get("gpu_type", ""),
        "gpu_vendor": info.get("gpu_vendor", ""),
        "vram_gb": float(info.get("vram_gb") or 0),
        "vram_exact": bool(info.get("vram_exact", True)),
        "ram_gb": float(info.get("ram_gb") or 0),
        "ram_available_gb": float(info.get("ram_available_gb") or 0),
        "detected": True,
        "created": now,
    }


def ensure_detected():
    profiles = _profiles()
    if profiles:
        return profiles
    profile = detect_profile()
    save_profiles([profile])
    settings.set("hardware_profile_active", profile["id"])
    return [profile]


def set_active(profile_id):
    if not any(str(p.get("id")) == str(profile_id) for p in _profiles()):
        raise ValueError("Profil matériel introuvable.")
    settings.set("hardware_profile_active", str(profile_id))


def to_system_info(profile):
    if not profile:
        return None
    return {
        "cpu": str(profile.get("cpu") or "CPU profil"),
        "cpu_count": int(profile.get("cpu_count") or 1),
        "ram_gb": float(profile.get("ram_gb") or 0),
        "ram_available_gb": float(profile.get("ram_available_gb") or profile.get("ram_gb") or 0),
        "gpu_type": str(profile.get("gpu_type") or "GPU profil"),
        "gpu_vendor": str(profile.get("gpu_vendor") or "Autre"),
        "vram_gb": float(profile.get("vram_gb") or 0),
        "vram_exact": bool(profile.get("vram_exact", True)),
        "_profile": True,
        "_profile_name": str(profile.get("name") or "Profil"),
    }


def recommendations(profile):
    """Résumé prudent, volontairement simple et explicite."""
    if not profile:
        return {}
    vram = float(profile.get("vram_gb") or 0)
    ram = float(profile.get("ram_gb") or 0)

    if vram >= 20:
        text = "LLM 20–32B souvent envisageables en quantification adaptée"
        image = "1024 px et workflows image lourds généralement envisageables"
        video = "vidéo locale possible ; commencer court puis augmenter"
        training = "QLoRA 7B/14B à tester selon modèle et contexte"
    elif vram >= 12:
        text = "LLM 12–14B confortables selon quantification"
        image = "1024 px souvent raisonnable pour les workflows image"
        video = "vidéo locale possible en réglages prudents"
        training = "QLoRA 7B raisonnable ; 14B à tester prudemment"
    elif vram >= 8:
        text = "LLM 7–9B à privilégier"
        image = "768 px conseillé pour commencer"
        video = "commencer en basse résolution et courte durée"
        training = "QLoRA 3B conseillé ; 7B selon marge VRAM"
    elif vram >= 5:
        text = "LLM 3–4B à privilégier"
        image = "512–768 px conseillé"
        video = "vidéo locale très prudente"
        training = "QLoRA 1.5B–3B conseillé"
    else:
        text = "petits LLM 1–3B ; davantage de calcul en RAM/CPU"
        image = "512 px conseillé"
        video = "vidéo locale déconseillée sauf workflow très léger"
        training = "entraînement GPU limité ; petits modèles uniquement"

    if ram < 16:
        text += " · RAM limitée"
    return {
        "text": text,
        "image": image,
        "video": video,
        "training": training,
    }
