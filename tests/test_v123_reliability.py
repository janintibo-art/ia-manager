import base64
import tempfile
from pathlib import Path

import pytest

from src.backend import (
    blender_animation,
    blender_tools,
    character_pipeline,
    creative_chat,
    creative_chat_3d,
    mobile_server,
    settings,
    settings_backup,
    storage,
)


def test_creative_references_are_unique(monkeypatch):
    with tempfile.TemporaryDirectory() as root:
        monkeypatch.setattr(creative_chat, "creations_dir", lambda: Path(root))
        data = base64.b64encode(b"image").decode("ascii")
        one = creative_chat._save_reference_image([{"kind": "image", "data": data}])
        two = creative_chat._save_reference_image([{"kind": "image", "data": data}])
        assert one != two
        assert Path(one).is_file() and Path(two).is_file()


def test_global_offline_mode_reaches_3d_environment(monkeypatch):
    monkeypatch.setattr(settings, "get", lambda key: True if key == "offline_mode" else "")
    env = creative_chat_3d._env("/tmp/ia-manager", "triposr")
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"


def test_creative_paths_are_in_settings_backup(monkeypatch):
    monkeypatch.setattr(settings, "load", lambda: {
        "creative_tools_root": "D:/Outils",
        "blender_executable": "C:/Blender/blender.exe",
        "image_comfy_url": "http://127.0.0.1:8188",
    })
    saved = settings_backup.snapshot()["settings"]
    assert saved["creative_tools_root"] == "D:/Outils"
    assert saved["blender_executable"].endswith("blender.exe")
    assert saved["image_comfy_url"].endswith(":8188")


def test_storage_probe_does_not_delete_preexisting_file():
    with tempfile.TemporaryDirectory() as root:
        marker = Path(root) / ".ia_manager_write_test"
        marker.write_text("user data", encoding="utf-8")
        storage.validate_root(root)
        assert marker.read_text(encoding="utf-8") == "user data"


def test_pipeline_refuses_missing_artifact():
    with tempfile.TemporaryDirectory() as root:
        source = Path(root) / "hero.blend"
        source.write_bytes(b"blend")
        plan = character_pipeline.new_plan(str(source), root, {"name": "hero"})
        with pytest.raises(ValueError, match="sortie attendue"):
            character_pipeline.mark_success(plan, {
                "step": "export", "label": "Exporter", "produces": "",
                "artifact": str(Path(root) / "absent.glb"),
            })


def test_blender_scripts_fail_on_python_error_and_do_not_collide():
    with tempfile.TemporaryDirectory() as root:
        source = Path(root) / "hero.blend"
        source.write_bytes(b"blend")
        glb = blender_animation.export_animated_script(str(source), str(Path(root) / "hero"), "glb")
        fbx = blender_animation.export_animated_script(str(source), str(Path(root) / "hero"), "fbx")
        assert glb != fbx
        assert "export_animations=True" in glb.read_text(encoding="utf-8")
        command = blender_tools.headless_script_command(str(source), glb, str(source))
        assert command["args"][:2] == ["--background", str(source.resolve())]
        assert "--python-exit-code" in command["args"]


def test_network_enumeration_failure_does_not_block_app(monkeypatch):
    monkeypatch.setattr(mobile_server.psutil, "net_if_addrs", lambda: (_ for _ in ()).throw(PermissionError()))
    assert mobile_server.lan_addresses() == []
