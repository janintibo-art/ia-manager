import ast
from pathlib import Path

from src.backend import studio_pack_installer as packer


def test_build_plan_only_automates_supported_engines():
    plan = packer.build_plan("full")
    assert all(
        (kind == "engine" and key in packer.ENGINE_ALIASES.values())
        or (kind == "utility" and key in packer.UTILITY_ALIASES.values())
        for kind, key in map(packer.split_token, plan["managed"])
    )
    assert len(plan["managed"]) >= 2
    assert "utility:ffmpeg" in plan["managed"]


def test_audio_pack_knows_python39():
    plan = packer.build_plan("audio")
    assert "engine:audiocraft" in plan["managed"]
    assert packer.python_kind("engine:audiocraft") == "py39"
    assert packer.python_kind("engine:comfyui") == "py310"


def test_resume_helpers():
    plan = packer.build_plan("image")
    assert packer.current_key(plan) == "engine:comfyui"
    advanced = packer.advance(plan)
    assert advanced["index"] == 1
    errored = packer.mark_error(advanced, "network")
    assert errored["state"] == "erreur"
    assert "network" in errored["last_error"]
    reset = packer.reset(errored)
    assert reset["index"] == 0 and reset["state"] == "prêt"


def test_sanitize_rebuilds_from_official_pack():
    plan = packer.build_plan("3d")
    dirty = dict(plan)
    dirty["managed"] = ["evil", "triposr"]
    dirty["index"] = 999
    clean = packer.sanitize(dirty)
    assert "evil" not in clean["managed"]
    assert clean["index"] <= len(clean["managed"])


def test_extension_preserves_search_fix_and_v103():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "ui" / "v100_extension.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "('huggingface','github','modelscope','civitai')" in source.replace(" ", "")
    assert "_attach_v103(tab)" in source
    assert "_attach_v104(tab,window.creative_tools_tab)" in source.replace(" ", "")
