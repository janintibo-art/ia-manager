import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class ModelExportTests(unittest.TestCase):
    def test_export_omits_readme(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.json"
            model_search.export_details(str(path), {"id": "a/b", "license": "MIT", "readme": "secret text"})
            data = json.loads(path.read_text())
            self.assertEqual(data["id"], "a/b")
            self.assertNotIn("readme", data)


if __name__ == "__main__": unittest.main()
