
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

from src.backend import (
    blender_tools, blender_game_ready, blender_animation, blender_rig_mapping
)

SCHEMA = 1

STEP_ORDER = (
    "import",
    "clean",
    "decimate",
    "uv",
    "rig",
    "animation",
    "retarget",
    "lod",
    "collision",
    "export",
)

STEP_LABELS = {
    "import": "Importer en .blend",
    "clean": "Nettoyer la scène",
    "decimate": "Réduire les polygones",
    "uv": "UV automatique",
    "rig": "Auto-rig",
    "animation": "Animation de base",
    "retarget": "Retargeting",
    "lod": "Générer les LOD",
    "collision": "Créer les collisions",
    "export": "Exporter pour le jeu",
}

SUPPORTED_INPUTS = (".blend", ".glb", ".gltf", ".fbx", ".obj", ".stl", ".ply")

def _safe_source(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError("Le modèle 3D source n'existe pas.")
    if p.suffix.lower() not in SUPPORTED_INPUTS:
        raise ValueError("Format source non pris en charge : " + p.suffix)
    return p

def _manifest_path(output_dir: str) -> Path:
    return Path(output_dir).expanduser().resolve() / "ia_manager_character_pipeline.json"

def save_manifest(plan: Dict[str, Any]) -> str:
    path = _manifest_path(plan["output_dir"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return str(path)

def load_manifest(output_dir: str) -> Dict[str, Any]:
    path = _manifest_path(output_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema") == SCHEMA:
            return data
    except (OSError, ValueError):
        pass
    return {}

def import_to_blend_script(source: str, output: str) -> Path:
    src = _safe_source(source)
    dst = Path(output).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".blend":
        raise ValueError("Une scène .blend n'a pas besoin d'import.")
    lines = [
        "import bpy",
        "from pathlib import Path",
        f"SRC=Path({repr(str(src))})",
        f"DST={repr(str(dst))}",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete(use_global=False)",
        "ext=SRC.suffix.lower()",
        "if ext in ('.glb','.gltf'): bpy.ops.import_scene.gltf(filepath=str(SRC))",
        "elif ext=='.fbx': bpy.ops.import_scene.fbx(filepath=str(SRC))",
        "elif ext=='.obj': bpy.ops.wm.obj_import(filepath=str(SRC))",
        "elif ext=='.stl': bpy.ops.wm.stl_import(filepath=str(SRC))",
        "elif ext=='.ply': bpy.ops.wm.ply_import(filepath=str(SRC))",
        "else: raise RuntimeError('Format import non pris en charge: '+ext)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_PIPELINE_IMPORTED::'+DST)",
    ]
    script = dst.parent / ".ia_manager_pipeline_import.py"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script

def new_plan(source: str, output_dir: str, options: Dict[str, Any]) -> Dict[str, Any]:
    src = _safe_source(source)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    enabled = []
    if src.suffix.lower() != ".blend":
        enabled.append("import")
    for step in STEP_ORDER:
        if step == "import":
            continue
        if bool(options.get(step, False)):
            enabled.append(step)
    if "export" not in enabled:
        enabled.append("export")

    name = blender_tools.safe_name(options.get("name") or src.stem)
    workspace = out / name
    workspace.mkdir(parents=True, exist_ok=True)

    plan = {
        "schema": SCHEMA,
        "name": name,
        "source": str(src),
        "output_dir": str(workspace),
        "enabled": enabled,
        "index": 0,
        "state": "prêt",
        "current_file": str(src),
        "last_error": "",
        "history": [],
        "options": {
            "decimate_ratio": float(options.get("decimate_ratio", 0.5)),
            "animation_name": str(options.get("animation_name") or "idle"),
            "animation_source": str(options.get("animation_source") or ""),
            "retarget_mapping": dict(options.get("retarget_mapping") or {}),
            "retarget_start": int(options.get("retarget_start", 1)),
            "retarget_end": int(options.get("retarget_end", 120)),
            "collision_mode": str(options.get("collision_mode") or "convex"),
            "engine": str(options.get("engine") or "godot"),
        },
    }
    save_manifest(plan)
    return plan

def sanitize(plan: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        return {}
    enabled = [s for s in plan.get("enabled", []) if s in STEP_ORDER]
    if not enabled:
        return {}
    plan = dict(plan)
    plan["enabled"] = enabled
    plan["index"] = max(0, min(int(plan.get("index") or 0), len(enabled)))
    plan["state"] = str(plan.get("state") or "prêt")[:40]
    plan["last_error"] = str(plan.get("last_error") or "")[:1000]
    plan["history"] = list(plan.get("history") or [])[-100:]
    return plan

def current_step(plan: Dict[str, Any]) -> str:
    idx = int(plan.get("index") or 0)
    steps = plan.get("enabled") or []
    return steps[idx] if 0 <= idx < len(steps) else ""

def _stage_path(plan: Dict[str, Any], suffix: str) -> Path:
    base = Path(plan["output_dir"])
    return base / f"{plan['name']}_{suffix}.blend"

def prepare_step(plan: Dict[str, Any], executable: str) -> Dict[str, Any]:
    step = current_step(plan)
    if not step:
        raise ValueError("Pipeline terminé.")
    src = Path(plan["current_file"]).resolve()
    out = Path(plan["output_dir"])
    opts = plan["options"]

    if step == "import":
        dst = _stage_path(plan, "import")
        script = import_to_blend_script(str(src), str(dst))
        cmd = blender_tools.headless_script_command(executable, script)
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if src.suffix.lower() != ".blend":
        raise ValueError("L'étape " + step + " nécessite une scène .blend.")

    if step == "clean":
        dst = _stage_path(plan, "clean")
        script = blender_tools.clean_script(str(src), str(dst))
        cmd = blender_tools.headless_script_command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "decimate":
        dst = _stage_path(plan, "lowpoly")
        script = blender_game_ready.decimate_script(str(src), str(dst), opts["decimate_ratio"])
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "uv":
        dst = _stage_path(plan, "uv")
        script = blender_game_ready.uv_script(str(src), str(dst))
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "rig":
        dst = _stage_path(plan, "rig")
        script = blender_game_ready.auto_rig_script(str(src), str(dst))
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "animation":
        dst = _stage_path(plan, opts["animation_name"])
        script = blender_animation.procedural_animation_script(str(src), str(dst), opts["animation_name"])
        cmd = blender_animation.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "retarget":
        source = str(opts.get("animation_source") or "").strip()
        if not source:
            raise ValueError("Aucune animation source n'est configurée pour le retargeting.")
        source_path = Path(source).expanduser().resolve()
        if source_path.suffix.lower() != ".blend":
            raise ValueError("Le retargeting du pipeline utilise une source .blend. Importez d'abord FBX/BVH.")
        dst = _stage_path(plan, "retarget")
        mapping = opts.get("retarget_mapping") or blender_rig_mapping.PROFILES["mixamo"]["bones"]
        script = blender_rig_mapping.mapped_retarget_script(
            str(src), str(source_path), str(dst), mapping,
            opts["retarget_start"], opts["retarget_end"]
        )
        cmd = blender_rig_mapping.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "lod":
        lod_dir = out / "LODs"
        script = blender_game_ready.lod_script(str(src), str(lod_dir))
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": "", "artifact": str(lod_dir)}

    if step == "collision":
        dst = _stage_path(plan, "collision")
        script = blender_game_ready.collision_script(str(src), str(dst), opts["collision_mode"])
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": str(dst)}

    if step == "export":
        target = out / f"{plan['name']}_{opts['engine']}.glb"
        script = blender_game_ready.export_script(str(src), str(target), opts["engine"])
        cmd = blender_game_ready.command(executable, script, str(src))
        return {"step": step, "label": STEP_LABELS[step], "command": cmd, "produces": "", "artifact": str(target)}

    raise ValueError("Étape inconnue : " + step)

def mark_started(plan: Dict[str, Any], step_info: Dict[str, Any]) -> Dict[str, Any]:
    plan = dict(plan)
    plan["state"] = "en cours"
    plan["last_error"] = ""
    plan["active_step"] = step_info["step"]
    save_manifest(plan)
    return plan

def mark_success(plan: Dict[str, Any], step_info: Dict[str, Any]) -> Dict[str, Any]:
    plan = dict(plan)
    produced = str(step_info.get("produces") or "")
    if produced:
        p = Path(produced)
        if not p.is_file():
            raise ValueError("Blender a terminé mais le fichier attendu est absent : " + produced)
        plan["current_file"] = str(p.resolve())
    artifact = str(step_info.get("artifact") or "")
    hist = list(plan.get("history") or [])
    hist.append({
        "step": step_info["step"],
        "label": step_info["label"],
        "status": "ok",
        "file": produced or artifact,
    })
    plan["history"] = hist[-100:]
    plan["index"] = int(plan.get("index") or 0) + 1
    plan["active_step"] = ""
    plan["last_error"] = ""
    plan["state"] = "terminé" if plan["index"] >= len(plan["enabled"]) else "prêt"
    save_manifest(plan)
    return plan

def mark_error(plan: Dict[str, Any], message: str) -> Dict[str, Any]:
    plan = dict(plan)
    plan["state"] = "erreur"
    plan["last_error"] = str(message)[:1000]
    plan["active_step"] = ""
    save_manifest(plan)
    return plan

def skip_step(plan: Dict[str, Any]) -> Dict[str, Any]:
    plan = dict(plan)
    step = current_step(plan)
    if not step:
        return plan
    hist = list(plan.get("history") or [])
    hist.append({"step": step, "label": STEP_LABELS[step], "status": "ignoré", "file": ""})
    plan["history"] = hist[-100:]
    plan["index"] = int(plan.get("index") or 0) + 1
    plan["state"] = "terminé" if plan["index"] >= len(plan["enabled"]) else "prêt"
    save_manifest(plan)
    return plan

def progress(plan: Dict[str, Any]) -> Dict[str, int]:
    total = len(plan.get("enabled") or [])
    done = min(int(plan.get("index") or 0), total)
    return {"done": done, "total": total, "percent": int((done / total) * 100) if total else 0}
