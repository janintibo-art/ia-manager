"""Blocs de code dans les réponses de l'IA : extraction, zip, affichage.

L'IA écrit le code entre ``` ``` (markdown). On retrouve le nom de chaque fichier :
  - ```python src/app.py            (chemin après le langage)
  - `src/app.py` ou **src/app.py**  (sur la ligne juste avant le bloc)
  - # fichier : src/app.py          (en commentaire sur la première ligne du bloc)
Sinon on invente un nom (fichier_1.py…).
"""

import html
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

# Consigne ajoutée quand le « mode projet de code » est activé dans le Chat
CODE_MODE_INSTRUCTIONS = (
    "Quand tu écris du code, mets chaque fichier dans son propre bloc ``` et écris son chemin "
    "complet juste après le langage, par exemple : ```python src/main.py\n"
    "Donne toujours les fichiers complets, jamais d'extraits avec « ... »."
)

EXTENSIONS = {
    "python": "py", "py": "py", "javascript": "js", "js": "js", "typescript": "ts", "ts": "ts",
    "tsx": "tsx", "jsx": "jsx", "html": "html", "css": "css", "scss": "scss", "json": "json",
    "yaml": "yml", "yml": "yml", "toml": "toml", "ini": "ini", "xml": "xml", "sql": "sql",
    "bash": "sh", "sh": "sh", "shell": "sh", "zsh": "sh", "powershell": "ps1", "ps1": "ps1",
    "bat": "bat", "cmd": "bat", "c": "c", "cpp": "cpp", "c++": "cpp", "h": "h", "hpp": "hpp",
    "csharp": "cs", "cs": "cs", "java": "java", "kotlin": "kt", "kt": "kt", "swift": "swift",
    "go": "go", "golang": "go", "rust": "rs", "rs": "rs", "php": "php", "ruby": "rb", "rb": "rb",
    "dart": "dart", "lua": "lua", "r": "r", "markdown": "md", "md": "md", "text": "txt",
    "txt": "txt", "dockerfile": "Dockerfile", "makefile": "Makefile", "gradle": "gradle",
    "vue": "vue", "svelte": "svelte",
}

FENCE_RE = re.compile(r"^(```+|~~~+)[ \t]*([^\n`]*)\n(.*?)^\1[ \t]*$", re.MULTILINE | re.DOTALL)
PATH_RE = re.compile(r"^[\w.\-/\\]+\.[A-Za-z0-9]{1,10}$|^(Dockerfile|Makefile)$")
COMMENT_PATH_RE = re.compile(
    r"^\s*(?:#|//|--|;|<!--|/\*)\s*(?:fichier|file|filename|chemin|path)\s*:\s*([\w.\-/\\]+)",
    re.IGNORECASE)
PREV_LINE_PATH_RE = re.compile(r"[`*\"']([\w.\-/\\]+\.[A-Za-z0-9]{1,10})[`*\"']|^\s*#+\s*([\w.\-/\\]+\.[A-Za-z0-9]{1,10})\s*$")


def _clean_path(p: str) -> Optional[str]:
    p = p.strip().strip("`*\"':").replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")
    parts = [x for x in p.split("/") if x not in ("", ".", "..")]
    if not parts:
        return None
    p = "/".join(parts)
    return p if PATH_RE.match(p) else None


def extract_code_blocks(text: str) -> List[Dict]:
    """Liste des blocs : {lang, code, filename (ou None), start, end}"""
    blocks = []
    for m in FENCE_RE.finditer(text):
        info = m.group(2).strip()
        code = m.group(3)
        if code.endswith("\n"):
            code = code[:-1]
        lang, filename = "", None
        if info:
            parts = info.split()
            first = parts[0]
            if len(parts) > 1:
                lang = first.lower()
                filename = _clean_path(parts[1])
            elif _clean_path(first) and ("." in first or "/" in first):
                filename = _clean_path(first)
                lang = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            else:
                lang = first.lower()
        if not filename:
            first_line = code.split("\n", 1)[0]
            cm = COMMENT_PATH_RE.match(first_line)
            if cm:
                filename = _clean_path(cm.group(1))
        if not filename:
            before = text[:m.start()].rstrip("\n").rsplit("\n", 1)[-1]
            pm = PREV_LINE_PATH_RE.search(before)
            if pm:
                filename = _clean_path(pm.group(1) or pm.group(2))
        blocks.append({"lang": lang, "code": code, "filename": filename,
                       "start": m.start(), "end": m.end()})
    return blocks


def default_name(block: Dict, index: int) -> str:
    ext = EXTENSIONS.get(block["lang"], "txt")
    if ext in ("Dockerfile", "Makefile"):
        return ext
    return f"fichier_{index}.{ext}"


def assign_filenames(blocks: List[Dict]) -> List[Dict]:
    """Donne un nom unique à chaque bloc (le dernier bloc d'un même fichier gagne)"""
    result: Dict[str, Dict] = {}
    for i, b in enumerate(blocks, 1):
        name = b["filename"] or default_name(b, i)
        result[name] = dict(b, filename=name)
    return list(result.values())


