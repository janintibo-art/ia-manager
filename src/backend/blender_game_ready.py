
from __future__ import annotations
from pathlib import Path
from typing import Dict, List

from src.backend import blender_tools

ENGINES = ("godot", "unity", "unreal")

def _write_script(path: Path, lines: List[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

def _source(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError("Le fichier source n'existe pas.")
    if p.suffix.lower() != ".blend":
        raise ValueError("Choisissez une scène Blender .blend.")
    return p

def decimate_script(source: str, output: str, ratio: float) -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    ratio = max(0.05, min(float(ratio), 1.0))
    lines = [
        "import bpy",
        f"DST={repr(str(dst))}",
        f"RATIO={ratio!r}",
        "for obj in list(bpy.context.scene.objects):",
        "    if obj.type=='MESH':",
        "        bpy.context.view_layer.objects.active=obj",
        "        obj.select_set(True)",
        "        mod=obj.modifiers.new(name='IA_Decimate', type='DECIMATE')",
        "        mod.ratio=RATIO",
        "        try: bpy.ops.object.modifier_apply(modifier=mod.name)",
        "        except Exception: pass",
        "        obj.select_set(False)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_DECIMATED::'+DST)",
    ]
    return _write_script(dst.parent / ".ia_manager_decimate.py", lines)

def lod_script(source: str, output_dir: str, ratios=(1.0, 0.5, 0.25, 0.12)) -> Path:
    src = _source(source)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    ratios = [max(0.03, min(float(r), 1.0)) for r in ratios]
    lines = [
        "import bpy",
        "from pathlib import Path",
        f"OUT=Path({repr(str(out))})",
        f"RATIOS={ratios!r}",
        "base_objects=[o for o in bpy.context.scene.objects if o.type=='MESH']",
        "for idx,ratio in enumerate(RATIOS):",
        "    bpy.ops.object.select_all(action='DESELECT')",
        "    for obj in base_objects:",
        "        obj.select_set(True)",
        "        dup=obj.copy()",
        "        dup.data=obj.data.copy()",
        "        bpy.context.collection.objects.link(dup)",
        "        bpy.context.view_layer.objects.active=dup",
        "        mod=dup.modifiers.new(name='IA_LOD', type='DECIMATE')",
        "        mod.ratio=ratio",
        "        try: bpy.ops.object.modifier_apply(modifier=mod.name)",
        "        except Exception: pass",
        "        obj.select_set(False)",
        "    bpy.ops.object.select_all(action='DESELECT')",
        "    for o in bpy.context.scene.objects:",
        "        if o.type=='MESH' and o not in base_objects: o.select_set(True)",
        "    target=OUT / ('LOD'+str(idx)+'.glb')",
        "    bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True)",
        "    for o in list(bpy.context.selected_objects): bpy.data.objects.remove(o, do_unlink=True)",
        "print('IA_MANAGER_LOD_DONE::'+str(OUT))",
    ]
    return _write_script(out / ".ia_manager_lods.py", lines)

def uv_script(source: str, output: str, margin: float = 0.02) -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    margin = max(0.001, min(float(margin), 0.2))
    lines = [
        "import bpy",
        f"DST={repr(str(dst))}",
        f"MARGIN={margin!r}",
        "for obj in list(bpy.context.scene.objects):",
        "    if obj.type!='MESH': continue",
        "    bpy.context.view_layer.objects.active=obj",
        "    obj.select_set(True)",
        "    bpy.ops.object.mode_set(mode='EDIT')",
        "    bpy.ops.mesh.select_all(action='SELECT')",
        "    bpy.ops.uv.smart_project(island_margin=MARGIN)",
        "    bpy.ops.object.mode_set(mode='OBJECT')",
        "    obj.select_set(False)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_UV_DONE::'+DST)",
    ]
    return _write_script(dst.parent / ".ia_manager_uv.py", lines)

def collision_script(source: str, output: str, mode: str = "convex") -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    if mode not in ("convex", "box"):
        raise ValueError("Mode collision inconnu.")
    lines = [
        "import bpy",
        f"DST={repr(str(dst))}",
        f"MODE={repr(mode)}",
        "mesh_objs=[o for o in bpy.context.scene.objects if o.type=='MESH']",
        "for obj in mesh_objs:",
        "    bpy.context.view_layer.objects.active=obj",
        "    obj.select_set(True)",
        "    if MODE=='convex':",
        "        dup=obj.copy(); dup.data=obj.data.copy(); bpy.context.collection.objects.link(dup)",
        "        dup.name=obj.name+'_COLLISION'",
        "        bpy.context.view_layer.objects.active=dup",
        "        bpy.ops.object.mode_set(mode='EDIT')",
        "        bpy.ops.mesh.select_all(action='SELECT')",
        "        bpy.ops.mesh.convex_hull()",
        "        bpy.ops.object.mode_set(mode='OBJECT')",
        "    else:",
        "        bpy.ops.mesh.primitive_cube_add(location=obj.location)",
        "        dup=bpy.context.object; dup.name=obj.name+'_COLLISION'",
        "        dup.dimensions=obj.dimensions",
        "    obj.select_set(False)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_COLLISION_DONE::'+DST)",
    ]
    return _write_script(dst.parent / ".ia_manager_collision.py", lines)

def auto_rig_script(source: str, output: str) -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    lines = [
        "import bpy",
        "from mathutils import Vector",
        f"DST={repr(str(dst))}",
        "meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']",
        "if not meshes: raise RuntimeError('Aucun mesh à rigger')",
        "bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))",
        "arm=bpy.context.object; arm.name='IA_AUTO_RIG'",
        "edit=arm.data.edit_bones",
        "root=edit[0]; root.name='root'; root.head=(0,0,0); root.tail=(0,0,1)",
        "spine=edit.new('spine'); spine.head=(0,0,1); spine.tail=(0,0,2); spine.parent=root",
        "head=edit.new('head'); head.head=(0,0,2); head.tail=(0,0,2.6); head.parent=spine",
        "for side,x in (('L',-0.55),('R',0.55)):",
        "    arm_b=edit.new('upper_arm_'+side); arm_b.head=(0,0,1.8); arm_b.tail=(x,0,1.8); arm_b.parent=spine",
        "    leg=edit.new('leg_'+side); leg.head=(x*0.35,0,1); leg.tail=(x*0.35,0,0); leg.parent=root",
        "bpy.ops.object.mode_set(mode='OBJECT')",
        "for obj in meshes:",
        "    mod=obj.modifiers.new(name='Armature', type='ARMATURE'); mod.object=arm",
        "    obj.parent=arm",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_AUTORIG_DONE::'+DST)",
    ]
    return _write_script(dst.parent / ".ia_manager_autorig.py", lines)

def export_script(source: str, output: str, engine: str) -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    if engine not in ENGINES:
        raise ValueError("Moteur de jeu inconnu.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() != ".glb":
        dst = dst.with_suffix(".glb")
    y_up = engine in ("unity", "godot")
    lines = [
        "import bpy",
        f"DST={repr(str(dst))}",
        f"ENGINE={repr(engine)}",
        "for obj in bpy.context.scene.objects:",
        "    if obj.type=='MESH':",
        "        bpy.context.view_layer.objects.active=obj",
        "        obj.select_set(True)",
        "        try: bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)",
        "        except Exception: pass",
        "        obj.select_set(False)",
        "bpy.ops.export_scene.gltf(filepath=DST, export_format='GLB', export_apply=True)",
        "print('IA_MANAGER_GAME_EXPORT::'+ENGINE+'::'+DST)",
    ]
    return _write_script(dst.parent / ".ia_manager_game_export.py", lines)

def bake_script(source: str, output_dir: str, size: int = 2048) -> Path:
    src = _source(source)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    size = max(256, min(int(size), 8192))
    lines = [
        "import bpy",
        "from pathlib import Path",
        f"OUT=Path({repr(str(out))})",
        f"SIZE={size}",
        "scene=bpy.context.scene",
        "scene.render.engine='BLENDER_EEVEE_NEXT'",
        "for obj in [o for o in scene.objects if o.type=='MESH']:",
        "    bpy.context.view_layer.objects.active=obj",
        "    obj.select_set(True)",
        "    if not obj.data.uv_layers: ",
        "        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')",
        "    obj.select_set(False)",
        "print('IA_MANAGER_BAKE_PREPARED::'+str(OUT))",
    ]
    return _write_script(out / ".ia_manager_bake_prepare.py", lines)

def command(executable: str, script: Path, blend_file: str) -> Dict:
    return blender_tools.headless_script_command(executable, script, blend_file)
