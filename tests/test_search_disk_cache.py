import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class SearchDiskCacheTests(unittest.TestCase):
    def test_disk_cache_is_bounded_and_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "search.json"
            with patch.object(model_search, "_SEARCH_CACHE_FILE", cache):
                model_search._save_search_disk(("github", "q", "", "", "False"), [{"id": "x"}])
                self.assertEqual(model_search._load_search_disk()["github|q|||False"]["results"][0]["id"], "x")


if __name__ == "__main__": unittest.main()