def build_zip(blocks: List[Dict], dest: str, root_folder: str = "") -> Path:
    """Crée un zip avec tous les blocs. root_folder = dossier racine dans le zip (optionnel)."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    root = root_folder.strip().strip("/")
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as z:
        for b in assign_filenames(blocks):
            arc = f"{root}/{b['filename']}" if root else b["filename"]
            z.writestr(arc, b["code"] + "\n")
    return dest_path


def write_to_folder(blocks: List[Dict], folder: str) -> List[Path]:
    """Écrit chaque bloc directement dans le dossier du dépôt (pour « Appliquer au dépôt »).
    Les chemins sont déjà nettoyés par _clean_path (pas de .. ni de racine absolue)."""
    base = Path(folder)
    written = []
    for b in assign_filenames(blocks):
        target = base / b["filename"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(b["code"] + "\n", encoding="utf-8")
        written.append(target)
    return written


# ------------------------------------------------------------ affichage HTML
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")
LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
URL_RE = re.compile(r"(?<![\"'>=])(https?://[^\s<]+)")


def _inline(text: str, colors: Dict[str, str]) -> str:
    t = html.escape(text)
    t = INLINE_CODE_RE.sub(
        lambda m: f"<code style='background-color:{colors['code_bg']}; color:{colors['code_fg']}'>"
                  f"&nbsp;{m.group(1)}&nbsp;</code>", t)
    t = BOLD_RE.sub(r"<b>\1</b>", t)
    t = ITALIC_RE.sub(r"<i>\1</i>", t)
    t = LINK_RE.sub(lambda m: f"<a href='{m.group(2)}'>{m.group(1)}</a>", t)
    return t


def _text_to_html(text: str, colors: Dict[str, str]) -> str:
    out, in_list = [], False
    for line in text.split("\n"):
        s = line.strip()
        bullet = re.match(r"^([-*•]|\d+[.)])\s+(.*)$", s)
        if bullet:
            if not in_list:
                out.append("<ul style='margin-top:2px; margin-bottom:2px'>")
                in_list = True
            out.append(f"<li>{_inline(bullet.group(2), colors)}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        heading = re.match(r"^(#{1,4})\s+(.*)$", s)
        if heading:
            size = {1: "+3", 2: "+2", 3: "+1", 4: "+0"}[len(heading.group(1))]
            out.append(f"<p style='margin-top:8px'><b><font size='{size}'>"
                       f"{_inline(heading.group(2), colors)}</font></b></p>")
        elif s:
            out.append(_inline(line, colors) + "<br>")
        else:
            out.append("<br>")
    if in_list:
        out.append("</ul>")
    html_text = "".join(out)
    while html_text.endswith("<br>"):
        html_text = html_text[:-4]
    return html_text


def markdown_to_html(text: str, msg_index: int, colors: Dict[str, str]) -> str:
    """Convertit la réponse en HTML. Chaque bloc de code reçoit des liens :
    copy:<msg>:<bloc>  et  save:<msg>:<bloc> ; et zip:<msg> s'il y a du code."""
    parts, pos = [], 0
    blocks = extract_code_blocks(text)
    for i, b in enumerate(blocks):
        parts.append(_text_to_html(text[pos:b["start"]], colors))
        title = html.escape(b["filename"] or b["lang"] or "code")
        code_html = html.escape(b["code"]).replace(" ", "&nbsp;").replace("\n", "<br>")
        parts.append(
            f"<table width='100%' cellpadding='10' cellspacing='0' "
            f"style='background-color:{colors['block_bg']}; margin-top:8px; margin-bottom:8px'>"
            f"<tr><td style='color:{colors['muted']}'>{title} &nbsp;&nbsp;"
            f"<a href='copy:{msg_index}:{i}'>📋 Copier</a> &nbsp;&nbsp;"
            f"<a href='save:{msg_index}:{i}'>💾 Enregistrer</a></td></tr>"
            f"<tr><td><span style='font-family:Consolas,\"Courier New\",monospace; "
            f"color:{colors['code_fg']}'>{code_html}</span></td></tr></table>"
        )
        pos = b["end"]
    parts.append(_text_to_html(text[pos:], colors))
    if blocks:
        n = len(assign_filenames(blocks))
        parts.append(f"<p><a href='zip:{msg_index}'>📦 Télécharger le code en zip ({n} fichier"
                     f"{'s' if n > 1 else ''})</a> &nbsp;&nbsp; <a href='apply:{msg_index}'>"
                     f"🚀 Appliquer au dépôt</a> &nbsp;&nbsp; <a href='copyall:{msg_index}'>"
                     f"📋 Copier toute la réponse</a></p>")
    else:
        parts.append(f"<p><a href='copyall:{msg_index}'>📋 Copier la réponse</a></p>")
    return "".join(parts)
