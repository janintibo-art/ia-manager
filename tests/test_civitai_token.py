import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class CivitaiTokenTests(unittest.TestCase):
    def test_token_header(self):
        with patch("src.backend.settings.get", return_value="civitai-secret"):
            headers = model_search.civitai_headers()
        self.assertEqual(headers["Authorization"], "Bearer civitai-secret")


if __name__ == "__main__": unittest.main()
