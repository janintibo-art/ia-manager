
from __future__ import annotations

import base64
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List

from src.backend import creative_tools, image_studio, settings, storage

PREFIX = "creative::"

CREATIVE_MODELS = (
    {
        "id": "sdxl",
        "label": "🎨 SDXL 1.0",
        "kind": "image",
        "specialty": "Image locale polyvalente",
        "engine": "comfyui",
        "checkpoint_hints": ("sd_xl_base", "sdxl", "stable-diffusion-xl"),
        "size": 1024, "steps": 25, "cfg": 7.0,
    },
    {
        "id": "sdxl-turbo",
        "label": "⚡ SDXL Turbo",
        "kind": "image",
        "specialty": "Image locale rapide",
        "engine": "comfyui",
        "checkpoint_hints": ("turbo", "sdxl_turbo", "sd_xl_turbo"),
        "size": 512, "steps": 4, "cfg": 1.0,
    },
    {
        "id": "animagine",
        "label": "🎨 Animagine XL",
        "kind": "image",
        "specialty": "Anime et manga local",
        "engine": "comfyui",
        "checkpoint_hints": ("animagine",),
        "size": 1024, "steps": 28, "cfg": 5.0,
    },
    {
        "id": "musicgen-small",
        "label": "🎵 MusicGen Small",
        "kind": "audio",
        "specialty": "Musique locale depuis un texte",
        "engine": "audiocraft",
        "model": "facebook/musicgen-small",
        "class": "MusicGen",
    },
    {
        "id": "audiogen",
        "label": "🔊 AudioGen",
        "kind": "audio",
        "specialty": "Bruitages et ambiances locales",
        "engine": "audiocraft",
        "model": "facebook/audiogen-medium",
        "class": "AudioGen",
    },
    {
        "id": "hunyuan3d",
        "label": "🧊 Hunyuan3D 2",
        "kind": "3d",
        "specialty": "Image vers objet 3D local",
        "engine": "hunyuan3d",
    },
    {
        "id": "triposr",
        "label": "🧊 TripoSR",
        "kind": "3d",
        "specialty": "Image vers maillage 3D local",
        "engine": "triposr",
    },
)

def is_creative_ref(ref: str) -> bool:
    return str(ref or "").startswith(PREFIX)

def model_id(ref: str) -> str:
    return str(ref or "")[len(PREFIX):] if is_creative_ref(ref) else ""

def model_for_ref(ref: str) -> Dict:
    mid = model_id(ref)
    for model in CREATIVE_MODELS:
        if model["id"] == mid:
            return dict(model)
    raise ValueError("Modèle créatif inconnu : " + mid)

def choices():
    return [(f"{m['label']} — {m['specialty']}", PREFIX + m["id"], dict(m)) for m in CREATIVE_MODELS]

def creations_dir() -> Path:
    base = storage.root()
    path = (base / "Creations Chat") if base else (Path.home() / "IA Manager" / "Creations Chat")
    path.mkdir(parents=True, exist_ok=True)
    return path

def _tool_root() -> str:
    return str(settings.get("creative_tools_root") or (Path.home()/"IA Manager"/"Outils"))

def tool_state(key: str) -> Dict:
    root = _tool_root()
    record = creative_tools.read_manifest(root, key)
    state = str(record.get("state") or "non installé")
    return {"installed": state.startswith("installé"), "state": state, "root": root}

def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

def _comfy_url() -> str:
    url = str(settings.get("image_comfy_url") or "").strip()
    if url:
        return url
    profiles = settings.get("media_studio_profiles") or {}
    if isinstance(profiles, dict):
        for key in ("wan21", "ltx-video", "cogvideox-2b"):
            item = profiles.get(key)
            if isinstance(item, dict) and str(item.get("url") or "").strip():
                return str(item["url"]).strip()
    return "http://127.0.0.1:8188"

def _select_checkpoint(url: str, hints) -> str:
    names = image_studio.checkpoints(url, True)
    if not names:
        raise RuntimeError("ComfyUI ne contient aucun checkpoint.")
    lowered = [(name, name.lower()) for name in names]
    for hint in hints:
        h = hint.lower()
        for name, low in lowered:
            if h in low:
                return name
    preview = ", ".join(names[:8])
    raise RuntimeError(
        "Le checkpoint demandé n'est pas présent dans ComfyUI. "
        "Installez-le d'abord dans ComfyUI. Checkpoints détectés : " + preview
    )

