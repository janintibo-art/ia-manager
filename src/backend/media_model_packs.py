"""Packs de modèles ComfyUI v171 : téléchargement multi-fichiers, reprise et vérification."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import requests

from src.backend import settings, creative_tools


PACKS = {
    "wan21": {
        "name": "Wan 2.1 T2V 1.3B — pack ComfyUI",
        "note": "Pack 480p : modèle 1.3B + encodeur UMT5 FP8 + VAE Wan.",
        "files": (
            {
                "folder": "diffusion_models",
                "name": "wan2.1_t2v_1.3B_fp16.safetensors",
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors?download=true",
            },
            {
                "folder": "text_encoders",
                "name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true",
            },
            {
                "folder": "vae",
                "name": "wan_2.1_vae.safetensors",
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true",
            },
        ),
    },
    "ltx-video": {
        "name": "LTX-2 FP8 — pack ComfyUI",
        "note": "Pack très lourd : checkpoint FP8 + encodeur Gemma 3. Prévoir plus de 30 Go de téléchargement.",
        "files": (
            {
                "folder": "checkpoints",
                "name": "ltx-2-19b-dev-fp8.safetensors",
                "url": "https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-dev-fp8.safetensors",
            },
            {
                "folder": "text_encoders",
                "name": "gemma_3_12B_it_fp4_mixed.safetensors",
                "url": "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors",
            },
        ),
    },
}


def pack_for(model_id: str):
    return PACKS.get(str(model_id or ""))


def managed_comfy_root():
    root = str(settings.get("creative_tools_root") or "").strip()
    if not root:
        return None
    try:
        source = creative_tools.paths(root, "comfyui")["source"]
    except Exception:
        return None
    return source if (source / "main.py").is_file() else None


def validate_comfy_root(folder):
    folder = Path(folder).expanduser().resolve()
    if (folder / "main.py").is_file() and (folder / "models").is_dir():
        return folder
    # Autorise le dossier models lui-même.
    if folder.name.lower() == "models" and (folder.parent / "main.py").is_file():
        return folder.parent
    raise ValueError("Choisissez le dossier racine de ComfyUI (celui qui contient main.py).")


def pack_state(model_id: str, comfy_root) -> Dict[str, object]:
    pack = pack_for(model_id)
    if not pack:
        return {"supported": False, "complete": False, "present": 0, "total": 0, "missing": []}
    root = validate_comfy_root(comfy_root)
    missing = []
    present = 0
    for item in pack["files"]:
        path = root / "models" / item["folder"] / item["name"]
        if path.is_file() and path.stat().st_size > 1024 * 1024:
            present += 1
        else:
            missing.append(str(path))
    return {
        "supported": True,
        "complete": not missing,
        "present": present,
        "total": len(pack["files"]),
        "missing": missing,
        "name": pack["name"],
        "note": pack["note"],
    }


def _download_one(url, target: Path, progress, prefix: str):
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    existing = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={existing}-"} if existing else {}

    with requests.Session() as session:
        session.trust_env = True
        with session.get(url, stream=True, timeout=(20, 120), headers=headers, allow_redirects=True) as response:
            if existing and response.status_code == 200:
                # Le serveur n'a pas accepté la reprise : repart proprement.
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
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = min(100, int(done * 100 / total))
                        progress(f"{prefix} · {pct}% · {target.name}")
                    else:
                        progress(f"{prefix} · {done // (1024*1024)} Mo · {target.name}")

    if total and part.stat().st_size < total:
        raise RuntimeError(f"Téléchargement incomplet : {target.name}")
    part.replace(target)
    return target


def install_pack(model_id: str, comfy_root, progress=lambda _text: None) -> List[str]:
    pack = pack_for(model_id)
    if not pack:
        raise ValueError("Aucun pack automatique n'est défini pour ce modèle.")
    root = validate_comfy_root(comfy_root)
    installed = []
    total_files = len(pack["files"])
    for index, item in enumerate(pack["files"], 1):
        target = root / "models" / item["folder"] / item["name"]
        if target.is_file() and target.stat().st_size > 1024 * 1024:
            progress(f"Fichier {index}/{total_files} déjà présent · {target.name}")
            installed.append(str(target))
            continue
        prefix = f"Fichier {index}/{total_files}"
        installed.append(str(_download_one(item["url"], target, progress, prefix)))
    progress("✅ Pack installé dans ComfyUI.")
    return installed
