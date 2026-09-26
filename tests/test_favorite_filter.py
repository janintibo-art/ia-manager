import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_favorites


class FavoriteFilterTests(unittest.TestCase):
    def test_favorites_are_source_specific(self):
        state = {"model_favorites": [{"source": "github", "id": "a/model"}]}
        with patch("src.backend.settings.get", side_effect=lambda key: state.get(key)):
            self.assertTrue(model_favorites.is_favorite("github", "a/model"))
            self.assertFalse(model_favorites.is_favorite("civitai", "a/model"))


if __name__ == "__main__": unittest.main()
