import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ui.tabs.tutorial_tab import GUIDE


class TutorialActionTests(unittest.TestCase):
    def test_guide_has_navigation_topics(self):
        self.assertIn("Recherche", GUIDE)
        self.assertIn("Connexions", GUIDE)
        self.assertIn("Espace de travail", GUIDE)


if __name__ == "__main__": unittest.main()
