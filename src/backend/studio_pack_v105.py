"""Extension des packs v103 pour les utilitaires automatisables v105."""
from src.backend import studio_advisor

V105_PACK_TOOL_EXTRAS = {
    "essential": ("ffmpeg", "faster-whisper"),
    "code": ("chromadb", "faiss"),
    "image": ("rembg", "realesrgan", "ffmpeg"),
    "audio": ("faster-whisper", "ffmpeg"),
    "video": ("ffmpeg", "realesrgan"),
    "3d": ("rembg",),
    "rag": ("chromadb", "faiss"),
    "full": ("rembg", "realesrgan", "faster-whisper", "demucs", "chromadb", "faiss", "ffmpeg"),
}

def extend_packs_v105():
    if getattr(studio_advisor, "_v105_packs_extended", False):
        return
    enriched = []
    for pack in studio_advisor.PACKS:
        record = dict(pack)
        record["tools"] = tuple(dict.fromkeys(
            tuple(pack.get("tools", ())) + V105_PACK_TOOL_EXTRAS.get(pack["id"], ())
        ))
        enriched.append(record)
    studio_advisor.PACKS = tuple(enriched)
    studio_advisor._v105_packs_extended = True
