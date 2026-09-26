import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class ModelSearchCacheTests(unittest.TestCase):
    def test_detail_is_cached(self):
        model_search.clear_detail_cache()
        with patch("src.backend.model_search.github_details", return_value={"id": "a/b"}) as loader:
            self.assertEqual(model_search.cached_details("github", "a/b")["id"], "a/b")
            self.assertEqual(model_search.cached_details("github", "a/b")["id"], "a/b")
            loader.assert_called_once()


if __name__ == "__main__": unittest.main()
