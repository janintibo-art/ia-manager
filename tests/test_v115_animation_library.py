
import tempfile
from pathlib import Path
from src.backend import animation_library as a

def test_classify():
    assert a.classify("Walking Forward")== "Walk"
    assert a.classify("Sword_Attack_01")== "Attack"
    assert a.classify("idle breathing")== "Idle"
    assert a.classify("something unknown")== "Other"

def test_scan_and_filter():
    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        (root/"walk.fbx").write_bytes(b"x"*10)
        (root/"attack.bvh").write_bytes(b"x"*20)
        (root/"ignore.txt").write_text("x")
        items=a.scan([str(root)])
        assert len(items)==2
        assert len(a.filter_items(items,category="Walk"))==1
        assert len(a.filter_items(items,query="attack"))==1

def test_metadata_roundtrip():
    with tempfile.TemporaryDirectory() as root:
        p=Path(root)/"dance.fbx"; p.write_bytes(b"x")
        a.save_metadata(str(p),{"category":"Dance","tags":["fun"],"notes":"ok"})
        data=a.load_metadata(str(p))
        assert data["category"]=="Dance"
        assert data["tags"]==["fun"]

def test_human_size():
    assert "Ko" in a.human_size(2048)
