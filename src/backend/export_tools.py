"""Export d'une discussion en PDF ou Word, pour la partager telle quelle.

Le PDF passe par QTextDocument/QPrinter (déjà fournis par PyQt6, pas de dépendance en plus).
Le Word est écrit à la main (zip + XML minimal) pour la même raison : pas de nouvelle
bibliothèque à faire passer par PyInstaller sur une machine qu'on ne peut pas tester ici."""

import xml.sax.saxutils as xmlutil
import zipfile
from html import escape
from pathlib import Path
from typing import Dict


def conversation_html(data: Dict) -> str:
    """HTML simple d'une discussion (utilisé pour l'export PDF)"""
    parts = [
        f"<h1>{escape(data.get('title') or 'Discussion')}</h1>",
        f"<p style='color:#666666'>Modèle : {escape(data.get('model', ''))} — "
        f"{escape(data.get('updated', ''))}</p>",
    ]
    for m in data.get("messages", []):
        who = "Vous" if m.get("role") == "user" else "IA"
        content = escape(m.get("content", "")).replace("\n", "<br>")
        parts.append(f"<h3>{who}</h3><p>{content}</p><hr>")
    return "".join(parts)


def export_pdf(data: Dict, dest: str) -> Path:
    """Écrit la discussion dans un PDF, avec QTextDocument + QPrinter (fournis par PyQt6)"""
    from PyQt6.QtCore import QMarginsF
    from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument
    from PyQt6.QtPrintSupport import QPrinter

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    doc = QTextDocument()
    doc.setHtml(conversation_html(data))

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(dest_path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageMargins(QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
    # Qt calcule seul la pagination à partir de la taille de page de l'imprimante.
    # PyQt6 a renommé QTextDocument::print() (pas de print_ comme en PyQt5).
    doc.print(printer)
    return dest_path


_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType='
    '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>'
)
_DOC_HEADER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
)
_DOC_FOOTER = '<w:sectPr/></w:body></w:document>'


def _paragraph(text: str, bold: bool = False, size: int = 22) -> str:
    """Un paragraphe Word ; chaque ligne du texte devient un saut de ligne dans le paragraphe."""
    rpr = f"<w:rPr>{'<w:b/>' if bold else ''}<w:sz w:val=\"{size}\"/></w:rPr>"
    runs = []
    for i, line in enumerate((text or "").split("\n")):
        if i:
            runs.append(f"<w:r>{rpr}<w:br/></w:r>")
        runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{xmlutil.escape(line)}</w:t></w:r>')
    return f"<w:p>{''.join(runs)}</w:p>"


def export_docx(data: Dict, dest: str) -> Path:
    """Écrit la discussion dans un .docx minimal mais valide (zip + XML, sans dépendance)."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    body = [_paragraph(data.get("title") or "Discussion", bold=True, size=32),
            _paragraph(f"Modèle : {data.get('model', '')} — {data.get('updated', '')}", size=18)]
    for m in data.get("messages", []):
        who = "Vous" if m.get("role") == "user" else "IA"
        body.append(_paragraph(who, bold=True, size=24))
        body.append(_paragraph(m.get("content", "")))
    document_xml = _DOC_HEADER + "".join(body) + _DOC_FOOTER

    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document_xml)
    return dest_path
