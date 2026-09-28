"""Catalogue v100 : modèles, outils et pipelines pour un studio IA local.

Ce module ne télécharge ni n'exécute rien tout seul. Il décrit des choix et
fournit une estimation prudente de compatibilité à partir de la RAM/VRAM.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

CATEGORIES = (
    "Texte & code", "Image", "Audio & musique", "Vidéo", "3D", "Vision", "Documents & RAG", "Voix"
)

MODELS: Tuple[Dict[str, Any], ...] = (
    # Texte / code
    dict(id="qwen25-coder-7b", name="Qwen2.5-Coder 7B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Code, scripts, correction et explications", input="Texte", output="Texte/code", min_vram=6, min_ram=16, size_gb=5.0,
         url="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct", tags="code local rapide gguf"),
    dict(id="qwen25-coder-14b", name="Qwen2.5-Coder 14B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Développement plus exigeant et grands fichiers", input="Texte", output="Texte/code", min_vram=10, min_ram=24, size_gb=9.0,
         url="https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct", tags="code local raisonnement"),
    dict(id="qwen25-coder-32b", name="Qwen2.5-Coder 32B", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Gros projets et raisonnement de code", input="Texte", output="Texte/code", min_vram=16, min_ram=32, size_gb=20.0,
         url="https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct", tags="code local puissant"),
    dict(id="deepseek-coder-v2-lite", name="DeepSeek-Coder-V2 Lite", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Programmation multilingue et complétion", input="Texte", output="Texte/code", min_vram=8, min_ram=16, size_gb=10.0,
         url="https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct", tags="code local"),
    dict(id="qwen25-14b", name="Qwen2.5 14B Instruct", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Assistant général, rédaction et raisonnement", input="Texte", output="Texte", min_vram=10, min_ram=24, size_gb=9.0,
         url="https://huggingface.co/Qwen/Qwen2.5-14B-Instruct", tags="assistant local français"),
    dict(id="mistral-small", name="Mistral Small", category="Texte & code", engine="Ollama / llama.cpp",
         specialty="Assistant général et rédaction", input="Texte", output="Texte", min_vram=12, min_ram=24, size_gb=15.0,
         url="https://huggingface.co/mistralai", tags="assistant local français"),

    # Image
    dict(id="flux-schnell", name="FLUX.1-schnell", category="Image", engine="ComfyUI / Diffusers",
         specialty="Texte vers image rapide", input="Texte", output="Image", min_vram=8, min_ram=16, size_gb=12.0,
         url="https://huggingface.co/black-forest-labs/FLUX.1-schnell", tags="image flux rapide local"),
    dict(id="flux-dev", name="FLUX.1-dev", category="Image", engine="ComfyUI / Diffusers",
         specialty="Image détaillée et suivi de prompt", input="Texte", output="Image", min_vram=12, min_ram=24, size_gb=24.0,
         url="https://huggingface.co/black-forest-labs/FLUX.1-dev", tags="image flux qualité local"),
    dict(id="sdxl-base", name="Stable Diffusion XL 1.0", category="Image", engine="ComfyUI / Diffusers",
         specialty="Création d'images polyvalente", input="Texte", output="Image", min_vram=8, min_ram=16, size_gb=7.0,
         url="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0", tags="image sdxl local"),
    dict(id="sd35-medium", name="Stable Diffusion 3.5 Medium", category="Image", engine="ComfyUI / Diffusers",
         specialty="Texte vers image moderne", input="Texte", output="Image", min_vram=10, min_ram=24, size_gb=12.0,
         url="https://huggingface.co/stabilityai/stable-diffusion-3.5-medium", tags="image sd35 local"),
    dict(id="controlnet", name="ControlNet", category="Image", engine="ComfyUI",
         specialty="Contrôle pose, profondeur, contours", input="Image + texte", output="Image", min_vram=8, min_ram=16, size_gb=3.0,
         url="https://huggingface.co/lllyasviel", tags="image pose depth canny"),
    dict(id="ip-adapter", name="IP-Adapter", category="Image", engine="ComfyUI",
         specialty="Guider une image par une référence visuelle", input="Image + texte", output="Image", min_vram=8, min_ram=16, size_gb=2.0,
         url="https://huggingface.co/h94/IP-Adapter", tags="image reference style"),

    # Audio / musique / voix
    dict(id="musicgen-small", name="MusicGen Small", category="Audio & musique", engine="AudioCraft",
         specialty="Musique depuis une description", input="Texte", output="WAV", min_vram=6, min_ram=16, size_gb=2.0,
         url="https://huggingface.co/facebook/musicgen-small", tags="music local audio"),
    dict(id="musicgen-melody", name="MusicGen Melody", category="Audio & musique", engine="AudioCraft",
         specialty="Musique guidée par une mélodie", input="Texte + audio", output="WAV", min_vram=12, min_ram=24, size_gb=7.0,
         url="https://huggingface.co/facebook/musicgen-melody", tags="music melody local"),
    dict(id="audiogen", name="AudioGen Medium", category="Audio & musique", engine="AudioCraft",
         specialty="Bruitages et ambiances sonores", input="Texte", output="WAV", min_vram=10, min_ram=24, size_gb=6.0,
         url="https://huggingface.co/facebook/audiogen-medium", tags="sfx sound local"),
    dict(id="stable-audio-open", name="Stable Audio Open", category="Audio & musique", engine="Diffusers / interface dédiée",
         specialty="Sons, boucles et textures audio", input="Texte", output="Audio", min_vram=10, min_ram=24, size_gb=6.0,
         url="https://huggingface.co/stabilityai/stable-audio-open-1.0", tags="audio loop local"),
    dict(id="whisper-large-v3", name="Whisper large-v3", category="Voix", engine="Whisper / faster-whisper",
         specialty="Transcription multilingue", input="Audio", output="Texte/SRT", min_vram=6, min_ram=16, size_gb=3.2,
         url="https://huggingface.co/openai/whisper-large-v3", tags="speech transcription local"),
    dict(id="kokoro", name="Kokoro 82M", category="Voix", engine="Kokoro / ONNX",
         specialty="Synthèse vocale légère", input="Texte", output="Audio", min_vram=0, min_ram=8, size_gb=1.0,
         url="https://huggingface.co/hexgrad/Kokoro-82M", tags="tts voice cpu local"),
    dict(id="xtts-v2", name="XTTS-v2", category="Voix", engine="Coqui TTS",
         specialty="Synthèse vocale multilingue avec référence", input="Texte + voix", output="Audio", min_vram=6, min_ram=16, size_gb=3.0,
         url="https://huggingface.co/coqui/XTTS-v2", tags="tts voice cloning local"),

    # Vidéo
    dict(id="wan21-t2v", name="Wan 2.1 T2V 1.3B", category="Vidéo", engine="ComfyUI / Wan",
         specialty="Texte vers courte vidéo", input="Texte", output="Vidéo", min_vram=8, min_ram=24, size_gb=15.0,
         url="https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B", tags="video text local"),
    dict(id="ltx-video", name="LTX-Video", category="Vidéo", engine="ComfyUI / LTX-Video",
         specialty="Texte ou image vers vidéo", input="Texte ou image", output="Vidéo", min_vram=10, min_ram=24, size_gb=18.0,
         url="https://huggingface.co/Lightricks/LTX-Video", tags="video image local"),
    dict(id="cogvideox-2b", name="CogVideoX-2B", category="Vidéo", engine="Diffusers / ComfyUI",
         specialty="Texte vers vidéo", input="Texte", output="Vidéo", min_vram=10, min_ram=24, size_gb=12.0,
         url="https://huggingface.co/THUDM/CogVideoX-2b", tags="video local"),

    # 3D
    dict(id="triposr", name="TripoSR", category="3D", engine="TripoSR",
         specialty="Image vers maillage 3D", input="Image", output="Mesh", min_vram=6, min_ram=16, size_gb=3.0,
         url="https://github.com/VAST-AI-Research/TripoSR", tags="3d mesh local"),
    dict(id="hunyuan3d2", name="Hunyuan3D 2", category="3D", engine="Hunyuan3D",
         specialty="Forme 3D puis texture", input="Image", output="Mesh texturé", min_vram=10, min_ram=24, size_gb=20.0,
         url="https://github.com/Tencent-Hunyuan/Hunyuan3D-2", tags="3d texture local"),
    dict(id="instantmesh", name="InstantMesh", category="3D", engine="InstantMesh",
         specialty="Reconstruction 3D depuis image", input="Image", output="Mesh", min_vram=8, min_ram=16, size_gb=8.0,
         url="https://github.com/TencentARC/InstantMesh", tags="3d mesh local"),
    dict(id="trellis", name="TRELLIS", category="3D", engine="TRELLIS",
         specialty="Génération d'actifs 3D depuis image", input="Image", output="3D", min_vram=12, min_ram=24, size_gb=20.0,
         url="https://github.com/microsoft/TRELLIS", tags="3d asset local"),

    # Vision / RAG
    dict(id="qwen2-vl-7b", name="Qwen2-VL 7B", category="Vision", engine="Ollama / Transformers",
         specialty="Comprendre captures, photos et documents visuels", input="Image + texte", output="Texte", min_vram=8, min_ram=16, size_gb=6.0,
         url="https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct", tags="vision screenshot local"),
    dict(id="llava", name="LLaVA 1.6", category="Vision", engine="Ollama / llama.cpp",
         specialty="Questions sur images", input="Image + texte", output="Texte", min_vram=8, min_ram=16, size_gb=6.0,
         url="https://huggingface.co/liuhaotian", tags="vision image local"),
    dict(id="bge-m3", name="BGE-M3", category="Documents & RAG", engine="Sentence Transformers / Ollama",
         specialty="Embeddings multilingues pour recherche locale", input="Texte", output="Vecteurs", min_vram=0, min_ram=8, size_gb=2.5,
         url="https://huggingface.co/BAAI/bge-m3", tags="rag embeddings documents local"),
    dict(id="nomic-embed", name="Nomic Embed Text", category="Documents & RAG", engine="Ollama / sentence-transformers",
         specialty="Embeddings légers pour RAG", input="Texte", output="Vecteurs", min_vram=0, min_ram=8, size_gb=1.0,
         url="https://huggingface.co/nomic-ai", tags="rag embeddings local"),
)

TOOLS: Tuple[Dict[str, str], ...] = (
    dict(id="comfyui", name="ComfyUI", category="Image/Vidéo", description="Workflows visuels pour image et vidéo.", url="https://github.com/comfyanonymous/ComfyUI"),
    dict(id="diffusers", name="Diffusers", category="Image/Vidéo/Audio", description="Bibliothèque de pipelines génératifs en Python.", url="https://github.com/huggingface/diffusers"),
    dict(id="rembg", name="rembg", category="Image", description="Suppression de fond locale.", url="https://github.com/danielgatis/rembg"),
    dict(id="realesrgan", name="Real-ESRGAN", category="Image/Vidéo", description="Upscale et restauration.", url="https://github.com/xinntao/Real-ESRGAN"),
    dict(id="gfpgan", name="GFPGAN", category="Image", description="Restauration de visages.", url="https://github.com/TencentARC/GFPGAN"),
    dict(id="segment-anything", name="Segment Anything", category="Image/Vision", description="Segmentation d'objets.", url="https://github.com/facebookresearch/segment-anything"),
    dict(id="audiocraft", name="AudioCraft", category="Audio", description="MusicGen et AudioGen.", url="https://github.com/facebookresearch/audiocraft"),
    dict(id="demucs", name="Demucs", category="Audio", description="Séparation voix, batterie, basse et autres stems.", url="https://github.com/facebookresearch/demucs"),
    dict(id="whisper", name="Whisper", category="Voix", description="Transcription locale.", url="https://github.com/openai/whisper"),
    dict(id="faster-whisper", name="faster-whisper", category="Voix", description="Whisper optimisé avec CTranslate2.", url="https://github.com/SYSTRAN/faster-whisper"),
    dict(id="piper", name="Piper", category="Voix", description="Synthèse vocale locale légère.", url="https://github.com/rhasspy/piper"),
    dict(id="coqui-tts", name="Coqui TTS", category="Voix", description="Synthèse vocale et XTTS.", url="https://github.com/coqui-ai/TTS"),
    dict(id="ffmpeg", name="FFmpeg", category="Audio/Vidéo", description="Conversion, montage et transcodage.", url="https://ffmpeg.org/"),
    dict(id="opencv", name="OpenCV", category="Vision/Vidéo", description="Traitement d'image et vidéo.", url="https://opencv.org/"),
    dict(id="blender", name="Blender", category="3D", description="Nettoyage, retopo, rig, rendu et export 3D.", url="https://www.blender.org/"),
    dict(id="triposr", name="TripoSR", category="3D", description="Reconstruction 3D depuis image.", url="https://github.com/VAST-AI-Research/TripoSR"),
    dict(id="hunyuan3d", name="Hunyuan3D 2", category="3D", description="Génération de forme et texture 3D.", url="https://github.com/Tencent-Hunyuan/Hunyuan3D-2"),
    dict(id="chromadb", name="Chroma", category="RAG", description="Base vectorielle locale.", url="https://github.com/chroma-core/chroma"),
    dict(id="faiss", name="FAISS", category="RAG", description="Recherche vectorielle locale rapide.", url="https://github.com/facebookresearch/faiss"),
    dict(id="llama-index", name="LlamaIndex", category="RAG/Agents", description="Indexation et pipelines RAG.", url="https://github.com/run-llama/llama_index"),
)

PIPELINES: Tuple[Dict[str, Any], ...] = (
    dict(name="Image propre", category="Image", min_vram=8, steps=("Prompt", "FLUX/SDXL", "rembg", "Real-ESRGAN", "PNG")),
    dict(name="Sprite de jeu", category="Image", min_vram=8, steps=("Référence", "ControlNet/IP-Adapter", "SDXL/FLUX", "rembg", "PNG transparent")),
    dict(name="Restauration photo", category="Image", min_vram=4, steps=("Image", "GFPGAN", "Real-ESRGAN", "Export")),
    dict(name="Musique + stems", category="Audio", min_vram=8, steps=("Prompt", "MusicGen", "Demucs", "Normalisation FFmpeg", "WAV")),
    dict(name="Bruitage prêt pour jeu", category="Audio", min_vram=8, steps=("Prompt", "AudioGen", "Nettoyage", "Normalisation", "WAV/OGG")),
    dict(name="Doublage local", category="Voix", min_vram=6, steps=("Vidéo/audio", "Whisper", "Traduction LLM", "XTTS/Kokoro", "Mux FFmpeg")),
    dict(name="Sous-titres automatiques", category="Voix", min_vram=4, steps=("Vidéo", "faster-whisper", "SRT", "FFmpeg")),
    dict(name="Image vers 3D", category="3D", min_vram=8, steps=("Image propre", "TripoSR/Hunyuan3D", "Blender", "Optimisation", "GLB")),
    dict(name="Personnage 3D", category="3D", min_vram=10, steps=("Image multi-vues", "Hunyuan3D", "Blender", "Retopo", "Rig")),
    dict(name="Texte vers vidéo", category="Vidéo", min_vram=10, steps=("Prompt", "Wan/LTX", "Upscale", "Interpolation", "FFmpeg")),
    dict(name="RAG documents", category="RAG", min_vram=0, steps=("PDF/MD/TXT", "Découpage", "BGE-M3", "Chroma/FAISS", "LLM local")),
    dict(name="Assistant de code projet", category="Code", min_vram=8, steps=("Dossier source", "Index RAG", "Qwen Coder", "Diff", "Validation")),
)


def _numbers(info: Any, key_fragment: str) -> List[float]:
    found: List[float] = []
    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for k, v in value.items(): walk(v, path + " " + str(k).lower())
        elif isinstance(value, (list, tuple)):
            for v in value: walk(v, path)
        elif key_fragment in path:
            text = str(value).lower().replace(',', '.')
            import re
            m = re.search(r"(\d+(?:\.\d+)?)\s*(gb|go|gib)?", text)
            if m:
                n = float(m.group(1))
                if not m.group(2) and n > 1024: n /= 1024.0
                found.append(n)
    walk(info)
    return found


def hardware_capacity(system_info: Any) -> Dict[str, float]:
    """Extrait de façon tolérante RAM/VRAM en Go depuis l'analyse existante."""
    vrams = _numbers(system_info, "vram") + _numbers(system_info, "video memory")
    rams = _numbers(system_info, "ram") + _numbers(system_info, "memory")
    return {"vram": max(vrams or [0.0]), "ram": max(rams or [0.0])}


