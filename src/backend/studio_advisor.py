"""Conseiller Studio IA v103 : catalogue additionnel et packs matériels.

Aucun téléchargement ni programme n'est lancé ici. Le module enrichit le catalogue
en mémoire et prépare des recommandations à partir de la RAM/VRAM déjà détectée.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.backend import studio_catalog as catalog

EXTRA_MODELS: Tuple[Dict[str, Any], ...] = (
    # Texte / code
    dict(id="qwen3-8b", name="Qwen3 8B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Assistant local généraliste et raisonnement", input="Texte", output="Texte",
         min_vram=6, min_ram=12, size_gb=5.5, url="https://huggingface.co/Qwen", tags="assistant reasoning local"),
    dict(id="qwen3-coder-14b", name="Qwen3 Coder 14B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Programmation, refactor et analyse de dépôt", input="Texte / code", output="Texte / code",
         min_vram=10, min_ram=24, size_gb=9.0, url="https://huggingface.co/Qwen", tags="code coder local"),
    dict(id="deepseek-r1-distill-8b", name="DeepSeek R1 Distill 8B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Raisonnement local compact", input="Texte", output="Texte",
         min_vram=6, min_ram=16, size_gb=5.5, url="https://huggingface.co/deepseek-ai", tags="reasoning local"),
    dict(id="mistral-small", name="Mistral Small", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Assistant multilingue et français", input="Texte", output="Texte",
         min_vram=10, min_ram=24, size_gb=9.0, url="https://huggingface.co/mistralai", tags="french multilingual local"),

    # Image
    dict(id="flux-fill", name="FLUX Fill", category="Image", engine="ComfyUI / Diffusers",
         specialty="Inpainting et remplacement de zones", input="Image + masque + texte", output="Image",
         min_vram=10, min_ram=24, size_gb=18.0, url="https://huggingface.co/black-forest-labs", tags="inpaint image local"),
    dict(id="sdxl-turbo", name="SDXL Turbo", category="Image", engine="ComfyUI / Diffusers",
         specialty="Prévisualisation image très rapide", input="Texte", output="Image",
         min_vram=6, min_ram=16, size_gb=7.0, url="https://huggingface.co/stabilityai", tags="image fast preview local"),
    dict(id="depth-anything-v2", name="Depth Anything V2", category="Vision", engine="Transformers / ComfyUI",
         specialty="Carte de profondeur pour ControlNet et 3D", input="Image", output="Profondeur",
         min_vram=4, min_ram=8, size_gb=1.5, url="https://huggingface.co/depth-anything", tags="depth vision local"),
    dict(id="sam2", name="SAM 2", category="Vision", engine="PyTorch / ComfyUI",
         specialty="Segmentation et détourage d'objets", input="Image / vidéo", output="Masque",
         min_vram=6, min_ram=16, size_gb=3.0, url="https://github.com/facebookresearch/sam2", tags="segment mask local"),

    # Audio / voix
    dict(id="ace-step", name="ACE-Step", category="Audio & musique", engine="Interface dédiée / Diffusers",
         specialty="Génération musicale locale moderne", input="Texte", output="Audio",
         min_vram=8, min_ram=16, size_gb=8.0, url="https://huggingface.co/ACE-Step", tags="music generation local"),
    dict(id="bark", name="Bark", category="Voix", engine="Transformers",
         specialty="Voix expressive et effets vocaux", input="Texte", output="Audio",
         min_vram=6, min_ram=16, size_gb=5.0, url="https://huggingface.co/suno/bark", tags="tts expressive local"),
    dict(id="silero-vad", name="Silero VAD", category="Voix", engine="ONNX / PyTorch",
         specialty="Détection locale de parole", input="Audio", output="Segments",
         min_vram=0, min_ram=4, size_gb=0.1, url="https://github.com/snakers4/silero-vad", tags="voice vad cpu local"),

    # Vidéo
    dict(id="rife", name="RIFE", category="Vidéo", engine="PyTorch / VapourSynth",
         specialty="Interpolation d'images vidéo", input="Vidéo", output="Vidéo",
         min_vram=4, min_ram=8, size_gb=1.0, url="https://github.com/hzwer/ECCV2022-RIFE", tags="video interpolation local"),
    dict(id="video2x", name="Video2X", category="Vidéo", engine="Real-ESRGAN / Vulkan",
         specialty="Upscale vidéo local", input="Vidéo", output="Vidéo",
         min_vram=4, min_ram=8, size_gb=1.0, url="https://github.com/k4yt3x/video2x", tags="video upscale local"),

    # 3D
    dict(id="stable-fast-3d", name="Stable Fast 3D", category="3D", engine="PyTorch",
         specialty="Image vers asset 3D rapide", input="Image", output="GLB",
         min_vram=8, min_ram=16, size_gb=6.0, url="https://huggingface.co/stabilityai/stable-fast-3d", tags="3d mesh local"),
    dict(id="mvdream", name="MVDream", category="3D", engine="Diffusers / ComfyUI",
         specialty="Génération multi-vues pour reconstruction 3D", input="Texte / image", output="Images multi-vues",
         min_vram=10, min_ram=24, size_gb=8.0, url="https://huggingface.co/bytedance/MVDream", tags="3d multiview local"),

    # Documents / RAG
    dict(id="jina-embeddings-v3", name="Jina Embeddings v3", category="Documents & RAG",
         engine="Sentence Transformers", specialty="Embeddings multilingues longs documents",
         input="Texte", output="Vecteurs", min_vram=0, min_ram=8, size_gb=1.5,
         url="https://huggingface.co/jinaai/jina-embeddings-v3", tags="rag embeddings multilingual local"),
    dict(id="reranker-bge", name="BGE Reranker", category="Documents & RAG",
         engine="Sentence Transformers", specialty="Reclassement précis des passages RAG",
         input="Requête + passages", output="Scores", min_vram=0, min_ram=8, size_gb=1.2,
         url="https://huggingface.co/BAAI", tags="rag reranker local"),
)

EXTRA_TOOLS: Tuple[Dict[str, str], ...] = (
    dict(id="llama-cpp", name="llama.cpp", category="Texte", description="Exécution locale GGUF et serveur OpenAI-compatible.", url="https://github.com/ggml-org/llama.cpp"),
    dict(id="open-webui", name="Open WebUI", category="Texte/RAG", description="Interface locale pour Ollama et RAG.", url="https://github.com/open-webui/open-webui"),
    dict(id="anythingllm", name="AnythingLLM", category="RAG", description="Espace documentaire et agents locaux.", url="https://github.com/Mintplex-Labs/anything-llm"),
    dict(id="invokeai", name="InvokeAI", category="Image", description="Studio image local avec workflows et canvas.", url="https://github.com/invoke-ai/InvokeAI"),
    dict(id="kohya-ss", name="Kohya SS", category="Entraînement image", description="Entraînement LoRA et fine-tuning diffusion.", url="https://github.com/bmaltais/kohya_ss"),
    dict(id="rvc", name="RVC", category="Voix", description="Conversion de voix locale.", url="https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI"),
    dict(id="audacity", name="Audacity", category="Audio", description="Édition et nettoyage audio local.", url="https://www.audacityteam.org/"),
    dict(id="rife", name="RIFE", category="Vidéo", description="Interpolation vidéo locale.", url="https://github.com/hzwer/ECCV2022-RIFE"),
    dict(id="video2x", name="Video2X", category="Vidéo", description="Upscale vidéo local.", url="https://github.com/k4yt3x/video2x"),
    dict(id="meshlab", name="MeshLab", category="3D", description="Nettoyage, inspection et simplification de maillages.", url="https://www.meshlab.net/"),
    dict(id="onnxruntime", name="ONNX Runtime", category="Runtime", description="Exécution CPU/GPU légère de nombreux modèles.", url="https://onnxruntime.ai/"),
    dict(id="nvidia-smi", name="NVIDIA System Management", category="Diagnostic", description="Diagnostic GPU/VRAM pour profils NVIDIA.", url="https://developer.nvidia.com/"),
)

EXTRA_PIPELINES: Tuple[Dict[str, Any], ...] = (
    dict(name="Inpainting propre", category="Image", min_vram=8,
         steps=("Image de référence", "FLUX/SDXL", "rembg", "Real-ESRGAN", "PNG")),
    dict(name="Concept vers personnage 3D", category="3D", min_vram=10,
         steps=("Prompt", "FLUX/SDXL", "Image multi-vues", "Hunyuan3D", "Blender", "GLB")),
    dict(name="Podcast local", category="Voix", min_vram=4,
         steps=("Documents", "LLM local", "XTTS/Kokoro", "Normalisation FFmpeg", "WAV")),
    dict(name="Nettoyage voix", category="Voix", min_vram=2,
         steps=("Audio source", "Whisper", "FFmpeg", "WAV")),
    dict(name="Vidéo améliorée", category="Vidéo", min_vram=4,
         steps=("Vidéo", "Upscale", "Interpolation", "FFmpeg", "MP4")),
    dict(name="RAG renforcé", category="RAG", min_vram=0,
         steps=("PDF/MD/TXT", "Découpage", "BGE-M3", "Chroma/FAISS", "LLM local")),
)

PACKS: Tuple[Dict[str, Any], ...] = (
    dict(id="essential", name="Essentiel local", description="Texte, vision légère, embeddings et utilitaires.",
         models=("qwen3-8b", "qwen2-vl-7b", "nomic-embed", "whisper-large-v3"),
         tools=("llama-cpp", "faster-whisper", "ffmpeg"), pipeline="RAG documents"),
    dict(id="code", name="Développement & code", description="Assistant code, raisonnement et contexte projet.",
         models=("qwen3-coder-14b", "deepseek-r1-distill-8b", "bge-m3", "reranker-bge"),
         tools=("llama-cpp", "chromadb", "faiss"), pipeline="Assistant de code projet"),
    dict(id="image", name="Image & assets 2D", description="Création, retouche, détourage et upscale.",
         models=("flux-schnell", "sdxl-base", "sdxl-turbo", "controlnet", "sam2"),
         tools=("comfyui", "rembg", "realesrgan", "segment-anything"), pipeline="Sprite de jeu"),
    dict(id="audio", name="Audio & musique", description="Musique, bruitages, séparation et finalisation.",
         models=("musicgen-small", "audiogen", "ace-step", "whisper-large-v3"),
         tools=("audiocraft", "demucs", "audacity", "ffmpeg"), pipeline="Musique + stems"),
    dict(id="video", name="Vidéo", description="Génération, upscale, interpolation et export.",
         models=("wan21-t2v", "ltx-video", "rife", "video2x"),
         tools=("comfyui", "rife", "video2x", "ffmpeg"), pipeline="Texte vers vidéo"),
    dict(id="3d", name="3D & personnages", description="Référence, multi-vues, reconstruction et nettoyage.",
         models=("stable-fast-3d", "triposr", "hunyuan3d2", "mvdream"),
         tools=("triposr", "hunyuan3d", "blender", "meshlab"), pipeline="Personnage 3D"),
    dict(id="rag", name="Documents & RAG", description="Embeddings, reclassement et recherche privée.",
         models=("bge-m3", "jina-embeddings-v3", "reranker-bge", "qwen3-8b"),
         tools=("chromadb", "faiss", "llama-index", "anythingllm"), pipeline="RAG renforcé"),
    dict(id="full", name="Studio complet", description="Sélection équilibrée couvrant tous les domaines sans tout télécharger.",
         models=("qwen3-8b", "qwen3-coder-14b", "flux-schnell", "musicgen-small",
                 "whisper-large-v3", "wan21-t2v", "stable-fast-3d", "bge-m3"),
         tools=("comfyui", "audiocraft", "faster-whisper", "ffmpeg", "blender", "chromadb"),
         pipeline="Image propre"),
)


def _merge_unique(existing, additions, key="id"):
    seen = {item.get(key) for item in existing}
    return tuple(existing) + tuple(item for item in additions if item.get(key) not in seen)


def extend_catalog() -> None:
    """Enrichit une seule fois les tuples du catalogue v100."""
    if getattr(catalog, "_v103_extended", False):
        return
    catalog.MODELS = _merge_unique(catalog.MODELS, EXTRA_MODELS)
    catalog.TOOLS = _merge_unique(catalog.TOOLS, EXTRA_TOOLS)
    # Les pipelines sont identifiés par leur nom.
    seen = {item.get("name") for item in catalog.PIPELINES}
    catalog.PIPELINES = tuple(catalog.PIPELINES) + tuple(p for p in EXTRA_PIPELINES if p.get("name") not in seen)
    catalog._v103_extended = True


def pack_by_id(pack_id: str) -> Dict[str, Any]:
    return next((p for p in PACKS if p["id"] == pack_id), PACKS[0])


def pack_plan(pack_id: str, vram: float = 0.0, ram: float = 0.0) -> Dict[str, Any]:
    """Retourne les modèles classés par compatibilité et les outils du pack."""
    extend_catalog()
    pack = pack_by_id(pack_id)
    model_map = {m["id"]: m for m in catalog.MODELS}
    tool_map = {t["id"]: t for t in catalog.TOOLS}
    models: List[Dict[str, Any]] = []
    for mid in pack["models"]:
        model = model_map.get(mid)
        if not model:
            continue
        status, reason = catalog.compatibility(model, vram, ram)
        models.append({"id": mid, "name": model["name"], "status": status, "reason": reason,
                       "engine": model["engine"], "size_gb": model["size_gb"]})
    tools = [tool_map[tid] for tid in pack["tools"] if tid in tool_map]
    return {"pack": pack, "models": models, "tools": tools}


def suitable_model_ids(plan: Dict[str, Any]) -> List[str]:
    """Favoris sûrs : bon, limite ou inconnu si le matériel n'a pas encore été analysé."""
    return [m["id"] for m in plan["models"] if m["status"] in ("bon", "limite", "inconnu")]
