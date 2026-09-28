import ast
from pathlib import Path


def test_v102_search_wiring():
    root = Path(__file__).resolve().parents[1]
    path = root / "src" / "ui" / "v100_extension.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert '("huggingface", "github", "modelscope", "civitai")' in source
    assert "self.detail_worker = FunctionWorker(ms.cached_details" in source
    assert "currentItemChanged.disconnect(tab.on_result_selected)" in source
    assert "currentItemChanged.connect(tab.on_result_selected)" in source
    assert "_repair_search_tab(window)" in source
