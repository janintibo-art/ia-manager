"""Catalogue image et client ComfyUI local. Aucun appel à Ollama."""
import time
import uuid
from pathlib import Path
import requests
from src.backend.local_creation import validate_engine_url
from src.backend import settings
from src.backend import creative_tools

MODELS = (
    dict(name="SDXL 1.0", specialty="Illustration, décors, images généralistes", repo="stabilityai/stable-diffusion-xl-base-1.0", direct=True, size=1024, steps=25, cfg=7.0,
         filename="sd_xl_base_1.0.safetensors",
         download_url="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true",
         note="Téléchargement et installation automatiques disponibles. Le refiner est facultatif et n'est pas utilisé ici."),
    dict(name="SDXL Turbo", specialty="Création rapide et essais", repo="stabilityai/sdxl-turbo", direct=True, size=512, steps=4, cfg=1.0,
         filename="sd_xl_turbo_1.0_fp16.safetensors",
         download_url="https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors?download=true",
         note="Téléchargement et installation automatiques disponibles. Commencer en 512 × 512 ; le texte négatif n'a pas d'effet avec CFG 1."),
    dict(name="Animagine XL 4.0", specialty="Anime, personnages et illustrations manga", repo="cagliostrolab/animagine-xl-4.0", direct=True, size=1024, steps=28, cfg=5.0,
         filename="animagine-xl-4.0-opt.safetensors",
         download_url="https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0-opt.safetensors?download=true",
         note="Téléchargement et installation automatiques disponibles. Les descriptions en anglais et les tags sont adaptés à ce modèle."),
    dict(name="FLUX.1 Schnell", specialty="Création texte vers image en peu d'étapes", repo="black-forest-labs/FLUX.1-schnell", direct=False, size=1024, steps=4, cfg=1.0,
         filename="flux1-schnell-fp8.safetensors",
         download_url="https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors?download=true",
         note="Téléchargement automatique de la version FP8 ComfyUI disponible. La génération simplifiée de cet onglet reste désactivée : ouvrez ensuite le workflow FLUX dans ComfyUI."),
)


def base_url(value, local_only=True):
    return validate_engine_url(value, local_only)


def _request(method, url, **kwargs):
    # Une adresse locale ne doit pas passer par un proxy ou une redirection.
    with requests.Session() as session:
        session.trust_env = False
        response = session.request(method, url, allow_redirects=False, **kwargs)
        if 300 <= response.status_code < 400:
            raise ValueError("Redirection refusée : utilisez directement l'adresse du moteur.")
        response.raise_for_status()
        return response


