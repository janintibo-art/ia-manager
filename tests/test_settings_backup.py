import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import settings_backup


class SettingsBackupTests(unittest.TestCase):
    def test_export_redacts_secrets(self):
        with patch("src.backend.settings.load", return_value={"theme": "sombre", "api_key": "secret",
                                                               "providers": [{"id": "x", "api_key": "hidden"}]}):
            data = settings_backup.snapshot()
        text = json.dumps(data)
        self.assertNotIn("hidden", text)
        self.assertNotIn("secret", text)

    def test_import_rejects_unknown_format(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"format": 999, "settings": {}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                settings_backup.import_file(str(path))


if __name__ == "__main__":
    unittest.main()
