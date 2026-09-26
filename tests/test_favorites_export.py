import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_favorites


class FavoritesExportTests(unittest.TestCase):
    def test_export_and_import(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "favorites.json"
            state = {"model_favorites": [{"source": "github", "id": "a/b"}]}
            with patch("src.backend.settings.get", side_effect=lambda key: state.get(key)), patch(
                    "src.backend.settings.set", side_effect=lambda key, value: state.__setitem__(key, value)):
                model_favorites.export_file(str(path))
                self.assertEqual(json.loads(path.read_text())["favorites"][0]["id"], "a/b")
                self.assertEqual(model_favorites.import_file(str(path)), 1)


if __name__ == "__main__": unittest.main()
