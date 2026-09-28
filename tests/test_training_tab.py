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

    def test_hardware_update_preserves_user_choice(self):
        tab = TrainingTab()
        info = dict(cpu='i9', gpu_type='RTX', gpu_vendor='NVIDIA', vram_exact=True,
                    vram_gb=12, ram_gb=32, ram_available_gb=24)
        tab.set_system_info(info)
        self.assertEqual(tab.model.text(), 'Qwen/Qwen2.5-3B-Instruct')
        tab.model.setText('my/custom-model')
        tab.mark_model_edited()
        info.update(vram_gb=48, ram_gb=64)
        tab.set_system_info(info)
        self.assertEqual(tab.model.text(), 'my/custom-model')
        self.assertIn('14B', tab.apply_recommended.text())
        tab.apply_recommendation()
        self.assertEqual(tab.model.text(), 'Qwen/Qwen2.5-14B-Instruct')
        self.assertEqual(tab.tuning()['context'], 2048)
        tab.deleteLater()
