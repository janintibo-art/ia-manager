import tempfile
from pathlib import Path
from src.backend import blender_tools as b

def test_safe_name():
    assert b.safe_name('Mon personnage 3D!')=='Mon_personnage_3D'
    assert b.safe_name('...')=='projet_blender'

def test_supported_formats():
    assert '.glb' in b.SUPPORTED_IMPORTS
    assert 'fbx' in b.SUPPORTED_EXPORTS

def test_project_structure(monkeypatch):
    with tempfile.TemporaryDirectory() as root:
        monkeypatch.setattr(b,'project_root',lambda:Path(root))
        folder=b.create_project_directory('hero')
        assert (folder/'assets').is_dir()
        assert (folder/'textures').is_dir()
        assert (folder/'exports').is_dir()

def test_template_script_contains_save():
    with tempfile.TemporaryDirectory() as root:
        project=Path(root)/'hero'; project.mkdir()
        path=b.template_script(project,'personnage')
        text=path.read_text(encoding='utf-8')
        assert 'save_as_mainfile' in text
        assert 'ARM_L_REFERENCE' in text
        compile(text,str(path),'exec')

def test_conversion_script():
    with tempfile.TemporaryDirectory() as root:
        src=Path(root)/'asset.obj'; src.write_text('dummy',encoding='utf-8')
        dst=Path(root)/'asset.glb'; script=b.conversion_script(str(src),str(dst)); text=script.read_text(encoding='utf-8')
        assert 'obj_import' in text
        assert 'export_scene.gltf' in text
        compile(text,str(script),'exec')
