import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class CivitaiTests(unittest.TestCase):
    def test_listing_is_normalized(self):
        item = model_search.parse_civitai_listing({"id": 12, "name": "A LoRA", "type": "LORA",
                                                    "creator": {"username": "artist"},
                                                    "stats": {"downloadCount": 7}})
        self.assertEqual(item["id"], "12")
        self.assertEqual(item["pipeline"], "civitai")
        self.assertEqual(item["type"], "LORA")

    @patch("src.backend.model_search.requests.get")
    def test_search_reads_items(self, get):
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {"items": [{"id": 1, "name": "Style"}]}
        self.assertEqual(model_search.search_civitai("style")[0]["id"], "1")


if __name__ == "__main__": unittest.main()
