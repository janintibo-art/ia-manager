import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class SearchCacheTests(unittest.TestCase):
    def test_search_reuses_result(self):
        model_search.clear_search_cache()
        with patch("src.backend.model_search.search_github", return_value=[{"id": "a/b"}]) as search:
            self.assertEqual(model_search.search_source("github", "q")[0]["id"], "a/b")
            model_search.search_source("github", "q")
            search.assert_called_once()


if __name__ == "__main__": unittest.main()
