"""Chemins des ressources visuelles, en source ou dans l'EXE PyInstaller."""

import sys
from pathlib import Path


def asset(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "assets" / "branding" / name
