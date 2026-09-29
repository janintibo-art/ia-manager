
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict

from src.backend import blender_tools, creative_chat

MAX_SECONDS = 20 * 60

def preview_path(glb_path: str) -> Path:
    src = Path(glb_path).expanduser().resolve()
    return src.with_name(src.stem + "_preview.png")

def build_preview_script(glb_path: str, output_path: str) -> Path:
    src = Path(glb_path).expanduser().resolve()
    out = Path(output_path).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() not in (".glb", ".gltf"):
        raise ValueError("L'aperçu 3D attend un fichier GLB/GLTF valide.")
    out.parent.mkdir(parents=True, exist_ok=True)

    script = out.parent / (".ia_manager_preview_" + src.stem + ".py")
    lines = [
        "import bpy, math",
        "from mathutils import Vector",
        f"SRC={repr(str(src))}",
        f"OUT={repr(str(out))}",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete(use_global=False)",
        "bpy.ops.import_scene.gltf(filepath=SRC)",
        "meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']",
        "if not meshes: raise RuntimeError('Aucun mesh dans le GLB')",
        "pts=[]",
        "for obj in meshes:",
        "    for corner in obj.bound_box:",
        "        pts.append(obj.matrix_world @ Vector(corner))",
        "minv=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))",
        "maxv=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))",
        "center=(minv+maxv)*0.5",
        "size=max(maxv.x-minv.x,maxv.y-minv.y,maxv.z-minv.z,0.1)",
        "scene=bpy.context.scene",
        "scene.render.engine='BLENDER_EEVEE_NEXT'",
        "scene.render.resolution_x=512",
        "scene.render.resolution_y=512",
        "scene.render.resolution_percentage=100",
        "scene.render.image_settings.file_format='PNG'",
        "scene.render.filepath=OUT",
        "scene.world.color=(0.035,0.035,0.045)",
        "bpy.ops.object.camera_add(location=(center.x+size*1.7,center.y-size*1.7,center.z+size*1.25))",
        "cam=bpy.context.object",
        "direction=center-cam.location",
        "cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()",
        "cam.data.lens=52",
        "scene.camera=cam",
        "bpy.ops.object.light_add(type='AREA',location=(center.x+size,center.y-size,center.z+size*2.0))",
        "key=bpy.context.object",
        "key.data.energy=1100",
        "key.data.shape='DISK'",
        "key.data.size=size*2.0",
        "bpy.ops.object.light_add(type='AREA',location=(center.x-size*1.2,center.y+size*0.6,center.z+size*0.7))",
        "fill=bpy.context.object",
        "fill.data.energy=650",
        "fill.data.size=size*2.5",
        "bpy.ops.object.light_add(type='AREA',location=(center.x,center.y+size*1.5,center.z+size*1.5))",
        "rim=bpy.context.object",
        "rim.data.energy=800",
        "rim.data.size=size*1.8",
        "scene.view_settings.look='AgX - Medium High Contrast'",
        "bpy.ops.render.render(write_still=True)",
        "print('IA_MANAGER_3D_PREVIEW::'+OUT)",
    ]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script

def render_preview(glb_path: str, should_stop=lambda: False) -> Dict:
    src = Path(glb_path).expanduser().resolve()
    out = preview_path(str(src))
    blender = blender_tools.detect_blender()
    if not blender:
        raise RuntimeError(
            "Blender n'est pas détecté. Configurez Blender Studio avant de générer l'aperçu 3D."
        )
    script = build_preview_script(str(src), str(out))
    cmd = blender_tools.headless_script_command(blender, script)
    from src.backend import process_control
    proc = process_control.run(
        [cmd["program"], *cmd["args"]], cwd=cmd["cwd"], timeout=MAX_SECONDS,
        should_stop=should_stop,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "Blender n'a pas pu créer l'aperçu.")[-1800:])
    if not out.is_file():
        raise RuntimeError("Blender a terminé sans créer l'aperçu PNG.")
    return {"preview_path": str(out), "source": str(src)}

def game_pipeline_defaults(path: str) -> Dict:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise ValueError("Le GLB n'existe plus.")
    return {
        "source": str(src),
        "name": src.stem,
        "clean": True,
        "decimate": True,
        "uv": True,
        "rig": True,
        "animation": False,
        "retarget": False,
        "lod": True,
        "collision": True,
        "decimate_ratio": 0.5,
        "collision_mode": "convex",
        "engine": "godot",
    }
