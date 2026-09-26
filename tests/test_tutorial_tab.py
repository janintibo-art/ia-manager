import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ui.tabs.tutorial_tab import GUIDE


class TutorialTests(unittest.TestCase):
    def test_guide_contains_core_topics(self):
        for topic in ("Ollama", "Hugging Face", "Civitai", "mode hors ligne", "Architecte Code"):
            self.assertIn(topic, GUIDE)


if __name__ == "__main__": unittest.main()
