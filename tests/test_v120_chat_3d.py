
from pathlib import Path
from src.backend import creative_chat_3d as c

def test_triposr_command_gpu(tmp_path):
    cmd = c.triposr_command(
        Path("python"), Path("source"), "input.png", tmp_path, "nvidia"
    )
    assert "run.py" in cmd
    assert "--model-save-format" in cmd
    assert "glb" in cmd
    assert "--device" not in cmd

def test_triposr_command_cpu(tmp_path):
    cmd = c.triposr_command(
        Path("python"), Path("source"), "input.png", tmp_path, "cpu"
    )
    assert cmd[-2:] == ["--device", "cpu"]

def test_hunyuan_command():
    cmd = c.hunyuan_command(Path("python"), "ref.png", Path("out.glb"), "nvidia")
    assert cmd[:3] == ["python", "-u", "-c"]
    code = cmd[-1]
    assert "Hunyuan3DDiTFlowMatchingPipeline" in code
    assert "mesh.export" in code
    compile(code, "<hunyuan-chat>", "exec")

def test_reference_required(monkeypatch):
    monkeypatch.setattr(c.creative_chat, "_save_reference_image", lambda items: "")
    try:
        c._reference([])
        assert False
    except ValueError as exc:
        assert "Joignez une image" in str(exc)
