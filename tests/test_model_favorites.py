import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_favorites


class FavoriteTests(unittest.TestCase):
    def test_toggle_adds_and_removes(self):
        state = {"model_favorites": []}
        with patch("src.backend.settings.get", side_effect=lambda key: state.get(key)), patch(
                "src.backend.settings.set", side_effect=lambda key, value: state.__setitem__(key, value)):
            self.assertTrue(model_favorites.toggle("github", "a/b", "b"))
            self.assertTrue(model_favorites.is_favorite("github", "a/b"))
            self.assertFalse(model_favorites.toggle("github", "a/b"))
            self.assertFalse(model_favorites.is_favorite("github", "a/b"))


if __name__ == "__main__": unittest.main()
