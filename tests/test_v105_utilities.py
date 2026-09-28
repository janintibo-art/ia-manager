import ast
import tempfile
from pathlib import Path

from src.backend import local_utilities as utils
from src.backend import studio_pack_installer as packer
from src.backend import studio_advisor
from src.backend.studio_pack_v105 import extend_packs_v105


def test_utility_recipes_use_argument_lists():
    with tempfile.TemporaryDirectory(prefix="v105 tools ") as root:
        for key in utils.UTILITIES:
            git = "C:/Git/git.exe" if utils.UTILITIES[key].get("needs_git") else None
            plan = utils.install_plan(root, key, "C:/Python/python.exe", git, windows=True)
            assert plan
            assert all(isinstance(step["args"], list) for step in plan)
            assert any(step["args"][:2] == ["-m", "venv"] for step in plan)
            for step in plan:
                if "-c" in step["args"]:
                    ast.parse(step["args"][step["args"].index("-c") + 1])


def test_utility_manifest_protects_unmanaged_folder():
    with tempfile.TemporaryDirectory() as root:
        p = utils.paths(root, "rembg")["base"]
        p.mkdir(parents=True); (p / "keep.txt").write_text("keep")
        try:
            utils.prepare(root, "rembg")
            assert False, "prepare should reject unmanaged directory"
        except ValueError:
            pass
        assert (p / "keep.txt").read_text() == "keep"


def test_v105_packs_gain_automated_utilities():
    extend_packs_v105()
    full = studio_advisor.pack_by_id("full")
    assert "rembg" in full["tools"]
    assert "faster-whisper" in full["tools"]
    plan = packer.build_plan("full")
    assert any(x == "utility:rembg" for x in plan["managed"])
    assert any(x == "utility:chromadb" for x in plan["managed"])


def test_v104_plan_migrates_without_losing_pack():
    old = {"schema": 1, "pack_id": "image", "index": 2, "state": "installation", "last_error": ""}
    migrated = packer.sanitize(old)
    assert migrated["schema"] == 2
    assert migrated["pack_id"] == "image"
    assert migrated["index"] == 0


def test_python_kinds():
    assert packer.python_kind("engine:audiocraft") == "py39"
    assert packer.python_kind("engine:comfyui") == "py310"
    assert packer.python_kind("utility:demucs") == "py310"
