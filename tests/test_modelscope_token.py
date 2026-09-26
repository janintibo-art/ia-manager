import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class ModelScopeTokenTests(unittest.TestCase):
    def test_token_header(self):
        with patch("src.backend.settings.get", return_value="ms-secret"):
            self.assertEqual(model_search.modelscope_headers()["Authorization"], "Bearer ms-secret")


if __name__ == "__main__": unittest.main()
