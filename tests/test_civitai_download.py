import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class CivitaiDownloadTests(unittest.TestCase):
    @patch("src.backend.model_search.requests.get")
    def test_downloads_file(self, get):
        class Response:
            status_code = 200; headers = {"Content-Length": "3"}
            def raise_for_status(self): pass
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def iter_content(self, chunk_size=0): return [b"abc"]
        get.return_value = Response()
        with tempfile.TemporaryDirectory() as folder, patch("pathlib.Path.home", return_value=Path(folder)):
            result = model_search.download_civitai_file({"asset": "style.safetensors", "size": 3,
                                                          "download_url": "https://x/style"})
            self.assertEqual(Path(result).read_bytes(), b"abc")


if __name__ == "__main__": unittest.main()
