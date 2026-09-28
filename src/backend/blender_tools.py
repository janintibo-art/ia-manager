from __future__ import annotations
import os, re, shutil
from pathlib import Path
from typing import Dict, List, Optional
from src.backend import settings

SUPPORTED_IMPORTS = ('.glb', '.gltf', '.fbx', '.obj', '.stl', '.ply')
SUPPORTED_EXPORTS = ('glb', 'gltf', 'fbx', 'obj', 'stl', 'ply')

def _configured() -> Optional[Path]:
    value = str(settings.get('blender_executable') or '').strip()
    if value:
        p = Path(value).expanduser()
        if p.is_file():
            return p
    return None

def _windows_candidates() -> List[Path]:
    roots = []
    for env in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        value = os.environ.get(env)
        if value:
            roots.append(Path(value))
    candidates = []
    for base in roots:
        foundation = base / 'Blender Foundation'
        if foundation.is_dir():
            candidates.extend(foundation.glob('Blender */blender.exe'))
        direct = base / 'Blender' / 'blender.exe'
        if direct.is_file():
            candidates.append(direct)
    return candidates

def detect_blender() -> str:
    configured = _configured()
    if configured:
        return str(configured.resolve())
    found = shutil.which('blender')
    if found:
        return str(Path(found).resolve())
    if os.name == 'nt':
        versions = sorted(_windows_candidates(), reverse=True)
        if versions:
            return str(versions[0].resolve())
    return ''

def validate_executable(path: str) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError("L'exécutable Blender n'existe pas.")
    if os.name == 'nt' and p.suffix.lower() != '.exe':
        raise ValueError('Sous Windows, sélectionnez blender.exe.')
    return str(p.resolve())

def set_executable(path: str) -> str:
    value = validate_executable(path)
    settings.set('blender_executable', value)
    return value

def version_command(executable: str) -> Dict:
    return {'program': validate_executable(executable), 'args': ['--version'], 'cwd': str(Path(executable).parent)}

def project_root() -> Path:
    value = str(settings.get('blender_projects_root') or '').strip()
    if value:
        return Path(value).expanduser()
    storage_root = str(settings.get('storage_root') or '').strip()
    if storage_root:
        return Path(storage_root).expanduser() / 'Projets Blender'
    return Path.home() / 'IA Manager' / 'Projets Blender'

def set_project_root(path: str) -> str:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    probe = p / '.ia_manager_blender_write'
    probe.write_text('ok', encoding='utf-8')
    probe.unlink(missing_ok=True)
    settings.set('blender_projects_root', str(p.resolve()))
    return str(p.resolve())

def safe_name(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9._-]+', '_', str(value or '').strip()).strip('._-')
    return value[:80] or 'projet_blender'

def create_project_directory(name: str) -> Path:
    base = project_root()
    base.mkdir(parents=True, exist_ok=True)
    folder = base / safe_name(name)
    folder.mkdir(parents=True, exist_ok=True)
    for sub in ('assets', 'textures', 'exports', 'renders', 'scripts'):
        (folder / sub).mkdir(exist_ok=True)
    return folder

def launch_command(executable: str, blend_file: str = '') -> Dict:
    exe = validate_executable(executable)
    args = [str(Path(blend_file).resolve())] if blend_file else []
    return {'program': exe, 'args': args, 'cwd': str(project_root())}

def headless_script_command(executable: str, script: Path, blend_file: str = '') -> Dict:
    exe = validate_executable(executable)
    args = ['--background']
    if blend_file:
        args.append(str(Path(blend_file).resolve()))
    args += ['--python', str(Path(script).resolve())]
    return {'program': exe, 'args': args, 'cwd': str(script.parent)}

def template_script(project: Path, template: str) -> Path:
    project = Path(project).resolve()
    scripts = project / 'scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    output = project / (project.name + '.blend')
    template = template if template in ('personnage', 'objet', 'environnement') else 'objet'
    lines = [
        'import bpy',
        "bpy.ops.object.select_all(action='SELECT')",
        'bpy.ops.object.delete(use_global=False)',
        'scene=bpy.context.scene',
        "scene.render.engine='BLENDER_EEVEE_NEXT'",
        'scene.render.resolution_x=1024',
        'scene.render.resolution_y=1024',
        'scene.world.color=(0.035,0.035,0.05)',
    ]
    if template == 'personnage':
        lines += [
            'bpy.ops.mesh.primitive_cube_add(location=(0,0,1))',
            "bpy.context.object.name='BODY'",
            'bpy.context.object.scale=(0.45,0.28,0.75)',
            'bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,2.05))',
            "bpy.context.object.name='HEAD_REFERENCE'",
            'bpy.ops.mesh.primitive_cube_add(location=(-0.75,0,1.15))',
            "bpy.context.object.name='ARM_L_REFERENCE'",
            'bpy.context.object.scale=(0.22,0.22,0.65)',
            'bpy.ops.mesh.primitive_cube_add(location=(0.75,0,1.15))',
            "bpy.context.object.name='ARM_R_REFERENCE'",
            'bpy.context.object.scale=(0.22,0.22,0.65)',
            'bpy.ops.mesh.primitive_cube_add(location=(-0.25,0,0.15))',
            "bpy.context.object.name='LEG_L_REFERENCE'",
            'bpy.context.object.scale=(0.22,0.25,0.75)',
            'bpy.ops.mesh.primitive_cube_add(location=(0.25,0,0.15))',
            "bpy.context.object.name='LEG_R_REFERENCE'",
            'bpy.context.object.scale=(0.22,0.25,0.75)',
        ]
    elif template == 'environnement':
        lines += [
            'bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))',
            "bpy.context.object.name='GROUND'",
            'for x,y,s in [(-3,-2,1.5),(3,1,2.0),(0,4,1.2)]:',
            '    bpy.ops.mesh.primitive_cube_add(location=(x,y,s/2))',
            "    bpy.context.object.name='BLOCKOUT'",
            '    bpy.context.object.scale=(1.2,1.2,s/2)',
        ]
    else:
        lines += [
            'bpy.ops.mesh.primitive_cube_add(location=(0,0,0))',
            "bpy.context.object.name='ASSET'",
            'bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)',
        ]
    lines += [
        'bpy.ops.wm.save_as_mainfile(filepath=' + repr(str(output)) + ')',
        "print('IA_MANAGER_BLEND_CREATED::' + " + repr(str(output)) + ')',
    ]
    path = scripts / ('create_' + template + '.py')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path

