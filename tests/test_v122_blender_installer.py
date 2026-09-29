from src.backend import blender_installer as b
def test_package_id(): assert b.BLENDER_PACKAGE_ID=="BlenderFoundation.Blender"
def test_install_command(monkeypatch):
    monkeypatch.setattr(b,"winget_path",lambda:"winget")
    cmd=b.install_command()
    assert cmd["program"]=="winget"
    assert "install" in cmd["args"] and "BlenderFoundation.Blender" in cmd["args"] and "--exact" in cmd["args"]
def test_upgrade_command(monkeypatch):
    monkeypatch.setattr(b,"winget_path",lambda:"winget")
    cmd=b.upgrade_command()
    assert "upgrade" in cmd["args"] and "BlenderFoundation.Blender" in cmd["args"]
