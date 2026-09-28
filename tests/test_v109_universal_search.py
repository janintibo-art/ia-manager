from src.backend import universal_search as u


def test_classify_domains():
    assert u.classify("FLUX image generation ComfyUI") == "Image"
    assert u.classify("whisper speech transcription") == "Voix"
    assert u.classify("Hunyuan3D mesh") == "3D"
    assert u.classify("BGE embeddings RAG") == "RAG / documents"


def test_merge_deduplicates_and_sorts():
    a = [{"key": "x:1", "name": "A", "popularity": 1}]
    b = [{"key": "x:1", "name": "A2", "popularity": 5},
         {"key": "x:2", "name": "B", "popularity": 2}]
    merged = u.merge_results(a, b)
    assert len(merged) == 2
    assert merged[0]["key"] == "x:1"
    assert merged[0]["name"] == "A2"


def test_filter_results():
    rows = [
        {"source": "pinokio", "type": "Application / outil", "local": True, "key": "p:1"},
        {"source": "hf-spaces", "type": "Application / outil", "local": False, "key": "s:1"},
        {"source": "civitai", "type": "Image", "local": True, "key": "c:1"},
    ]
    assert len(u.filter_results(rows, local_only=True)) == 2
    assert len(u.filter_results(rows, type_name="Image")) == 1
    assert len(u.filter_results(rows, source="pinokio")) == 1


def test_sources_include_main_catalogs():
    ids = {sid for sid, _ in u.SOURCES}
    assert {"huggingface", "hf-spaces", "pinokio", "github", "civitai", "modelscope"} <= ids
