import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import tempfile
import unittest
from pathlib import Path
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication
from src.ui.tabs.training_tab import TrainingTab
from src.backend import local_jobs


class TrainingTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_process(self, program, args):
        with tempfile.TemporaryDirectory() as tmp:
            tab = TrainingTab()
            tab.start_process(program, args, Path(tmp))
            loop = QEventLoop()
            timer = QTimer()
            timer.timeout.connect(lambda: loop.quit() if tab.process is None else None)
            timer.start(10)
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            timer.stop()
            try:
                self.assertIsNone(tab.process)
                self.assertFalse(local_jobs.state()['active'])
                return tab.status.text(), tab.log.toPlainText()
            finally:
                tab.shutdown()
                tab.deleteLater()

    def test_real_subprocess_success(self):
        status, log = self.run_process(sys.executable, ['-u', '-c', 'print("result-ok")'])
        self.assertEqual(status, 'Terminé.')
        self.assertIn('result-ok', log)

    def test_missing_interpreter_releases_queue(self):
        status, _ = self.run_process('/nonexistent-ia-training-python', [])
        self.assertIn('échec', status)
