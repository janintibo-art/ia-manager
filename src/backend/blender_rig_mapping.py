
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List

from src.backend import blender_tools

PROFILES = {
    "ia_manager": {
        "name": "IA Manager",
        "bones": {
            "root": "root", "spine": "spine", "head": "head",
            "upper_arm_L": "upper_arm_L", "upper_arm_R": "upper_arm_R",
            "leg_L": "leg_L", "leg_R": "leg_R",
        },
    },
    "mixamo": {
        "name": "Mixamo",
        "bones": {
            "root": "mixamorig:Hips", "spine": "mixamorig:Spine2", "head": "mixamorig:Head",
            "upper_arm_L": "mixamorig:LeftArm", "upper_arm_R": "mixamorig:RightArm",
            "leg_L": "mixamorig:LeftUpLeg", "leg_R": "mixamorig:RightUpLeg",
        },
    },
    "generic": {
        "name": "Blender générique",
        "bones": {
            "root": "Hips", "spine": "Spine", "head": "Head",
            "upper_arm_L": "UpperArm.L", "upper_arm_R": "UpperArm.R",
            "leg_L": "Thigh.L", "leg_R": "Thigh.R",
        },
    },
}

def _blend(path: str) -> Path:
    p=Path(path).expanduser().resolve()
    if not p.is_file() or p.suffix.lower()!=".blend":
        raise ValueError("Choisissez une scène .blend valide.")
    return p

def save_mapping(path: str, mapping: Dict[str,str]) -> str:
    p=Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    clean={str(k):str(v).strip() for k,v in mapping.items() if str(k).strip() and str(v).strip()}
    p.write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding="utf-8")
    return str(p)

def load_mapping(path: str) -> Dict[str,str]:
    p=Path(path).expanduser().resolve()
    data=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data,dict): raise ValueError("Mapping invalide.")
    return {str(k):str(v) for k,v in data.items()}

def import_animation_script(target_blend: str, source_file: str, output: str) -> Path:
    target=_blend(target_blend)
    source=Path(source_file).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in (".fbx",".bvh"):
        raise ValueError("Source animation prise en charge : FBX ou BVH.")
    dst=Path(output).expanduser().resolve()
    lines=[
        "import bpy",
        f"SRC={repr(str(source))}",
        f"DST={repr(str(dst))}",
        "ext=SRC.lower().split('.')[-1]",
        "if ext=='fbx': bpy.ops.import_scene.fbx(filepath=SRC)",
        "elif ext=='bvh': bpy.ops.import_anim.bvh(filepath=SRC)",
        "else: raise RuntimeError('Format animation non pris en charge')",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_ANIM_IMPORTED::'+DST)",
    ]
    p=dst.parent/".ia_manager_import_anim.py"
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return p

def mapped_retarget_script(target_blend: str, source_blend: str, output: str,
                           mapping: Dict[str,str], start: int, end: int) -> Path:
    target=_blend(target_blend); source=_blend(source_blend)
    dst=Path(output).expanduser().resolve()
    mapping={str(k):str(v) for k,v in mapping.items() if str(k).strip() and str(v).strip()}
    start=max(1,int(start)); end=max(start,int(end))
    lines=[
        "import bpy",
        f"SOURCE={repr(str(source))}",
        f"DST={repr(str(dst))}",
        f"MAP={mapping!r}",
        f"START={start}",
        f"END={end}",
        "targets=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']",
        "if not targets: raise RuntimeError('Aucune armature cible')",
        "target=next((a for a in targets if a.name=='IA_AUTO_RIG'),targets[0])",
        "with bpy.data.libraries.load(SOURCE,link=False) as (data_from,data_to):",
        "    data_to.objects=[n for n in data_from.objects if n]",
        "for obj in data_to.objects:",
        "    if obj is not None: bpy.context.collection.objects.link(obj)",
        "sources=[o for o in data_to.objects if o and o.type=='ARMATURE']",
        "if not sources: raise RuntimeError('Aucune armature source')",
        "source=sources[0]",
        "for tname,sname in MAP.items():",
        "    tb=target.pose.bones.get(tname); sb=source.pose.bones.get(sname)",
        "    if not tb or not sb: continue",
        "    c=tb.constraints.new('COPY_ROTATION'); c.target=source; c.subtarget=sname",
        "    if tname=='root':",
        "        c2=tb.constraints.new('COPY_LOCATION'); c2.target=source; c2.subtarget=sname",
        "scene=bpy.context.scene; scene.frame_start=START; scene.frame_end=END",
        "bpy.context.view_layer.objects.active=target; target.select_set(True)",
        "bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')",
        "bpy.ops.nla.bake(frame_start=START,frame_end=END,only_selected=True,visual_keying=True,clear_constraints=True,use_current_action=True,bake_types={'POSE'})",
        "bpy.ops.object.mode_set(mode='OBJECT')",
        "if target.animation_data and target.animation_data.action: target.animation_data.action.name='IA_MAPPED_RETARGET'",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_MAPPED_RETARGET::'+DST)",
    ]
    p=dst.parent/".ia_manager_mapped_retarget.py"
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return p

def clip_script(source_blend: str, output: str, name: str, start: int, end: int) -> Path:
    src=_blend(source_blend)
    dst=Path(output).expanduser().resolve()
    name=str(name or "clip").strip()[:60] or "clip"
    start=max(1,int(start)); end=max(start,int(end))
    lines=[
        "import bpy",
        f"DST={repr(str(dst))}",
        f"NAME={repr(name)}",
        f"START={start}",
        f"END={end}",
        "arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']",
        "if not arms: raise RuntimeError('Aucune armature')",
        "arm=arms[0]",
        "scene=bpy.context.scene; scene.frame_start=START; scene.frame_end=END",
        "action=arm.animation_data.action if arm.animation_data else None",
        "if action:",
        "    action.name=NAME",
        "    for fc in action.fcurves:",
        "        pts=[kp for kp in fc.keyframe_points if START<=kp.co.x<=END]",
        "        for kp in list(fc.keyframe_points):",
        "            if kp not in pts: fc.keyframe_points.remove(kp)",
        "bpy.ops.wm.save_as_mainfile(filepath=DST)",
        "print('IA_MANAGER_CLIP::'+NAME+'::'+DST)",
    ]
    p=dst.parent/".ia_manager_clip.py"
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return p

def preview_script(source_blend: str, output: str, start: int, end: int) -> Path:
    src=_blend(source_blend)
    dst=Path(output).expanduser().resolve()
    start=max(1,int(start)); end=max(start,int(end))
    lines=[
        "import bpy",
        f"DST={repr(str(dst))}",
        f"START={start}",
        f"END={end}",
        "scene=bpy.context.scene",
        "scene.frame_start=START; scene.frame_end=END",
        "scene.render.resolution_x=512; scene.render.resolution_y=512; scene.render.resolution_percentage=100",
        "scene.render.filepath=DST",
        "scene.render.image_settings.file_format='FFMPEG'",
        "scene.render.ffmpeg.format='MPEG4'",
        "scene.render.ffmpeg.codec='H264'",
        "bpy.ops.render.render(animation=True)",
        "print('IA_MANAGER_PREVIEW::'+DST)",
    ]
    p=dst.parent/".ia_manager_preview.py"
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return p

def command(executable: str, script: Path, blend_file: str) -> Dict:
    return blender_tools.headless_script_command(executable,script,blend_file)
