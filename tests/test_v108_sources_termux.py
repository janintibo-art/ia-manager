from src.backend import extra_sources, termux_center


def test_sources_present():
    ids = {s["id"] for s in extra_sources.SOURCES}
    assert {"stability-matrix", "hf-spaces", "comfy-registry", "openmodeldb"} <= ids


def test_hf_browser_search_url():
    url = extra_sources.browser_search_url("hf-spaces", "generate image")
    assert "type=space" in url
    assert "generate+image" in url


def test_termux_workflow_update():
    commands = termux_center.workflow_commands(
        "ia_manager", "janintibo-art", "v108 test", "update"
    )
    assert commands
    text = "\n".join(c for _, c in commands)
    assert "mise-a-jour.sh ia_manager" in text
    assert "gh run watch" in text


def test_ssh_args_are_argument_list():
    args = termux_center.ssh_args(
        "192.168.1.20", 8022, "u0_a123", "pwd", ""
    )
    assert args[-2] == "u0_a123@192.168.1.20"
    assert args[-1] == "pwd"
    assert "-p" in args and "8022" in args
