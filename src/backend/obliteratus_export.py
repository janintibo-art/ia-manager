"""Conversion locale isolée des checkpoints, puis import Ollama."""
import json
import os
import re
import shutil
import time
from pathlib import Path

def model_library(root=None, export_root=None):
    """Checkpoints complets et conversions locales associées, sans charger les poids."""
    export_root = Path(export_root) if export_root else Path.home() / 'ia-conversion/exports'
    conversions = {}
    for manifest in export_root.glob('*/source.json'):
        try:
            info = json.loads(manifest.read_text(encoding='utf-8'))
            gguf = manifest.parent / 'model.gguf'
            if gguf.is_file() and gguf.stat().st_size > 0:
                conversions.setdefault(str(Path(info['checkpoint']).resolve()), []).append(
                    {'name': info['name'], 'path': str(gguf), 'size': gguf.stat().st_size})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    result = []
    for path in checkpoints(root):
        try:
            weight_files = list(path.glob('*.safetensors'))
            size = sum(f.stat().st_size for f in weight_files)
            config = json.loads((path / 'config.json').read_text(encoding='utf-8'))
            family = config.get('model_type') or config.get('architectures', ['Modèle'])[0]
            result.append({'path': str(path), 'run': path.parent.name,
                           'family': str(family), 'size': size,
                           'exports': conversions.get(str(path.resolve()), [])})
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            continue
    return result

PREPARE = r'''
import pathlib, sys, urllib.request, zipfile, tempfile, shutil
root = pathlib.Path(sys.argv[1])
target = root / 'llama.cpp-master'
if not (target / 'convert_hf_to_gguf.py').is_file():
    print('Téléchargement du convertisseur officiel llama.cpp...', flush=True)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        archive = pathlib.Path(temp) / 'source.zip'
        urllib.request.urlretrieve('https://github.com/ggml-org/llama.cpp/archive/refs/heads/master.zip', archive)
        unpack = pathlib.Path(temp) / 'unpack'
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                path = pathlib.PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in item.filename:
                    raise ValueError('Chemin interdit dans archive')
            z.extractall(unpack)
        if target.exists():
            raise RuntimeError('Installation incomplète du convertisseur : choisir un autre dossier outil.')
        shutil.move(str(unpack / 'llama.cpp-master'), target)
print('Convertisseur prêt.', flush=True)
'''

def checkpoints(root=None):
    root = Path(root) if root else Path.home() / '.local/state/obliteratus/runs'
    return sorted((p for p in root.glob('*/checkpoint') if valid_checkpoint(p)),
                  key=lambda p: p.stat().st_mtime, reverse=True)

def valid_checkpoint(path):
    path = Path(path)
    if not ((path / 'config.json').is_file() and any(path.glob('*.safetensors')) and (path / 'tokenizer_config.json').is_file()):
        return False
    index = path / 'model.safetensors.index.json'
    if index.is_file():
        try:
            weights = json.loads(index.read_text(encoding='utf-8'))['weight_map']
            return bool(weights) and all(isinstance(f, str) and Path(f).name == f and (path / f).is_file() for f in weights.values())
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False
    return True

def make_steps(checkpoint, name, python, root=None, ollama=None):
    checkpoint = Path(checkpoint).resolve()
    if not valid_checkpoint(checkpoint):
        raise ValueError('Choisissez un checkpoint complet : config, tokenizer et Safetensors.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}', name):
        raise ValueError('Nom : 1 à 64 caractères, minuscules, chiffres, tiret, point ou soulignement.')
    if not Path(python).is_file():
        raise ValueError('Installez Obliteratus avant de convertir un modèle.')
    ollama = ollama or shutil.which('ollama')
    if not ollama and os.name == 'nt':
        candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'
        if candidate.is_file():
            ollama = str(candidate)
    if not ollama:
        raise ValueError('Ollama introuvable : installez-le, puis relancez IA Manager.')
    root = Path(root) if root else Path.home() / 'ia-conversion'
    venv = root / 'venv'
    converter_python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    source = root / 'llama.cpp-master'
    # Une sortie distincte préserve les conversions précédentes, même en cas d'échec.
    output = root / 'exports' / (name + '-' + str(time.time_ns()))
    output.mkdir(parents=True, exist_ok=False)
    gguf = output / 'model.gguf'
    modelfile = output / 'Modelfile'
    modelfile.write_text('FROM ./model.gguf\n', encoding='utf-8')
    (output / 'source.json').write_text(
        json.dumps({'checkpoint': str(checkpoint), 'name': name}, ensure_ascii=False), encoding='utf-8')
    steps = [(str(python), ['-u', '-c', PREPARE, str(root)])]
    if not converter_python.is_file():
        steps.append((str(python), ['-m', 'venv', str(venv)]))
    steps.extend([
        (str(converter_python), ['-m', 'pip', 'install', '-r', str(source / 'requirements/requirements-convert_hf_to_gguf.txt')]),
        (str(converter_python), ['-u', str(source / 'convert_hf_to_gguf.py'), str(checkpoint), '--outfile', str(gguf), '--outtype', 'f16']),
        (str(ollama), ['create', name, '-f', str(modelfile)]),
    ])
    return steps
