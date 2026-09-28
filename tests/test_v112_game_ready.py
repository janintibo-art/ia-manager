
import tempfile
from pathlib import Path
from src.backend import blender_game_ready as g

def fake_blend(root):
    p=Path(root)/"x.blend"; p.write_bytes(b"blend"); return p

def test_decimate_script():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root); dst=Path(root)/"low.blend"
        script=g.decimate_script(str(src),str(dst),0.5)
        text=script.read_text(encoding="utf-8")
        assert "DECIMATE" in text and "0.5" in text
        compile(text,str(script),"exec")

def test_lod_script():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root); out=Path(root)/"lods"
        script=g.lod_script(str(src),str(out))
        text=script.read_text(encoding="utf-8")
        assert "LOD0" in text or "LOD" in text
        assert "export_scene.gltf" in text
        compile(text,str(script),"exec")

def test_uv_and_collision():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        uv=g.uv_script(str(src),str(Path(root)/"uv.blend"))
        col=g.collision_script(str(src),str(Path(root)/"col.blend"),"convex")
        assert "smart_project" in uv.read_text(encoding="utf-8")
        assert "convex_hull" in col.read_text(encoding="utf-8")

def test_autorig_and_export():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        rig=g.auto_rig_script(str(src),str(Path(root)/"rig.blend"))
        exp=g.export_script(str(src),str(Path(root)/"game.glb"),"godot")
        assert "IA_AUTO_RIG" in rig.read_text(encoding="utf-8")
        assert "export_scene.gltf" in exp.read_text(encoding="utf-8")