def generate_image(model: Dict, prompt: str) -> Dict:
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ValueError("Décrivez l'image à créer.")
    state = tool_state("comfyui")
    if not state["installed"]:
        raise RuntimeError("ComfyUI n'est pas installé dans IA Manager. Installez-le depuis Outils locaux.")
    url = _comfy_url()
    checkpoint = _select_checkpoint(url, model["checkpoint_hints"])
    graph = image_studio.workflow(
        checkpoint, prompt, "blurry, low quality, watermark, text",
        int(model["size"]), int(model["steps"]), float(model["cfg"]),
        int(time.time() * 1000) % 2147483647,
    )
    data = image_studio.generate(url, graph, local_only=True)
    out = creations_dir() / f"{model['id']}_{_timestamp()}.png"
    out.write_bytes(data)
    return {
        "kind": "image",
        "path": str(out),
        "label": model["label"],
        "text": f"Image créée avec {model['label']} via ComfyUI.",
        "engine": "comfyui",
    }

def _duration(prompt: str) -> int:
    match = re.search(r"(?:dur[ée]e?\s*[:=]?\s*)?(\d{1,2})\s*(?:s|sec|secondes?)\b", prompt.lower())
    return max(1, min(int(match.group(1)), 20)) if match else 8

def generate_audio(model: Dict, prompt: str) -> Dict:
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ValueError("Décrivez la musique ou le son à créer.")
    root = _tool_root()
    state = tool_state("audiocraft")
    if not state["installed"]:
        raise RuntimeError("AudioCraft n'est pas installé dans IA Manager. Installez-le depuis Outils locaux.")
    paths = creative_tools.paths(root, "audiocraft")
    python = paths["python"]
    if not python.is_file():
        raise RuntimeError("Python AudioCraft introuvable. Reprenez l'installation d'AudioCraft.")
    record = creative_tools.read_manifest(root, "audiocraft")
    device = "cuda" if record.get("hardware") == "nvidia" else "cpu"
    duration = _duration(prompt)
    base = creations_dir() / f"{model['id']}_{_timestamp()}"
    code = "\n".join([
        "from audiocraft.models import MusicGen, AudioGen",
        "from audiocraft.data.audio import audio_write",
        f"cls={'AudioGen' if model['class']=='AudioGen' else 'MusicGen'}",
        f"m=cls.get_pretrained({model['model']!r},device={device!r})",
        f"m.set_generation_params(duration={float(duration)!r})",
        f"wave=m.generate([{prompt!r}])",
        f"audio_write({str(base)!r},wave[0].cpu(),m.sample_rate,strategy='loudness',loudness_compressor=True)",
        f"print({(str(base)+'.wav')!r})",
    ])
    env = os.environ.copy()
    env.update(creative_tools.environment(root, "audiocraft", offline=False))
    flags = 0x08000000 if os.name == "nt" else 0
    proc = subprocess.run(
        [str(python), "-c", code],
        cwd=str(paths["source"]),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
        creationflags=flags,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "Échec AudioCraft")[-1600:])
    wav = Path(str(base) + ".wav")
    if not wav.is_file():
        raise RuntimeError("AudioCraft a terminé sans créer le fichier WAV attendu.")
    return {
        "kind": "audio",
        "path": str(wav),
        "label": model["label"],
        "text": f"Audio créé avec {model['label']} · {duration} s.",
        "engine": "audiocraft",
    }

def _save_reference_image(attachments: List[Dict]) -> str:
    for item in attachments or []:
        if item.get("kind") == "image" and item.get("data"):
            mime = str(item.get("mime") or "image/png").lower()
            ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
            out = creations_dir() / f"reference_3d_{_timestamp()}{ext}"
            out.write_bytes(base64.b64decode(item["data"]))
            return str(out)
    return ""

def prepare_3d(model: Dict, prompt: str, attachments: List[Dict]) -> Dict:
    state = tool_state(model["engine"])
    reference = _save_reference_image(attachments)
    if not state["installed"]:
        text = (
            f"{model['label']} n'est pas encore installé. "
            "Cliquez sur « Installer / démarrer le moteur » ci-dessous."
        )
    elif reference:
        text = (
            f"Référence enregistrée : {reference}\n"
            f"Démarrez {model['label']}, puis importez cette image dans son interface locale."
        )
    else:
        text = (
            f"{model['label']} est prêt. Joignez une image au message pour préparer une référence 3D, "
            "puis ouvrez son interface locale."
        )
    return {
        "kind": "handoff",
        "engine": model["engine"],
        "label": model["label"],
        "text": text,
        "path": reference,
    }

def generate(ref: str, prompt: str, attachments=None) -> Dict:
    model = model_for_ref(ref)
    if model["kind"] == "image":
        return generate_image(model, prompt)
    if model["kind"] == "audio":
        return generate_audio(model, prompt)
    if model["kind"] == "3d":
        return prepare_3d(model, prompt, list(attachments or []))
    raise ValueError("Type créatif inconnu.")
