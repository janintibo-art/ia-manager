
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List

from src.backend import creative_chat, creative_tools

MAX_SECONDS = 60 * 60

def _root() -> str:
    return creative_chat._tool_root()

def _reference(attachments: List[Dict]) -> str:
    path = creative_chat._save_reference_image(list(attachments or []))
    if not path:
        raise ValueError(
            "Joignez une image de référence au message. "
            "Pour un personnage : corps entier, de face, bras décollés du torse et jambes séparées."
        )
    return path

def _env(root: str, engine: str) -> Dict[str, str]:
    env = os.environ.copy()
    from src.backend import settings
    env.update(creative_tools.environment(root, engine, offline=bool(settings.get("offline_mode"))))
    return env

def _run(command, cwd: Path, env: Dict[str, str], should_stop=lambda: False) -> str:
    from src.backend import process_control
    proc = process_control.run(command, cwd=str(cwd), env=env, timeout=MAX_SECONDS, should_stop=should_stop)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "Le moteur 3D a échoué.")[-2200:]
        raise RuntimeError(tail)
    return (proc.stdout or "")[-1200:]

def triposr_command(python: Path, source: Path, image: str, output_dir: Path, hardware: str):
    args = [
        str(python), "-u", "run.py", image,
        "--output-dir", str(output_dir),
        "--model-save-format", "glb",
        "--mc-resolution", "256",
        "--foreground-ratio", "0.85",
    ]
    if hardware == "cpu":
        args += ["--device", "cpu"]
    return args

def hunyuan_command(python: Path, image: str, output_file: Path, hardware: str):
    # API officielle Hunyuan3D 2 : le pipeline renvoie un trimesh exportable.
    code = "\n".join([
        "import torch",
        "from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline",
        f"image={image!r}",
        f"output={str(output_file)!r}",
        "device='cuda' if torch.cuda.is_available() else 'cpu'",
        "pipe=Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2')",
        "try:",
        "    pipe=pipe.to(device)",
        "except Exception:",
        "    pass",
        "mesh=pipe(image=image)[0]",
        "mesh.export(output)",
        "print('IA_MANAGER_3D::'+output)",
    ])
    return [str(python), "-u", "-c", code]

def _copy_result(source: Path, model_id: str) -> Path:
    if not source.is_file():
        raise RuntimeError("Le moteur a terminé sans produire le GLB attendu.")
    out = creative_chat.creations_dir() / f"{model_id}_{time.strftime('%Y%m%d_%H%M%S')}.glb"
    if source.resolve() != out.resolve():
        shutil.copy2(source, out)
    return out

def generate_triposr(model: Dict, reference: str, should_stop=lambda: False) -> Dict:
    root = _root()
    state = creative_chat.tool_state("triposr")
    if not state["installed"]:
        raise RuntimeError("TripoSR n'est pas installé. Installez-le depuis Outils locaux.")
    paths = creative_tools.paths(root, "triposr")
    python = paths["python"]
    if not python.is_file():
        raise RuntimeError("Python TripoSR introuvable. Reprenez l'installation de TripoSR.")
    hardware = str(creative_tools.read_manifest(root, "triposr").get("hardware") or "nvidia")
    work = creative_chat.creations_dir() / ("triposr_job_" + time.strftime("%Y%m%d_%H%M%S"))
    work.mkdir(parents=True, exist_ok=True)
    command = triposr_command(python, paths["source"], reference, work, hardware)
    _run(command, paths["source"], _env(root, "triposr"), should_stop)
    result = _copy_result(work / "0" / "mesh.glb", model["id"])
    return {
        "kind": "3d",
        "path": str(result),
        "reference": reference,
        "label": model["label"],
        "engine": "triposr",
        "text": "Modèle 3D créé avec TripoSR. Le GLB est prêt pour Blender ou le Pipeline personnage.",
    }

def generate_hunyuan(model: Dict, reference: str, should_stop=lambda: False) -> Dict:
    root = _root()
    state = creative_chat.tool_state("hunyuan3d")
    if not state["installed"]:
        raise RuntimeError("Hunyuan3D 2 n'est pas installé. Installez-le depuis Outils locaux.")
    paths = creative_tools.paths(root, "hunyuan3d")
    python = paths["python"]
    if not python.is_file():
        raise RuntimeError("Python Hunyuan3D introuvable. Reprenez l'installation de Hunyuan3D 2.")
    hardware = str(creative_tools.read_manifest(root, "hunyuan3d").get("hardware") or "nvidia")
    work = creative_chat.creations_dir() / ("hunyuan3d_job_" + time.strftime("%Y%m%d_%H%M%S"))
    work.mkdir(parents=True, exist_ok=True)
    raw = work / "mesh.glb"
    command = hunyuan_command(python, reference, raw, hardware)
    _run(command, paths["source"], _env(root, "hunyuan3d"), should_stop)
    result = _copy_result(raw, model["id"])
    return {
        "kind": "3d",
        "path": str(result),
        "reference": reference,
        "label": model["label"],
        "engine": "hunyuan3d",
        "text": "Modèle 3D créé avec Hunyuan3D 2. Le GLB est prêt pour Blender ou le Pipeline personnage.",
    }

def generate_3d(ref: str, prompt: str, attachments=None, should_stop=lambda: False) -> Dict:
    model = creative_chat.model_for_ref(ref)
    if model.get("kind") != "3d":
        raise ValueError("Ce modèle n'est pas un moteur 3D.")
    reference = _reference(list(attachments or []))
    if model["engine"] == "triposr":
        return generate_triposr(model, reference, should_stop)
    if model["engine"] == "hunyuan3d":
        return generate_hunyuan(model, reference, should_stop)
    raise ValueError("Moteur 3D non pris en charge.")
