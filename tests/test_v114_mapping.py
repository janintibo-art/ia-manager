
import tempfile, json
from pathlib import Path
from src.backend import blender_rig_mapping as r

def fake(root,name="x.blend"):
    p=Path(root)/name; p.write_bytes(b"blend"); return p

def test_profiles():
    assert {"ia_manager","mixamo","generic"} <= set(r.PROFILES)
    assert "mixamorig:Hips" in r.PROFILES["mixamo"]["bones"].values()

def test_mapping_roundtrip():
    with tempfile.TemporaryDirectory() as root:
        p=Path(root)/"map.json"
        r.save_mapping(str(p),{"root":"Hips"})
        assert r.load_mapping(str(p))=={"root":"Hips"}

def test_import_fbx():
    with tempfile.TemporaryDirectory() as root:
        target=fake(root)
        source=Path(root)/"walk.fbx"; source.write_bytes(b"x")
        script=r.import_animation_script(str(target),str(source),str(Path(root)/"out.blend"))
        assert "import_scene.fbx" in script.read_text(encoding="utf-8")

def test_mapped_retarget_and_clip_compile():
    with tempfile.TemporaryDirectory() as root:
        target=fake(root,"t.blend"); source=fake(root,"s.blend")
        a=r.mapped_retarget_script(str(target),str(source),str(Path(root)/"o.blend"),{"root":"Hips"},1,30)
        c=r.clip_script(str(target),str(Path(root)/"clip.blend"),"walk",1,20)
        compile(a.read_text(encoding="utf-8"),str(a),"exec")
        compile(c.read_text(encoding="utf-8"),str(c),"exec")
