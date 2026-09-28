"""Catalogue image et client ComfyUI local. Aucun appel à Ollama."""
import time
import uuid
from urllib.parse import urlsplit
import requests
from src.backend.local_creation import validate_engine_url

MODELS = (
    dict(name="SDXL 1.0", specialty="Illustration, décors, images généralistes", repo="stabilityai/stable-diffusion-xl-base-1.0", direct=True, size=1024, steps=25, cfg=7.0,
         note="Télécharger le checkpoint sd_xl_base_1.0.safetensors. Le refiner est facultatif et n'est pas utilisé ici."),
    dict(name="SDXL Turbo", specialty="Création rapide et essais", repo="stabilityai/sdxl-turbo", direct=True, size=512, steps=4, cfg=1.0,
         note="Télécharger sd_xl_turbo_1.0_fp16.safetensors. Commencer en 512 × 512 ; le texte négatif n'a pas d'effet avec CFG 1."),
    dict(name="Animagine XL 4.0", specialty="Anime, personnages et illustrations manga", repo="cagliostrolab/animagine-xl-4.0", direct=True, size=1024, steps=28, cfg=5.0,
         note="Télécharger le checkpoint animagine-xl-4.0-opt.safetensors. Les descriptions en anglais et les tags sont adaptés à ce modèle."),
    dict(name="FLUX.1 Schnell", specialty="Création texte vers image en peu d'étapes", repo="black-forest-labs/FLUX.1-schnell", direct=False, size=1024, steps=4, cfg=1.0,
         note="Workflow FLUX requis avec ses encodeurs de texte et son VAE. Utiliser un modèle de workflow FLUX dans ComfyUI ; la génération simplifiée de cet onglet ne le prend pas en charge."),
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
    response.raise_for_status()
    names = response.json()['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError("Liste des modèles ComfyUI invalide.")
    return names


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


def generate(url, graph, progress=lambda _: None, local_only=True):
    url = base_url(url, local_only)
    response = _request('POST', url + '/prompt', json={'prompt': graph, 'client_id': str(uuid.uuid4())}, timeout=30)
    response.raise_for_status()
    answer = response.json()
    if answer.get('node_errors') or not answer.get('prompt_id'):
        raise ValueError("ComfyUI a refusé le workflow : " + str(answer.get('node_errors') or answer))
    prompt_id = answer['prompt_id']
    progress("Génération en cours dans ComfyUI…")
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        response = _request('GET', url + '/history/' + prompt_id, timeout=15)
        response.raise_for_status()
        history = response.json().get(prompt_id)
        if history:
            status = history.get('status', {})
            if status.get('status_str') == 'error':
                raise RuntimeError("Échec ComfyUI : " + str(status.get('messages', 'consultez ComfyUI'))[-1500:])
            for output in history.get('outputs', {}).values():
                for item in output.get('images', []):
                    response = _request('GET', url + '/view', params={k: item[k] for k in ('filename', 'subfolder', 'type') if k in item}, timeout=60)
                    response.raise_for_status()
                    return response.content
            if status.get('completed'):
                raise RuntimeError("La tâche est terminée sans image. Consultez ComfyUI.")
        time.sleep(1)
    raise TimeoutError("Attente dépassée (30 minutes). La tâche peut encore tourner dans ComfyUI : consultez son interface avant de relancer.")
