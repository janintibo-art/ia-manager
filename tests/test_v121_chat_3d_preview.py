
import tempfile
from pathlib import Path
from src.backend import chat_3d_preview as p

def test_preview_path():
    assert p.preview_path("hero.glb").name == "hero_preview.png"

def test_build_preview_script_compiles():
    with tempfile.TemporaryDirectory() as root:
        src=Path(root)/"hero.glb"
        src.write_bytes(b"glb")
        out=Path(root)/"preview.png"
        script=p.build_preview_script(str(src),str(out))
        text=script.read_text(encoding="utf-8")
        assert "import_scene.gltf" in text
        assert "BLENDER_EEVEE_NEXT" in text
        assert "render(write_still=True)" in text
        compile(text,str(script),"exec")

def test_game_defaults():
    with tempfile.TemporaryDirectory() as root:
        src=Path(root)/"hero.glb"
        src.write_bytes(b"glb")
        d=p.game_pipeline_defaults(str(src))
        assert d["clean"] is True
        assert d["decimate"] is True
        assert d["rig"] is True
        assert d["lod"] is True
        assert d["collision"] is True
        assert d["engine"]=="godot"
        assert d["decimate_ratio"]==0.5
