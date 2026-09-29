import ast
from pathlib import Path

from src.backend import studio_advisor as advisor
from src.backend import studio_catalog as catalog


def test_v103_catalog_extension_is_idempotent():
    before_models = len(catalog.MODELS)
    advisor.extend_catalog()
    after_once = len(catalog.MODELS)
    advisor.extend_catalog()
    assert len(catalog.MODELS) == after_once
    assert after_once >= before_models
    ids = [m["id"] for m in catalog.MODELS]
    assert len(ids) == len(set(ids))


def test_v103_has_rich_catalog_and_packs():
    advisor.extend_catalog()
    assert len(advisor.EXTRA_MODELS) >= 15
    assert len(advisor.EXTRA_TOOLS) >= 10
    assert len(advisor.PACKS) >= 7
    assert any(p["id"] == "full" for p in advisor.PACKS)


def test_pack_plan_respects_hardware():
    plan = advisor.pack_plan("image", vram=12, ram=32)
    assert plan["models"]
    assert plan["tools"]
    assert all(m["status"] in ("bon", "limite", "difficile", "inconnu") for m in plan["models"])
    assert any(m["status"] == "bon" for m in plan["models"])


def test_suitable_ids_exclude_difficult():
    plan = advisor.pack_plan("3d", vram=2, ram=8)
    chosen = set(advisor.suitable_model_ids(plan))
    difficult = {m["id"] for m in plan["models"] if m["status"] == "difficile"}
    assert not (chosen & difficult)


def test_extension_keeps_v102_fix_and_attaches_v103():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "ui" / "v100_extension.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "('huggingface','github','modelscope','civitai')" in source.replace(" ", "")
    assert "studio_advisor.extend_catalog()" in source
    assert "_attach_v103(tab)" in source
