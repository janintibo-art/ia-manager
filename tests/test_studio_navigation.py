import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import ast
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTabWidget, QWidget
from src.ui.navigation import StudioShell, SECTIONS


class StudioNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_navigation_and_programmatic_links_stay_synchronized(self):
        tabs = QTabWidget()
        indices = [entry[0] for _, entries in SECTIONS for entry in entries]
        self.assertEqual(len(indices), len(set(indices)))
        self.assertEqual(sorted(indices), list(range(len(indices))))
        main_file = Path(__file__).resolve().parents[1] / 'src' / 'ui' / 'main_window.py'
        tree = ast.parse(main_file.read_text(encoding='utf-8'))
        registered = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Attribute) and node.func.attr == 'addTab'
                      and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'tabs']
        self.assertEqual(len(indices), len(registered))
        for index in range(len(registered)):
            tabs.addTab(QWidget(), str(index))
        shell = StudioShell(tabs, QWidget())
        self.assertEqual(set(shell.entries), set(range(tabs.count())))
        for index, (item, title, *_) in shell.entries.items():
            shell.navigation.setCurrentItem(item)
            self.assertEqual(tabs.currentIndex(), index)
            self.assertEqual(shell.title.text(), title)
            target = (index + 1) % tabs.count()
            tabs.setCurrentWidget(tabs.widget(target))
            self.assertEqual(shell.navigation.currentItem().data(Qt.ItemDataRole.UserRole), target)
        shell.deleteLater()


if __name__ == '__main__':
    unittest.main()
