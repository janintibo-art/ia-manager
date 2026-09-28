
import base64
import tempfile
from pathlib import Path
from src.backend import creative_chat as c

def test_creative_choices():
    ids={c.model_id(ref) for _label,ref,_m in c.choices()}
    assert {"sdxl","sdxl-turbo","animagine","musicgen-small","audiogen","hunyuan3d","triposr"} <= ids

def test_ref_detection():
    assert c.is_creative_ref("creative::sdxl")
    assert not c.is_creative_ref("ollama::qwen3:8b")
    assert c.model_for_ref("creative::audiogen")["kind"]=="audio"

def test_duration():
    assert c._duration("une boucle durée 12 s") == 12
    assert c._duration("un son court") == 8
    assert c._duration("durée 99 secondes") == 20

def test_save_3d_reference(monkeypatch):
    with tempfile.TemporaryDirectory() as root:
        monkeypatch.setattr(c,"creations_dir",lambda:Path(root))
        data=base64.b64encode(b"fakepng").decode("ascii")
        out=c._save_reference_image([{"kind":"image","mime":"image/png","data":data}])
        assert Path(out).read_bytes()==b"fakepng"

def test_checkpoint_selection(monkeypatch):
    monkeypatch.setattr(c.image_studio,"checkpoints",lambda url,local_only:["foo.safetensors","sd_xl_base_1.0.safetensors"])
    assert c._select_checkpoint("http://127.0.0.1:8188",("sd_xl_base",))=="sd_xl_base_1.0.safetensors"