def checkpoints(url, local_only=True):
    response = _request('GET', base_url(url, local_only) + '/object_info/CheckpointLoaderSimple', timeout=15)
    names = response.json()['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError("Liste des modèles ComfyUI invalide.")
    return names


def managed_checkpoints_dir():
    """Retourne le dossier checkpoints de ComfyUI lorsqu'il est géré par IA Manager."""
    root = str(settings.get('creative_tools_root') or '').strip()
    if not root:
        return None
    source = creative_tools.paths(root, 'comfyui')['source']
    if not source.is_dir():
        return None
    return source / 'models' / 'checkpoints'


def validate_checkpoints_dir(folder):
    folder = Path(folder).expanduser().resolve()
    # Accepte directement .../models/checkpoints ou crée le dossier s'il manque sous une source ComfyUI valide.
    if folder.name.lower() == 'checkpoints' and folder.parent.name.lower() == 'models':
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    candidate = folder / 'models' / 'checkpoints'
    if (folder / 'main.py').is_file() or (folder / 'comfy').is_dir():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    raise ValueError("Choisissez le dossier ComfyUI/models/checkpoints, ou le dossier racine de ComfyUI.")


def download_checkpoint(model, folder, progress=lambda _msg: None):
    url = model.get('download_url')
    filename = model.get('filename')
    if not url or not filename:
        raise ValueError("Ce modèle ne propose pas encore d'installation automatique. Utilisez sa fiche de téléchargement.")

    target_dir = validate_checkpoints_dir(folder)
    target = target_dir / filename
    partial = target.with_suffix(target.suffix + '.part')

    if target.is_file() and target.stat().st_size > 100 * 1024 * 1024:
        progress("Le checkpoint est déjà présent : " + str(target))
        return str(target)

    resume_from = partial.stat().st_size if partial.exists() else 0
    headers = {'Range': f'bytes={resume_from}-'} if resume_from else {}
    mode = 'ab' if resume_from else 'wb'

    progress("Connexion au serveur de téléchargement…")
    with requests.Session() as session:
        # Pour Hugging Face, les fichiers passent par une redirection CDN : elle est attendue ici.
        response = session.get(url, stream=True, allow_redirects=True, headers=headers, timeout=(20, 120))
        if resume_from and response.status_code == 200:
            # Le serveur n'a pas accepté la reprise : recommencer proprement.
            resume_from = 0
            mode = 'wb'
        elif response.status_code not in (200, 206):
            response.raise_for_status()

        remaining = int(response.headers.get('Content-Length') or 0)
        total = resume_from + remaining if remaining else 0
        downloaded = resume_from
        last_percent = -1

        target_dir.mkdir(parents=True, exist_ok=True)
        with partial.open(mode) as handle:
            for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = int(downloaded * 100 / total)
                    if percent != last_percent:
                        last_percent = percent
                        progress(f"Téléchargement {percent} % — {downloaded / (1024**3):.2f} / {total / (1024**3):.2f} Go")
                else:
                    progress(f"Téléchargement — {downloaded / (1024**3):.2f} Go reçus")

    # Empêche de considérer une petite page d'erreur comme un checkpoint valide.
    if not partial.is_file() or partial.stat().st_size < 100 * 1024 * 1024:
        raise RuntimeError("Le fichier téléchargé est anormalement petit. Téléchargement interrompu ou refusé.")

    partial.replace(target)
    progress("Checkpoint installé dans ComfyUI : " + str(target))
    return str(target)


def workflow(checkpoint, prompt, negative, size, steps, cfg, seed):
    if not checkpoint or not prompt.strip():
        raise ValueError("Choisissez un checkpoint et décrivez votre image.")
    if size not in (512, 768, 1024) or not 1 <= steps <= 60 or not 1 <= cfg <= 15:
        raise ValueError("Paramètres de génération invalides.")
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': checkpoint}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': size, 'height': size, 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0], 'seed': seed, 'steps': steps, 'cfg': cfg, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0}},
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'IA_Manager'}},
    }


def generate(url, graph, progress=lambda _: None, local_only=True, should_stop=lambda: False):
    url = base_url(url, local_only)
    response = _request('POST', url + '/prompt', json={'prompt': graph, 'client_id': str(uuid.uuid4())}, timeout=30)
    answer = response.json()
    if answer.get('node_errors') or not answer.get('prompt_id'):
        raise ValueError("ComfyUI a refusé le workflow : " + str(answer.get('node_errors') or answer))
    prompt_id = answer['prompt_id']
    progress("Génération en cours dans ComfyUI…")
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        if should_stop():
            try:
                _request('POST', url + '/interrupt', timeout=5)
            except Exception:
                pass
            raise InterruptedError("Création d’image arrêtée.")
        response = _request('GET', url + '/history/' + prompt_id, timeout=15)
        history = response.json().get(prompt_id)
        if history:
            status = history.get('status', {})
            if status.get('status_str') == 'error':
                raise RuntimeError("Échec ComfyUI : " + str(status.get('messages', 'consultez ComfyUI'))[-1500:])
            for output in history.get('outputs', {}).values():
                for item in output.get('images', []):
                    response = _request('GET', url + '/view', params={k: item[k] for k in ('filename', 'subfolder', 'type') if k in item}, timeout=60)
                    return response.content
            if status.get('completed'):
                raise RuntimeError("La tâche est terminée sans image. Consultez ComfyUI.")
        time.sleep(1)
    raise TimeoutError("Attente dépassée (30 minutes). La tâche peut encore tourner dans ComfyUI : consultez son interface avant de relancer.")
