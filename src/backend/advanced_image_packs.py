"""Packs Image avancés v180 pour ComfyUI."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import requests

from src.backend import creative_tools, settings


PACKS: Dict[str, Dict] = {
    "flux-dev": {
        "name": "FLUX.1-dev FP8",
        "note": "Checkpoint FP8 ComfyUI. Très volumineux (~17 Go).",
        "files": [
            {
                "folder": "checkpoints",
                "name": "flux1-dev-fp8.safetensors",
                "url": "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors",
            },
        ],
    },
    "sd35-medium": {
        "name": "Stable Diffusion 3.5 Medium FP8",
        "note": "Checkpoint ComfyUI tout-en-un avec encodeurs texte inclus (~11,6 Go).",
        "files": [
            {
                "folder": "checkpoints",
                "name": "sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors",
                "url": "https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/resolve/main/sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors",
            },
        ],
    },
    "controlnet": {
        "name": "ControlNet Union SDXL ProMax",
        "note": "Un seul modèle SDXL pour plusieurs types de contrôle (~2,5 Go).",
        "files": [
            {
                "folder": "controlnet",
                "name": "controlnet-union-sdxl-1.0-promax.safetensors",
                "url": "https://huggingface.co/xinsir/controlnet-union-sdxl-1.0/resolve/main/diffusion_pytorch_model_promax.safetensors",
            },
        ],
    },
    "ip-adapter": {
        "name": "IP-Adapter Plus SDXL",
        "note": "Installe le modèle IP-Adapter, l'encodeur CLIP Vision et le nœud ComfyUI_IPAdapter_plus.",
        "files": [
            {
                "folder": "ipadapter",
                "name": "ip-adapter-plus_sdxl_vit-h.safetensors",
                "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
            },
            {
                "folder": "clip_vision",
                "name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
                "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors",
            },
        ],
        "custom_node": {
            "folder": "ComfyUI_IPAdapter_plus",
            "repo": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
        },
    },
}


def pack_for(pack_id: str):
    return PACKS.get(str(pack_id or ""))


def managed_comfy_root():
    root = str(settings.get("creative_tools_root") or "").strip()
    if not root:
        return None
    source = creative_tools.paths(root, "comfyui")["source"]
    return source if (source / "main.py").is_file() else None


def validate_comfy_root(value):
    root = Path(value).expanduser().resolve()
    if (root / "main.py").is_file() and (root / "models").is_dir():
        return root
    raise ValueError("Choisissez le dossier racine de ComfyUI (celui qui contient main.py et models).")


def pack_state(pack_id: str, comfy_root):
    pack = pack_for(pack_id)
    if not pack:
        raise ValueError("Pack image avancé inconnu.")
    root = validate_comfy_root(comfy_root)
    present = []
    missing = []
    for item in pack["files"]:
        target = root / "models" / item["folder"] / item["name"]
        (present if target.is_file() and target.stat().st_size > 1024 * 1024 else missing).append(str(target))
    node = pack.get("custom_node")
    node_ready = True
    if node:
        node_ready = (root / "custom_nodes" / node["folder"]).is_dir()
    return {
        "complete": not missing and node_ready,
        "present": len(present),
        "total": len(pack["files"]),
        "missing": missing,
        "node_ready": node_ready,
    }


def _download_one(url: str, target: Path, progress, prefix: str):
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    existing = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={existing}-"} if existing else {}

    with requests.get(url, headers=headers, stream=True, timeout=(20, 180), allow_redirects=True) as response:
        if existing and response.status_code == 200:
            existing = 0
            try:
                part.unlink()
            except FileNotFoundError:
                pass
        elif existing and response.status_code != 206:
            response.raise_for_status()
        else:
            response.raise_for_status()

        total_header = int(response.headers.get("Content-Length") or 0)
        total = total_header + existing if response.status_code == 206 else total_header
        mode = "ab" if existing and response.status_code == 206 else "wb"
        done = existing
        with part.open(mode) as handle:
            for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                done += len(chunk)
                if total:
                    progress(f"{prefix} · {int(done * 100 / total)}% · {target.name}")
                else:
                    progress(f"{prefix} · {done // (1024*1024)} Mo · {target.name}")

    if not part.is_file() or part.stat().st_size < 1024 * 1024:
        raise RuntimeError("Téléchargement incomplet : " + target.name)
    part.replace(target)
    return target


def _install_custom_node(pack: Dict, root: Path, progress):
    node = pack.get("custom_node")
    if not node:
        return
    target = root / "custom_nodes" / node["folder"]
    if target.is_dir():
        progress("Nœud personnalisé déjà présent : " + node["folder"])
        return
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git est requis pour installer le nœud IP-Adapter. Installez Git depuis le Centre d'installation.")
    target.parent.mkdir(parents=True, exist_ok=True)
    progress("Installation du nœud ComfyUI : " + node["folder"])
    result = subprocess.run(
        [git, "clone", "--depth", "1", node["repo"], str(target)],
        cwd=str(target.parent),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        raise RuntimeError("Échec du clonage du nœud IP-Adapter : " + (result.stderr or result.stdout)[-800:])


def install_pack(pack_id: str, comfy_root, progress=lambda _text: None) -> List[str]:
    pack = pack_for(pack_id)
    if not pack:
        raise ValueError("Pack image avancé inconnu.")
    root = validate_comfy_root(comfy_root)
    installed = []
    total_files = len(pack["files"])
    for index, item in enumerate(pack["files"], 1):
        target = root / "models" / item["folder"] / item["name"]
        if target.is_file() and target.stat().st_size > 1024 * 1024:
            progress(f"Fichier {index}/{total_files} déjà présent · {target.name}")
            installed.append(str(target))
            continue
        installed.append(str(_download_one(item["url"], target, progress, f"Fichier {index}/{total_files}")))
    _install_custom_node(pack, root, progress)
    progress("✅ Pack image avancé installé dans ComfyUI.")
    return installed
