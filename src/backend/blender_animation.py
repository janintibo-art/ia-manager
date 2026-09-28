
from __future__ import annotations
from pathlib import Path
from typing import Dict, List

from src.backend import blender_tools

ANIMATIONS = {
    "idle": {"name": "Idle", "frames": 48},
    "walk": {"name": "Marche", "frames": 32},
    "run": {"name": "Course", "frames": 24},
    "attack": {"name": "Attaque", "frames": 20},
    "jump": {"name": "Saut", "frames": 30},
}

def _source(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file() or p.suffix.lower() != ".blend":
        raise ValueError("Choisissez une scène .blend valide.")
    return p

def _write(path: Path, lines: List[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

def procedural_animation_script(source: str, output: str, animation: str) -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    if animation not in ANIMATIONS:
        raise ValueError("Animation inconnue.")
    frames = ANIMATIONS[animation]["frames"]
    lines = [
        "import bpy, math",
        f"DST={repr(str(dst))}",
        f"ANIM={repr(animation)}",
        f"END={frames}",
        "arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']",
        "if not arms: raise RuntimeError('Aucune armature trouvée')",
        "arm=next((a for a in arms if a.name=='IA_AUTO_RIG'), arms[0])",
        "bpy.context.view_layer.objects.active=arm",
        "arm.select_set(True)",
        "bpy.ops.object.mode_set(mode='POSE')",
        "pb=arm.pose.bones",
        "def bone(name): return pb.get(name)",
        "scene=bpy.context.scene",
        "scene.frame_start=1",
        "scene.frame_end=END",
        "for b in pb:",
        "    b.rotation_mode='XYZ'",
        "    b.location=(0,0,0)",
        "    b.rotation_euler=(0,0,0)",
        "def key(bone_name,frame,rot=(0,0,0),loc=(0,0,0)):",
        "    b=bone(bone_name)",
        "    if not b: return",
        "    b.rotation_euler=rot",
        "    b.location=loc",
        "    b.keyframe_insert(data_path='rotation_euler',frame=frame)",
        "    b.keyframe_insert(data_path='location',frame=frame)",
        "if ANIM=='idle':",
        "    for f,z in [(1,0),(12,0.02),(24,0),(36,-0.02),(48,0)]:",
        "        key('spine',f,(0.02*math.sin(f),0,0),(0,0,z))",
        "        key('upper_arm_L',f,(0,0,0.08*math.sin(f)))",
        "        key('upper_arm_R',f,(0,0,-0.08*math.sin(f)))",
        "elif ANIM=='walk':",
        "    poses=[(1,0.55,-0.55),(9,-0.55,0.55),(17,0.55,-0.55),(25,-0.55,0.55),(32,0.55,-0.55)]",
        "    for f,l,r in poses:",
        "        key('leg_L',f,(l,0,0)); key('leg_R',f,(r,0,0))",
        "        key('upper_arm_L',f,(-r*0.7,0,0)); key('upper_arm_R',f,(-l*0.7,0,0))",
        "        key('root',f,(0,0,0),(0,0,0.03 if f%16 else 0))",
        "elif ANIM=='run':",
        "    poses=[(1,0.9,-0.9),(7,-0.9,0.9),(13,0.9,-0.9),(19,-0.9,0.9),(24,0.9,-0.9)]",
        "    for f,l,r in poses:",
        "        key('leg_L',f,(l,0,0)); key('leg_R',f,(r,0,0))",
        "        key('upper_arm_L',f,(-r,0,0)); key('upper_arm_R',f,(-l,0,0))",
        "        key('spine',f,(0.18,0,0))",
        "elif ANIM=='attack':",
        "    key('upper_arm_R',1,(0,0,0)); key('upper_arm_R',6,(-1.2,0,-0.4)); key('upper_arm_R',10,(0.8,0,0.6)); key('upper_arm_R',20,(0,0,0))",
        "    key('spine',1,(0,0,0)); key('spine',8,(0,0,-0.25)); key('spine',12,(0,0,0.3)); key('spine',20,(0,0,0))",
        "elif ANIM=='jump':",
        "    key('root',1,(0,0,0),(0,0,0)); key('root',8,(0,0,0),(0,0,-0.15)); key('root',16,(0,0,0),(0,0,1.2)); key('root',24,(0,0,0),(0,0,0.1)); key('root',30,(0,0,0),(0,0,0))",
        "    key('leg_L',8,(0.55,0,0)); key('leg_R',8,(0.55,0,0)); key('leg_L',16,(-0.25,0,0)); key('leg_R',16,(-0.25,0,0)); key('leg_L',30,(0,0,0)); key('leg_R',30,(0,0,0))",
        "bpy.ops.object.mode_set(mode='OBJECT')",
        "if arm.animation_data and arm.animation_data.action:",
        "    arm.animation_data.action.name='IA_'+ANIM.upper()",
        "scene.frame_set(1)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_ANIMATION::'+ANIM+'::'+DST)",
    ]
    return _write(dst.parent / f".ia_manager_anim_{animation}.py", lines)

def retarget_script(target_blend: str, source_blend: str, output: str, start: int = 1, end: int = 120) -> Path:
    target = _source(target_blend)
    source = _source(source_blend)
    dst = Path(output).expanduser().resolve()
    start = max(1, int(start))
    end = max(start, int(end))
    lines = [
        "import bpy",
        f"SOURCE={repr(str(source))}",
        f"DST={repr(str(dst))}",
        f"START={start}",
        f"END={end}",
        "target_arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']",
        "if not target_arms: raise RuntimeError('Aucune armature cible')",
        "target=next((a for a in target_arms if a.name=='IA_AUTO_RIG'),target_arms[0])",
        "with bpy.data.libraries.load(SOURCE, link=False) as (data_from,data_to):",
        "    data_to.objects=[n for n in data_from.objects if n]",
        "for obj in data_to.objects:",
        "    if obj is not None: bpy.context.collection.objects.link(obj)",
        "source_arms=[o for o in data_to.objects if o and o.type=='ARMATURE']",
        "if not source_arms: raise RuntimeError('Aucune armature source')",
        "source=source_arms[0]",
        "pairs=[]",
        "src_names={b.name.lower():b.name for b in source.pose.bones}",
        "aliases={",
        " 'root':['root','hips','pelvis'],",
        " 'spine':['spine','spine1','chest'],",
        " 'head':['head','neck'],",
        " 'upper_arm_L':['upper_arm_l','leftarm','arm_l'],",
        " 'upper_arm_R':['upper_arm_r','rightarm','arm_r'],",
        " 'leg_L':['leg_l','leftupleg','thigh_l'],",
        " 'leg_R':['leg_r','rightupleg','thigh_r'],",
        "}",
        "for tname,candidates in aliases.items():",
        "    tb=target.pose.bones.get(tname)",
        "    if not tb: continue",
        "    sname=next((src_names[c.lower()] for c in candidates if c.lower() in src_names),None)",
        "    if not sname: continue",
        "    sb=source.pose.bones.get(sname)",
        "    if not sb: continue",
        "    c=tb.constraints.new('COPY_ROTATION'); c.target=source; c.subtarget=sname; c.mix_mode='REPLACE'",
        "    if tname=='root':",
        "        c2=tb.constraints.new('COPY_LOCATION'); c2.target=source; c2.subtarget=sname",
        "    pairs.append((tb,sname))",
        "scene=bpy.context.scene; scene.frame_start=START; scene.frame_end=END",
        "bpy.context.view_layer.objects.active=target; target.select_set(True)",
        "bpy.ops.object.mode_set(mode='POSE')",
        "bpy.ops.pose.select_all(action='SELECT')",
        "bpy.ops.nla.bake(frame_start=START,frame_end=END,only_selected=True,visual_keying=True,clear_constraints=True,use_current_action=True,bake_types={'POSE'})",
        "bpy.ops.object.mode_set(mode='OBJECT')",
        "if target.animation_data and target.animation_data.action: target.animation_data.action.name='IA_RETARGET'",
        "for obj in source_arms:",
        "    bpy.data.objects.remove(obj,do_unlink=True)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_RETARGET_DONE::'+DST)",
    ]
    return _write(dst.parent / ".ia_manager_retarget.py", lines)

def export_animated_script(source: str, output: str, fmt: str = "glb") -> Path:
    src = _source(source)
    dst = Path(output).expanduser().resolve()
    fmt = fmt.lower()
    if fmt not in ("glb", "fbx"):
        raise ValueError("Format animé pris en charge : GLB ou FBX.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "glb":
        lines = [
            "import bpy",
            f"DST={repr(str(dst.with_suffix('.glb')))}",
            "bpy.ops.export_scene.gltf(filepath=DST,export_format='GLB',export_animations=True,export_apply=True)",
            "print('IA_MANAGER_ANIM_EXPORT::'+DST)",
        ]
    else:
        lines = [
            "import bpy",
            f"DST={repr(str(dst.with_suffix('.fbx')))}",
            "bpy.ops.export_scene.fbx(filepath=DST,bake_anim=True,add_leaf_bones=False,use_armature_deform_only=True)",
            "print('IA_MANAGER_ANIM_EXPORT::'+DST)",
        ]
    return _write(dst.parent / ".ia_manager_anim_export.py", lines)

def animation_info_script(source: str) -> Path:
    src = _source(source)
    path = src.parent / ".ia_manager_anim_info.py"
    lines = [
        "import bpy",
        "print('IA_MANAGER_ANIM_INFO_BEGIN')",
        "for obj in bpy.context.scene.objects:",
        "    if obj.type=='ARMATURE':",
        "        action=obj.animation_data.action if obj.animation_data else None",
        "        print('ARMATURE',obj.name,'ACTION',action.name if action else 'NONE')",
        "        if action:",
        "            print('FRAME_RANGE',int(action.frame_range[0]),int(action.frame_range[1]))",
        "print('IA_MANAGER_ANIM_INFO_END')",
    ]
    return _write(path, lines)

def command(executable: str, script: Path, blend_file: str) -> Dict:
    return blender_tools.headless_script_command(executable, script, blend_file)
