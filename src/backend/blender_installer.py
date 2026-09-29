from __future__ import annotations
import os, shutil
BLENDER_PACKAGE_ID = "BlenderFoundation.Blender"
BLENDER_DOWNLOAD_URL = "https://www.blender.org/download/"
def winget_path(): return shutil.which("winget") or ""
def can_auto_install(): return os.name == "nt" and bool(winget_path())
def install_command():
    exe=winget_path()
    if not exe: raise ValueError("WinGet n'est pas disponible sur ce PC.")
    return {"program":exe,"args":["install","--id",BLENDER_PACKAGE_ID,"--exact","--source","winget","--accept-source-agreements","--accept-package-agreements"],"cwd":""}
def upgrade_command():
    exe=winget_path()
    if not exe: raise ValueError("WinGet n'est pas disponible sur ce PC.")
    return {"program":exe,"args":["upgrade","--id",BLENDER_PACKAGE_ID,"--exact","--source","winget","--accept-source-agreements","--accept-package-agreements"],"cwd":""}
def status_text(installed_path):
    if installed_path: return "✅ Blender détecté : "+installed_path
    if can_auto_install(): return "⚠️ Blender n'est pas installé. IA Manager peut l'installer avec WinGet."
    if os.name=="nt": return "⚠️ Blender n'est pas détecté et WinGet n'est pas disponible."
    return "⚠️ Blender n'est pas détecté. Installation automatique intégrée actuellement prévue pour Windows."
