import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class ModelScopeTests(unittest.TestCase):
    def test_listing_is_normalized(self):
        item = model_search.parse_modelscope_listing({"Path": "Qwen/Qwen3", "Downloads": 42, "Likes": 3})
        self.assertEqual(item["id"], "Qwen/Qwen3")
        self.assertEqual(item["pipeline"], "modelscope")

    @patch("src.backend.model_search.requests.get")
    def test_search_reads_models_payload(self, get):
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {"data": {"models": [{"id": "A/B"}]}}
        self.assertEqual(model_search.search_modelscope("qwen")[0]["id"], "A/B")


if __name__ == "__main__": unittest.main()
