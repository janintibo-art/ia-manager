"""Fichiers joints au Chat : images, PDF, Word, zip, fichiers texte et code."""

import base64
import html
import re
import zipfile
from pathlib import Path
from typing import Dict, List

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_TEXT_CHARS = 120_000          # au-delà, le texte est coupé (les petits modèles saturent)
MAX_ZIP_FILES = 60
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MAX_ENTRY_BYTES = 200_000
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024
MAX_TEXT_BYTES = 512_000
BINARY_EXT = {".exe", ".dll", ".so", ".bin", ".gguf", ".mp3", ".mp4", ".avi", ".mkv", ".wav",
              ".ico", ".ttf", ".otf", ".woff", ".woff2", ".jar", ".class", ".pyc", ".apk", ".7z", ".rar"}

# Modèles qui acceptent les images (préfixes de noms Ollama ou distants)
VISION_HINTS = ("llava", "bakllava", "moondream", "minicpm-v", "llama3.2-vision", "qwen2.5vl",
                "qwen3-vl", "granite3.2-vision", "gemma3:", "gemma3n", "medgemma", "glm-ocr",
                "deepseek-ocr", "mistral-small3", "llama4", "claude", "gpt-4o", "gpt-4.1", "gpt-5", "o3", "o4")


def model_accepts_images(model_ref: str) -> bool:
    name = model_ref.lower().split("::")[-1]
    if name.startswith("gemma3:1b"):
        return False
    return any(h in name for h in VISION_HINTS)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:4096]


def pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[Lecture PDF indisponible : bibliothèque pypdf absente]"
    reader = PdfReader(str(path))
    pages = []
    used = 0
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
            remaining = MAX_TEXT_CHARS - used
            pages.append(f"--- Page {i} ---\n{text[:remaining]}")
            used += len(text)
            if used >= MAX_TEXT_CHARS:
                pages.append("[… lecture PDF arrêtée à la limite de texte]")
                break
        except Exception:
            pages.append(f"--- Page {i} --- (illisible)")
    return "\n".join(pages)


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        info = z.getinfo("word/document.xml")
        if info.file_size > MAX_DOCX_XML_BYTES:
            raise ValueError("Document Word trop volumineux après décompression (8 Mio maximum).")
        with z.open(info) as stream:
            raw = stream.read(MAX_DOCX_XML_BYTES + 1)
        if len(raw) > MAX_DOCX_XML_BYTES:
            raise ValueError("Document Word trop volumineux après décompression.")
        xml = raw.decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(xml)


def zip_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        entries = [info for info in z.infolist() if not info.is_dir()]
        listing = "Contenu de l'archive :\n" + "\n".join(f"- {entry.filename}" for entry in entries[:300])
        out.append(listing[:MAX_TEXT_CHARS])
        used = len(out[0])
        shown = skipped = 0
        for entry in entries:
            if shown >= MAX_ZIP_FILES or used >= MAX_TEXT_CHARS:
                out.append("\n[… limite de lecture de l'archive atteinte]")
                break
            n = entry.filename
            if Path(n).suffix.lower() in BINARY_EXT | IMAGE_EXT or entry.file_size > MAX_ENTRY_BYTES:
                skipped += 1
                continue
            with z.open(entry) as stream:
                data = stream.read(MAX_ENTRY_BYTES + 1)
            if _looks_binary(data) or len(data) > MAX_ENTRY_BYTES:
                skipped += 1
                continue
            ext = Path(n).suffix.lstrip(".")
            fragment = f"\n### {n}\n```{ext}\n{_decode(data)}\n```"
            remaining = max(0, MAX_TEXT_CHARS - used)
            out.append(fragment[:remaining])
            used += len(fragment)
            shown += 1
        if skipped:
            out.append(f"\n[{skipped} fichier(s) binaire(s) ou trop volumineux ignoré(s)]")
    return "\n".join(out)


def check_size(path):
    size = Path(path).stat().st_size
    if size > MAX_ATTACHMENT_BYTES:
        raise ValueError("Fichier trop volumineux : 25 Mio maximum par pièce jointe.")
    return size


def load_attachment(path: str) -> Dict:
    """Renvoie {name, kind: 'image'|'text', mime?, data(b64)?, text?, size}"""
    p = Path(path)
    ext = p.suffix.lower()
    size = check_size(p)
    # Ne pas recopier en mémoire les PDF/Word/ZIP avant leur lecture spécialisée.
    raw = b""
    if ext not in (".pdf", ".docx", ".zip"):
        with p.open("rb") as stream:
            raw = stream.read(MAX_ATTACHMENT_BYTES + 1 if ext in IMAGE_EXT else MAX_TEXT_BYTES)
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise ValueError("Fichier trop volumineux.")
    info = {"name": p.name, "path": str(p), "size": size}

    if ext in IMAGE_EXT:
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext.lstrip("."), f"image/{ext.lstrip('.')}")
        info.update(kind="image", mime=mime, data=base64.b64encode(raw).decode("ascii"))
        return info

    if ext == ".pdf":
        text = pdf_text(p)
    elif ext == ".docx":
        text = docx_text(p)
    elif ext == ".zip":
        text = zip_text(p)
    elif ext in BINARY_EXT or _looks_binary(raw):
        text = f"[Fichier binaire « {p.name} » ({size} octets) : contenu non lisible par l'IA]"
    else:
        text = _decode(raw)
        if size > len(raw):
            text += "\n[… lecture limitée aux premiers 512 Ko du fichier]"

    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS] + f"\n[… texte coupé : {len(text) - MAX_TEXT_CHARS} caractères en plus]"
    info.update(kind="text", text=text, truncated=truncated)
    return info


def image_attachment(name: str, png_bytes: bytes) -> Dict:
    """Image venant du presse-papiers ou convertie en PNG"""
    return {"name": name, "path": "", "size": len(png_bytes), "kind": "image",
            "mime": "image/png", "data": base64.b64encode(png_bytes).decode("ascii")}


def build_message(text: str, attachments: List[Dict]) -> Dict:
    """Message utilisateur prêt pour l'IA : le texte des fichiers est ajouté au message,
    les images partent à part (base64)."""
    parts = [text.strip()]
    for a in attachments:
        if a["kind"] == "text":
            ext = Path(a["name"]).suffix.lstrip(".")
            fence = "" if ext in ("pdf", "docx", "zip") else ext
            parts.append(f"\n\n--- Fichier joint : {a['name']} ---\n```{fence}\n{a['text']}\n```")
    msg = {"role": "user", "content": "".join(parts).strip()}
    images = [{"mime": a["mime"], "data": a["data"]} for a in attachments if a["kind"] == "image"]
    if images:
        msg["images"] = images
    names = [a["name"] for a in attachments]
    if names:
        msg["attachments"] = names
        msg["display"] = text.strip()
    return msg


def human_size(n: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} o"
