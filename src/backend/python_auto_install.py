"""Installation automatique d'un runtime Python sous Windows pour IA Manager."""
import json
import os
from pathlib import Path
import shutil
import subprocess

def required_tag(tool_key: str) -> str:
    return "3.9" if tool_key == "audiocraft" else "3.11"

def _creationflags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

def manager_candidates():
    seen=set()
    for name in ("pymanager","py"):
        path=shutil.which(name)
        if path:
            key=os.path.normcase(os.path.abspath(path))
            if key not in seen:
                seen.add(key);yield path
    local=os.environ.get("LOCALAPPDATA")
    if not local:return
    base=Path(local)/"Microsoft"/"WindowsApps"
    if not base.is_dir():return
    for pattern in (
        "PythonSoftwareFoundation.PythonManager_*/*pymanager*.exe",
        "PythonSoftwareFoundation.PythonManager_*/*py.exe",
        "pymanager.exe","py.exe",
    ):
        for p in base.glob(pattern):
            if p.is_file():
                key=os.path.normcase(str(p.resolve()))
                if key not in seen:
                    seen.add(key);yield str(p)

def manager_program():
    for candidate in manager_candidates():
        try:
            run=subprocess.run([candidate,"help"],capture_output=True,text=True,timeout=5,creationflags=_creationflags())
            text=((run.stdout or "")+(run.stderr or "")).lower()
            if run.returncode==0 and ("install" in text or "python" in text):
                return candidate
        except Exception:
            pass
    return ""

def runtime_from_manager(manager: str, tag: str) -> str:
    if not manager:return ""
    for cmd in (
        [manager,"list","--one","--format=exe",tag],
        [manager,"list","-1","-f","exe",tag],
    ):
        try:
            run=subprocess.run(cmd,capture_output=True,text=True,timeout=8,creationflags=_creationflags())
            if run.returncode!=0:continue
            for raw in (run.stdout or "").splitlines():
                value=raw.strip().strip('"')
                if value.lower().endswith("python.exe") and Path(value).is_file():
                    return value
        except Exception:
            pass
    return ""

def winget_program():
    return shutil.which("winget") or ""

def python_manager_winget_args():
    return [
        "install","9NQ7512CXL7T","-e",
        "--accept-package-agreements","--accept-source-agreements",
        "--disable-interactivity",
    ]
