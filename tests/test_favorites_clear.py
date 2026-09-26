import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_favorites


class FavoritesClearTests(unittest.TestCase):
    def test_clear_returns_count(self):
        state = {"model_favorites": [{"source": "github", "id": "a/b"}, {"source": "civitai", "id": "1"}]}
        with patch("src.backend.settings.get", side_effect=lambda key: state.get(key)), patch(
                "src.backend.settings.set", side_effect=lambda key, value: state.__setitem__(key, value)):
            self.assertEqual(model_favorites.clear(), 2)
            self.assertEqual(state["model_favorites"], [])


if __name__ == "__main__": unittest.main()
