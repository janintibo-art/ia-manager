
from src.backend import media_setup

def test_tool_mapping():
    assert media_setup.tool_for_model({"id":"hunyuan3d2","engine":"Hunyuan3D"})=="hunyuan3d"
    assert media_setup.tool_for_model({"id":"triposr","engine":"TripoSR"})=="triposr"
    assert media_setup.tool_for_model({"id":"musicgen-small","engine":"AudioCraft"})=="audiocraft"

def test_quick_guide():
    guide=media_setup.quick_guide({"id":"hunyuan3d2","engine":"Hunyuan3D"})
    assert guide["tool"]=="hunyuan3d"
    assert len(guide["steps"])>=4

def test_unknown_engine():
    guide=media_setup.quick_guide({"id":"unknown","engine":"Other"})
    assert guide["tool"]==""
