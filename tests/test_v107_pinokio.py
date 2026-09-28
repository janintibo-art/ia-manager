from src.backend import pinokio_integration as p


def test_normalize_registry_item():
    item = p.normalize_item({
        "id": "example-app",
        "title": "Example AI",
        "description": "Local AI app",
        "repo": "https://github.com/example/app.git",
        "tags": ["image", "local"],
        "author": {"name": "dev"},
    })
    assert item["id"] == "example-app"
    assert item["name"] == "Example AI"
    assert item["install_uri"].startswith("https://github.com/")
    assert item["author"] == "dev"


def test_rows_accept_common_registry_shapes():
    assert p._rows([{"id": "a"}]) == [{"id": "a"}]
    assert p._rows({"results": [{"id": "b"}]}) == [{"id": "b"}]
    assert p._rows({"data": {"items": [{"id": "c"}]}}) == [{"id": "c"}]


def test_safe_export_removes_raw():
    clean = p.safe_export({"id": "a", "raw": {"secret": "x"}})
    assert clean == {"id": "a"}


def test_commands_require_pterm(monkeypatch):
    monkeypatch.setattr(p, "pterm_path", lambda: "pterm")
    item = {"install_uri": "https://github.com/example/app.git"}
    assert p.download_command(item)["args"] == ["download", item["install_uri"]]
    run = p.run_command(item)["args"]
    assert run[:2] == ["run", item["install_uri"]]
    assert "--open" in run
