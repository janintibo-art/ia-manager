
import tempfile
from pathlib import Path
from src.backend import character_pipeline as p

def fake_blend(root,name="hero.blend"):
    f=Path(root)/name; f.write_bytes(b"blend"); return f

def test_plan_order_and_export():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        plan=p.new_plan(str(src),root,{"name":"hero","clean":True,"uv":True,"rig":True,"export":True})
        assert plan["enabled"]==["clean","uv","rig","export"]
        assert p.current_step(plan)=="clean"

def test_non_blend_adds_import():
    with tempfile.TemporaryDirectory() as root:
        src=Path(root)/"hero.obj"; src.write_text("x")
        plan=p.new_plan(str(src),root,{"name":"hero","clean":True})
        assert plan["enabled"][0]=="import"

def test_manifest_roundtrip():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        plan=p.new_plan(str(src),root,{"clean":True})
        loaded=p.load_manifest(plan["output_dir"])
        assert loaded["name"]==plan["name"]
        assert loaded["source"]==plan["source"]

def test_import_script_compiles():
    with tempfile.TemporaryDirectory() as root:
        src=Path(root)/"hero.obj"; src.write_text("x")
        script=p.import_to_blend_script(str(src),str(Path(root)/"hero.blend"))
        compile(script.read_text(encoding="utf-8"),str(script),"exec")

def test_skip_progress():
    with tempfile.TemporaryDirectory() as root:
        src=fake_blend(root)
        plan=p.new_plan(str(src),root,{"clean":True,"uv":True})
        plan=p.skip_step(plan)
        prog=p.progress(plan)
        assert prog["done"]==1
        assert prog["total"]==3
