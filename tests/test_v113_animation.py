
import tempfile
from pathlib import Path
from src.backend import blender_animation as a

def fake_blend(root,name="x.blend"):
    p=Path(root)/name; p.write_bytes(b"blend"); return p

def test_animation_library():
    assert {"idle","walk","run","attack","jump"} <= set(a.ANIMATIONS)

def test_procedural_script_compiles():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        dst=Path(root)/"walk.blend"
        script=a.procedural_animation_script(str(src),str(dst),"walk")
        text=script.read_text(encoding="utf-8")
        assert "IA_WALK" not in text or "ANIM" in text
        assert "keyframe_insert" in text
        compile(text,str(script),"exec")

def test_retarget_script_has_bake():
    with tempfile.TemporaryDirectory() as root:
        target=fake_blend(root,"target.blend")
        source=fake_blend(root,"source.blend")
        script=a.retarget_script(str(target),str(source),str(Path(root)/"retarget.blend"),1,60)
        text=script.read_text(encoding="utf-8")
        assert "nla.bake" in text
        assert "COPY_ROTATION" in text
        compile(text,str(script),"exec")

def test_animated_exports():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        glb=a.export_animated_script(str(src),str(Path(root)/"hero"),"glb")
        fbx=a.export_animated_script(str(src),str(Path(root)/"hero"),"fbx")
        assert "export_animations=True" in glb.read_text(encoding="utf-8")
        assert "bake_anim=True" in fbx.read_text(encoding="utf-8")
