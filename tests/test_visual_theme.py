import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ui import style


class VisualThemeTests(unittest.TestCase):
    def test_theme_contains_brand_and_cards(self):
        sheet = style.build_stylesheet()
        self.assertIn("QFrame#Hero", sheet)
        self.assertIn("QLabel#Brand", sheet)
        self.assertIn("QFrame#Card", sheet)


if __name__ == "__main__": unittest.main()
