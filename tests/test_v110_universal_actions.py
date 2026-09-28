import tempfile
from pathlib import Path

from src.backend import universal_actions as a


def item(source, **extra):
    value = {
        "source": source,
        "id": "owner/model",
        "name": "Model",
        "url": "https://example.test",
        "install_ref": "",
    }
    value.update(extra)
    return value


def test_actions_by_source():
    assert a.action_for(item("huggingface"))["kind"] == "search"
    assert a.action_for(item("github"))["source_index"] == 1
    assert a.action_for(item("civitai"))["source_index"] == 3
    assert a.action_for(item("pinokio", install_ref="https://github.com/x/y.git"))["kind"] == "pinokio-download"
    assert a.action_for(item("hf-spaces", install_ref="https://huggingface.co/spaces/a/b"))["kind"] == "clone-space"


def test_safe_folder_name():
    assert a.safe_folder_name("owner/my cool space") == "my-cool-space"
    assert a.safe_folder_name("../bad") == "bad"


def test_clone_space_command():
    with tempfile.TemporaryDirectory() as root:
        cmd = a.clone_command(
            item("hf-spaces", id="owner/demo",
                 install_ref="https://huggingface.co/spaces/owner/demo"),
            root, "git"
        )
        assert cmd["program"] == "git"
        assert cmd["args"][:3] == ["clone", "--depth", "1"]
        assert Path(cmd["target"]).parent == Path(root).resolve()


def test_clone_rejects_non_space_url():
    with tempfile.TemporaryDirectory() as root:
        try:
            a.clone_command(
                item("hf-spaces", install_ref="https://example.com/x"),
                root, "git"
            )
            assert False
        except ValueError:
            pass
