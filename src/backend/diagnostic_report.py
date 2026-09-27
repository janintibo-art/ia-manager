"""Rapport de diagnostic partageable sans secrets ni chemins personnels."""
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
import platform
import shutil
import subprocess

import psutil


def _version(package):
    try:
        return version(package)
    except (PackageNotFoundError, ValueError):
        return 'absent'


def _command_version(executable, args=('--version',)):
    program = shutil.which(executable)
    if not program:
        return 'absent'
    try:
        result = subprocess.run([program, *args], capture_output=True, text=True,
                                timeout=4, check=False)
        text = (result.stdout or result.stderr).splitlines()
        return text[0][:100] if text else 'détecté'
    except (OSError, subprocess.TimeoutExpired):
        return 'détecté (version indisponible)'


def create_report():
    """Collecte un minimum de données; ne lit aucun journal ou paramètre sensible."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(__import__('pathlib').Path.home()))
    lines = [
        'IA Manager — diagnostic local',
        'Date : ' + datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z'),
        'Système : ' + platform.system() + ' ' + platform.release(),
        'Architecture : ' + platform.machine(),
        'Python : ' + platform.python_version(),
        'PyQt6 : ' + _version('PyQt6'),
        'RAM : {:.1f} Go au total, {:.1f} Go disponibles'.format(mem.total / 2**30, mem.available / 2**30),
        'Disque utilisateur : {:.1f} Go libres'.format(disk.free / 2**30),
        'Git : ' + _command_version('git'),
        'GitHub CLI : ' + _command_version('gh'),
        'Ollama : ' + _command_version('ollama'),
        'GPU NVIDIA : ' + _command_version('nvidia-smi', ('--query-gpu=name,memory.total', '--format=csv,noheader')),
        'Obliteratus installé : ' + ('oui' if _obliteratus_present() else 'non'),
        '',
        'Ce rapport ne contient ni jetons, ni noms de modèles privés, ni chemins de fichiers.',
    ]
    return '\n'.join(lines) + '\n'


def _obliteratus_present():
    from src.backend.obliteratus import environment_python
    return environment_python().is_file()