def compatibility(model: Dict[str, Any], vram: float, ram: float) -> Tuple[str, str]:
    need_vram, need_ram = float(model.get("min_vram", 0)), float(model.get("min_ram", 0))
    if ram and ram < need_ram:
        return "limite", f"RAM conseillée {need_ram:g} Go"
    if need_vram <= 0:
        return "bon", "CPU possible"
    if not vram:
        return "inconnu", f"VRAM conseillée {need_vram:g} Go"
    if vram >= need_vram:
        return "bon", f"VRAM {vram:g} Go ≥ {need_vram:g} Go"
    if vram >= need_vram * 0.7:
        return "limite", f"VRAM {vram:g} Go ; viser {need_vram:g} Go ou utiliser offload/quantification"
    return "difficile", f"VRAM {vram:g} Go ; modèle prévu autour de {need_vram:g} Go"


def filter_models(text: str = "", category: str = "Toutes", compatible_only: bool = False,
                  vram: float = 0, ram: float = 0) -> List[Dict[str, Any]]:
    needle = text.strip().lower()
    result = []
    for model in MODELS:
        if category != "Toutes" and model["category"] != category: continue
        haystack = " ".join(str(model.get(k, "")) for k in ("name", "category", "specialty", "engine", "tags")).lower()
        if needle and needle not in haystack: continue
        status, _ = compatibility(model, vram, ram)
        if compatible_only and status not in ("bon", "inconnu"): continue
        result.append(model)
    return result
