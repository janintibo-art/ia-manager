import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTabWidget, QWidget
from src.ui.navigation import StudioShell


class StudioNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_navigation_and_programmatic_links_stay_synchronized(self):
        tabs = QTabWidget()
        for index in range(15):
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
