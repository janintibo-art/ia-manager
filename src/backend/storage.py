"""Emplacements des données volumineuses et copie prudente vers un autre disque."""
import os
import shutil
import hashlib
import uuid
from pathlib import Path

from src.backend import settings


def root():
    value = str(settings.get("storage_root") or "").strip()
    return Path(value).expanduser() if value else None


def app_models():
    base = root()
    return base / "Modeles" / "Telechargements" if base else Path.home() / ".ia_manager" / "models"


def backups():
    base = root()
    return base / "Sauvegardes" if base else Path.home() / ".ia_manager" / "archives_chat"


def conversions():
    base = root()
    return base / "Modeles" / "Conversions" if base else Path.home() / "ia-conversion"


def ollama_models():
    value = str(settings.get("ollama_models_dir") or "").strip()
    return Path(value).expanduser() if value else Path.home() / ".ollama" / "models"


def validate_root(directory):
    path = Path(directory).expanduser()
    if not path.is_absolute() or str(path) == path.anchor or (os.name == "nt" and not path.drive):
        raise ValueError("Choisissez un dossier complet sur un disque, par exemple D:\\IA Manager.")
    path.mkdir(parents=True, exist_ok=True)
    probe = path / (".ia_manager_write_test_" + uuid.uuid4().hex)
    created = False
    try:
        with probe.open("xb") as stream:
            created = True
            stream.write(b"ok")
    finally:
        if created:
            probe.unlink(missing_ok=True)
    return path.resolve()


def copy_folder(source, destination):
    """Copie sans écrasement; échoue en cas de conflit ou de copie incomplète."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.exists():
        return 0
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("Le nouveau dossier ne peut pas contenir l'ancien (ni l'inverse).")
    copied = 0
    for current, dirs, files in os.walk(source):
        relative = Path(current).relative_to(source)
        target = destination / relative
        target.mkdir(parents=True, exist_ok=True)
        dirs[:] = [name for name in dirs if not (Path(current) / name).is_symlink()]
        for name in files:
            origin, output = Path(current) / name, target / name
            if origin.is_symlink():
                continue
            if output.exists():
                if output.stat().st_size != origin.stat().st_size or _digest(output) != _digest(origin):
                    raise FileExistsError(f"Conflit : {output}. Choisissez un dossier vide.")
                continue
            temp = output.with_name(output.name + ".ia-manager-part")
            try:
                temp.unlink(missing_ok=True)
                with origin.open("rb") as src, temp.open("xb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                if temp.stat().st_size != origin.stat().st_size:
                    raise IOError(f"Copie incomplète : {origin}")
                temp.replace(output)
                copied += 1
            finally:
                temp.unlink(missing_ok=True)
    return copied


def _digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()


def set_ollama_location(directory):
    """Règle Ollama pour les prochaines sessions Windows et ce processus."""
    value = str(validate_root(directory))
    if os.name == "nt":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            winreg.SetValueEx(key, "OLLAMA_MODELS", 0, winreg.REG_SZ, value)
        import ctypes
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(result))
    os.environ["OLLAMA_MODELS"] = value
    settings.set("ollama_models_dir", value)
