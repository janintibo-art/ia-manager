import tempfile
from pathlib import Path

from src.backend import settings
from src.backend import weight_storage as ws
from src.backend.studio_pack_v105 import extend_packs_v105


def test_human_size():
    assert ws.human_size(0) == "0 o"
    assert "Ko" in ws.human_size(2048)
    assert "Go" in ws.human_size(5 * 1024**3)


def test_inventory_and_cleanup_only_partial(monkeypatch):
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        (root / "ok.gguf").write_bytes(b"x" * 20)
        (root / "dl.gguf.part").write_bytes(b"x" * 10)
        outside = root.parent / "outside.tmp"
        outside.write_bytes(b"x" * 5)

        monkeypatch.setattr(ws, "known_locations", lambda: [
            {"id": "x", "name": "Test", "path": root},
        ])
        inv = ws.inventory()
        assert any(x["name"] == "ok.gguf" and not x["partial"] for x in inv)
        assert any(x["name"] == "dl.gguf.part" and x["partial"] for x in inv)

        result = ws.clean_partials([str(root / "dl.gguf.part"), str(root / "ok.gguf"), str(outside)])
        assert result["deleted"] == 1
        assert not (root / "dl.gguf.part").exists()
        assert (root / "ok.gguf").exists()
        assert outside.exists()
        outside.unlink()


def test_pack_estimate_has_margin():
    extend_packs_v105()
    estimate = ws.pack_storage_estimate("full")
    assert estimate["models"]
    assert estimate["recommended_gb"] >= estimate["raw_gb"]
    assert estimate["recommended_gb"] > 0


def test_free_space_and_folder_size():
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        (root / "a.bin").write_bytes(b"x" * 1234)
        assert ws.folder_size(root) >= 1234
        assert ws.free_space(root) > 0
