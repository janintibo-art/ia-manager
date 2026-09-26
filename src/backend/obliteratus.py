"""Pont vers Obliteratus dans un environnement Python séparé de l'EXE."""
import os
import shutil
import sys
from pathlib import Path

UPSTREAM = "https://github.com/elder-plinius/OBLITERATUS"
REVISION = "b847511776a2afa7ed076f676184a4abfef2b162"
SPACE_URL = "https://huggingface.co/spaces/pliny-the-prompter/obliteratus"
PACKAGE = f"obliteratus[spaces] @ {UPSTREAM}/archive/{REVISION}.zip"


def tools_dir():
    return Path.home() / ".ia_manager" / "tools" / "obliteratus"


def environment_python():
    return tools_dir() / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def default_python():
    if not getattr(sys, "frozen", False):
        return sys.executable
    return shutil.which("python") or shutil.which("python3") or ""


def install_steps(python):
    executable = Path(python).expanduser()
    if not executable.is_file():
        raise ValueError("Choisissez un véritable exécutable Python 3.10 ou plus récent.")
    if getattr(sys, "frozen", False) and executable.resolve() == Path(sys.executable).resolve():
        raise ValueError("L'EXE IA Manager ne remplace pas une installation Python.")
    return [
        (str(executable), ["-c", "import sys; assert sys.version_info >= (3, 10), 'Python 3.10 minimum'"]),
        (str(executable), ["-m", "venv", str(tools_dir() / ".venv")]),
        (str(environment_python()), ["-m", "pip", "install", PACKAGE]),
    ]


def launch_command(port):
    if not 1024 <= int(port) <= 65535:
        raise ValueError("Port attendu entre 1024 et 65535.")
    return str(environment_python()), ["-u", "-m", "obliteratus", "ui", "--host", "127.0.0.1",
                                        "--port", str(port), "--no-browser"]


def local_url(port):
    return f"http://127.0.0.1:{int(port)}"
