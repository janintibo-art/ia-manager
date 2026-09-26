import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import download_history


class DownloadHistoryTests(unittest.TestCase):
    def test_record_and_cleanup_preserves_referenced_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "models"
            history = root / "download_history.json"
            cached = root / "downloads" / "model.gguf"
            temp = root / "downloads" / "broken.part"
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b"ok"); temp.write_bytes(b"partial")
            with patch.object(download_history, "ROOT", root), patch.object(download_history, "HISTORY", history):
                download_history.record("model", "GitHub", str(cached), 2)
                self.assertEqual(download_history.cleanup_cache(), 1)
                self.assertTrue(cached.exists())
                self.assertFalse(temp.exists())


if __name__ == "__main__": unittest.main()
