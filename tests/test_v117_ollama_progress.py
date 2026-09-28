
import json
from src.backend.ai_manager import AIManager

class FakeResponse:
    status_code = 200
    text = ""
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def close(self): pass
    def iter_lines(self, decode_unicode=True):
        events = [
            {"status": "pulling manifest"},
            {"status": "pulling abc", "completed": 25, "total": 100},
            {"status": "pulling abc", "completed": 100, "total": 100},
            {"status": "success"},
        ]
        for event in events:
            yield json.dumps(event)

def test_stream_progress(monkeypatch, tmp_path):
    manager = AIManager()
    progress = []
    statuses = []
    monkeypatch.setattr("src.backend.ai_manager.requests.post", lambda *a, **k: FakeResponse())
    monkeypatch.setattr(manager, "invalidate_model_cache", lambda *a, **k: None)
    assert manager.download_model_stream(
        "hf.co/test/model:Q4_K_M",
        on_progress=lambda done, total: progress.append((done, total)),
        on_status=statuses.append,
    )
    assert progress[-1] == (100, 100)
    assert "pulling manifest" in statuses
    assert "success" in statuses

def test_stream_cancel(monkeypatch):
    manager = AIManager()
    monkeypatch.setattr("src.backend.ai_manager.requests.post", lambda *a, **k: FakeResponse())
    try:
        manager.download_model_stream("x", should_stop=lambda: True)
        assert False
    except InterruptedError:
        pass
