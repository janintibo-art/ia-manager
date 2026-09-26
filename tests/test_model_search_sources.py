import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class ModelSourceTests(unittest.TestCase):
    def test_github_listing_is_normalized(self):
        result = model_search.parse_github_listing({
            "full_name": "demo/model-gguf", "name": "model-gguf",
            "owner": {"login": "demo"}, "stargazers_count": 1200,
            "forks_count": 4, "description": "A local model", "topics": ["gguf"]})
        self.assertEqual(result["id"], "demo/model-gguf")
        self.assertEqual(result["downloads"], 1200)
        self.assertEqual(result["pipeline"], "github")

    @patch("src.backend.model_search.requests.get")
    def test_github_details_keeps_only_gguf_assets(self, get):
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = [{"tag_name": "v1", "assets": [
            {"name": "model-Q4_K_M.gguf", "size": 100, "browser_download_url": "https://x/model.gguf"},
            {"name": "README.txt", "size": 10, "browser_download_url": "https://x/readme"}]}]
        details = model_search.github_details("demo/model")
        self.assertEqual(len(details["quants"]), 1)
        self.assertEqual(details["quants"][0]["quant"], "Q4_K_M")


if __name__ == "__main__":
    unittest.main()
