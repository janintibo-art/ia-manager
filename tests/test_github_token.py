import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import model_search


class GithubTokenTests(unittest.TestCase):
    def test_token_is_sent_without_exposing_value_in_diagnostic(self):
        with patch("src.backend.settings.get", return_value="ghp_PRIVATE"):
            headers = model_search.github_headers()
        self.assertEqual(headers["Authorization"], "Bearer ghp_PRIVATE")
        from src.backend import diagnostics
        with patch("src.backend.settings.get", side_effect=lambda key: "ghp_PRIVATE" if key == "github_token" else None):
            self.assertNotIn("ghp_PRIVATE", str(diagnostics.snapshot()))


if __name__ == "__main__": unittest.main()