def conversion_script(source: str, destination: str) -> Path:
    src = Path(source).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()
    if not src.is_file():
        raise ValueError("Le fichier 3D source n'existe pas.")
    if src.suffix.lower() not in SUPPORTED_IMPORTS:
        raise ValueError("Format d'import non pris en charge : " + src.suffix)
    fmt = dst.suffix.lower().lstrip('.')
    if fmt not in SUPPORTED_EXPORTS:
        raise ValueError("Format d'export non pris en charge : " + dst.suffix)
    dst.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'import bpy',
        'from pathlib import Path',
        'SRC=Path(' + repr(str(src)) + ')',
        'DST=Path(' + repr(str(dst)) + ')',
        "bpy.ops.object.select_all(action='SELECT')",
        'bpy.ops.object.delete(use_global=False)',
        'ext=SRC.suffix.lower()',
        "if ext in ('.glb','.gltf'): bpy.ops.import_scene.gltf(filepath=str(SRC))",
        "elif ext=='.fbx': bpy.ops.import_scene.fbx(filepath=str(SRC))",
        "elif ext=='.obj': bpy.ops.wm.obj_import(filepath=str(SRC))",
        "elif ext=='.stl': bpy.ops.wm.stl_import(filepath=str(SRC))",
        "elif ext=='.ply': bpy.ops.wm.ply_import(filepath=str(SRC))",
        "else: raise RuntimeError('Format import non pris en charge: '+ext)",
        'for obj in list(bpy.context.scene.objects):',
        "    if obj.type=='MESH':",
        '        obj.select_set(True)',
        '        bpy.context.view_layer.objects.active=obj',
        '        try: bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)',
        '        except Exception: pass',
        'fmt=DST.suffix.lower()',
        "if fmt=='.glb': bpy.ops.export_scene.gltf(filepath=str(DST), export_format='GLB')",
        "elif fmt=='.gltf': bpy.ops.export_scene.gltf(filepath=str(DST), export_format='GLTF_SEPARATE')",
        "elif fmt=='.fbx': bpy.ops.export_scene.fbx(filepath=str(DST), use_selection=False)",
        "elif fmt=='.obj': bpy.ops.wm.obj_export(filepath=str(DST), export_selected_objects=False)",
        "elif fmt=='.stl': bpy.ops.wm.stl_export(filepath=str(DST), export_selected_objects=False)",
        "elif fmt=='.ply': bpy.ops.wm.ply_export(filepath=str(DST), export_selected_objects=False)",
        "else: raise RuntimeError('Format export non pris en charge: '+fmt)",
        "print('IA_MANAGER_CONVERTED::'+str(DST))",
    ]
    script = dst.parent / ('.ia_manager_convert_' + safe_name(src.stem) + '_to_' + fmt + '.py')
    script.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return script

def clean_script(source_blend: str, destination_blend: str) -> Path:
    src = Path(source_blend).expanduser().resolve()
    dst = Path(destination_blend).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != '.blend':
        raise ValueError('Choisissez un fichier .blend valide.')
    dst.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'import bpy',
        'from pathlib import Path',
        'DST=Path(' + repr(str(dst)) + ')',
        'for obj in list(bpy.data.objects):',
        "    if obj.type=='MESH':",
        '        bpy.context.view_layer.objects.active=obj',
        '        obj.select_set(True)',
        '        try: bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)',
        '        except Exception: pass',
        '        obj.select_set(False)',
        'for block in (bpy.data.meshes,bpy.data.materials,bpy.data.images,bpy.data.curves):',
        '    for datablock in list(block):',
        '        if datablock.users==0: block.remove(datablock)',
        'bpy.ops.wm.save_as_mainfile(filepath=str(DST))',
        "print('IA_MANAGER_CLEANED::'+str(DST))",
    ]
    script = dst.parent / '.ia_manager_clean_scene.py'
    script.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return script
