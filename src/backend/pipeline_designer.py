"""Pipeline Designer v101 : presets, favoris et validation locale.

Le module ne lance aucun programme. Il prépare des chaînes de travail sérialisables
et des guides de démarrage à partir du catalogue v100.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

SCHEMA_VERSION = 1
MAX_STEPS = 24

STEP_LIBRARY: Tuple[Dict[str, str], ...] = (
    dict(id="prompt", name="Prompt", family="Entrée", role="Description texte ou consigne"),
    dict(id="reference", name="Image de référence", family="Entrée", role="Image ou planche source"),
    dict(id="source_audio", name="Audio source", family="Entrée", role="Audio, musique ou voix à traiter"),
    dict(id="source_video", name="Vidéo source", family="Entrée", role="Vidéo à analyser ou transformer"),
    dict(id="source_docs", name="Documents", family="Entrée", role="PDF, Markdown, texte ou code source"),
    dict(id="llm", name="LLM local", family="IA", role="Texte, traduction, raisonnement ou code"),
    dict(id="flux_sdxl", name="FLUX / SDXL", family="Image", role="Génération d’images"),
    dict(id="controlnet", name="ControlNet / IP-Adapter", family="Image", role="Contrôle pose, structure ou référence"),
    dict(id="rembg", name="rembg", family="Image", role="Suppression locale de l’arrière-plan"),
    dict(id="upscale", name="Real-ESRGAN / Upscale", family="Image", role="Agrandissement et amélioration"),
    dict(id="restore", name="GFPGAN", family="Image", role="Restauration de visages / photos"),
    dict(id="musicgen", name="MusicGen", family="Audio", role="Génération musicale"),
    dict(id="audiogen", name="AudioGen", family="Audio", role="Génération de bruitages"),
    dict(id="demucs", name="Demucs", family="Audio", role="Séparation en stems"),
    dict(id="whisper", name="Whisper / faster-whisper", family="Voix", role="Transcription locale"),
    dict(id="tts", name="Piper / XTTS / Kokoro", family="Voix", role="Synthèse vocale"),
    dict(id="video_gen", name="Wan / LTX", family="Vidéo", role="Génération vidéo"),
    dict(id="interpolate", name="Interpolation vidéo", family="Vidéo", role="Création d’images intermédiaires"),
    dict(id="triposr", name="TripoSR", family="3D", role="Image vers maillage 3D"),
    dict(id="hunyuan3d", name="Hunyuan3D", family="3D", role="Forme et texture 3D"),
    dict(id="blender", name="Blender", family="3D", role="Nettoyage, retopo, rig et export"),
    dict(id="embed", name="Embeddings BGE", family="RAG", role="Vectorisation locale"),
    dict(id="vector_db", name="Chroma / FAISS", family="RAG", role="Recherche vectorielle"),
    dict(id="ffmpeg", name="FFmpeg", family="Sortie", role="Conversion, normalisation ou mux"),
    dict(id="export_png", name="Export PNG", family="Sortie", role="Image finale"),
    dict(id="export_audio", name="Export WAV / OGG", family="Sortie", role="Audio final"),
    dict(id="export_video", name="Export MP4", family="Sortie", role="Vidéo finale"),
    dict(id="export_3d", name="Export GLB", family="Sortie", role="Objet 3D final"),
)

PROJECT_PROFILES: Tuple[Dict[str, Any], ...] = (
    dict(id="game-2d", name="Jeu 2D", description="Sprites, transparence, upscale et sons courts.", pipeline="Sprite de jeu", favorites=("flux-schnell", "sdxl-base")),
    dict(id="game-3d", name="Jeu 3D", description="Références propres, génération 3D puis Blender.", pipeline="Personnage 3D", favorites=("hunyuan3d", "triposr")),
    dict(id="music", name="Musique", description="Composition locale, stems et normalisation.", pipeline="Musique + stems", favorites=("musicgen-small", "musicgen-melody")),
    dict(id="video", name="Vidéo", description="Génération, interpolation et finalisation FFmpeg.", pipeline="Texte vers vidéo", favorites=("wan21", "ltx-video")),
    dict(id="voice", name="Voix / doublage", description="Transcription, traduction et synthèse vocale.", pipeline="Doublage local", favorites=("whisper-large-v3", "faster-whisper")),
    dict(id="documents", name="Documents / RAG", description="Indexation privée et assistant local.", pipeline="RAG documents", favorites=("bge-m3", "qwen25-14b")),
    dict(id="code", name="Développement", description="Indexation de projet et modèle spécialisé code.", pipeline="Assistant de code projet", favorites=("qwen25-coder-14b", "deepseek-coder-v2-lite")),
)

# Correspondance souple depuis le libellé historique v100 vers les briques v101.
ALIASES = {
    "prompt": "prompt", "référence": "reference", "image propre": "reference", "image multi-vues": "reference",
    "pdf/md/txt": "source_docs", "dossier source": "source_docs", "vidéo/audio": "source_video", "vidéo": "source_video",
    "flux/sdxl": "flux_sdxl", "sdxl/flux": "flux_sdxl", "controlnet/ip-adapter": "controlnet",
    "rembg": "rembg", "real-esrgan": "upscale", "upscale": "upscale", "gfpgan": "restore",
    "musicgen": "musicgen", "audiogen": "audiogen", "demucs": "demucs", "whisper": "whisper",
    "faster-whisper": "whisper", "xtts/kokoro": "tts", "wan/ltx": "video_gen", "interpolation": "interpolate",
    "triposr/hunyuan3d": "hunyuan3d", "hunyuan3d": "hunyuan3d", "blender": "blender",
    "bge-m3": "embed", "chroma/faiss": "vector_db", "index rag": "vector_db", "llm local": "llm",
    "qwen coder": "llm", "traduction llm": "llm", "normalisation ffmpeg": "ffmpeg", "ffmpeg": "ffmpeg",
    "mux ffmpeg": "ffmpeg", "png": "export_png", "png transparent": "export_png", "export": "export_png",
    "wav": "export_audio", "wav/ogg": "export_audio", "srt": "export_audio", "mp4": "export_video", "glb": "export_3d",
    "optimisation": "blender", "retopo": "blender", "rig": "blender", "nettoyage": "ffmpeg", "découpage": "source_docs",
    "diff": "llm", "validation": "llm", "texture": "hunyuan3d",
}


def step_map() -> Dict[str, Dict[str, str]]:
    return {step["id"]: step for step in STEP_LIBRARY}


def normalize_steps(steps: Iterable[str]) -> List[str]:
    """Convertit les anciens libellés ou IDs en IDs v101, sans doublons adjacents."""
    known = step_map()
    result: List[str] = []
    for raw in steps:
        value = str(raw).strip()
        sid = value if value in known else ALIASES.get(value.lower())
        if not sid:
            # Correspondances partielles utiles pour les libellés composés de la v100.
            low = value.lower()
            sid = next((target for label, target in ALIASES.items() if label in low), None)
        if sid and (not result or result[-1] != sid):
            result.append(sid)
        if len(result) >= MAX_STEPS:
            break
    return result


def pipeline_record(name: str, steps: Iterable[str], category: str = "Personnalisé") -> Dict[str, Any]:
    clean_name = str(name).strip()[:80]
    if not clean_name:
        raise ValueError("Donnez un nom au pipeline.")
    normalized = normalize_steps(steps)
    if not normalized:
        raise ValueError("Ajoutez au moins une étape au pipeline.")
    return {"schema": SCHEMA_VERSION, "name": clean_name, "category": str(category).strip()[:40] or "Personnalisé", "steps": normalized}


def validate_saved(value: Any) -> List[Dict[str, Any]]:
    """Nettoie une valeur provenant du JSON de réglages avant affichage."""
    if not isinstance(value, list):
        return []
    result: List[Dict[str, Any]] = []
    seen = set()
    for item in value[:100]:
        if not isinstance(item, dict):
            continue
        try:
            record = pipeline_record(item.get("name", ""), item.get("steps", ()), item.get("category", "Personnalisé"))
        except ValueError:
            continue
        key = record["name"].casefold()
        if key in seen:
            continue
        seen.add(key); result.append(record)
    return result


def favorites(value: Any) -> List[str]:
    if not isinstance(value, list): return []
    result = []
    for item in value:
        item = str(item).strip()
        if item and item not in result: result.append(item)
    return result[:200]


def guide_for_steps(step_ids: Iterable[str]) -> List[str]:
    """Produit un guide lisible et non-exécutant pour préparer la chaîne."""
    known = step_map()
    result = []
    for index, sid in enumerate(normalize_steps(step_ids), 1):
        step = known[sid]
        result.append(f"{index}. {step['name']} — {step['role']}")
    return result
