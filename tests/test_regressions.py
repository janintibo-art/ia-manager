"""Régressions ciblées : données, confinement des fichiers et processus Qt."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROFILE = tempfile.TemporaryDirectory(prefix="ia_manager_regression_")
os.environ["HOME"] = PROFILE.name
os.environ["USERPROFILE"] = PROFILE.name
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from src.backend import code_tools, settings, obliteratus as ob
from src.backend.project_manager import ProjectManager
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QProcess, QThread, pyqtSignal
from src.ui.tabs.obliteratus_tab import ObliteratusTab
from src.ui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])


def wait_until(predicate, timeout=6):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        APP.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Délai dépassé")


class RegressionTests(unittest.TestCase):
    def test_conversations_unique_and_update(self):
        with tempfile.TemporaryDirectory() as d:
            pm = ProjectManager(d)
            pid = pm.create_project("Test")
            ids = [pm.save_conversation(pid, {"title": str(i)}) for i in range(25)]
            self.assertEqual(len(set(ids)), 25)
            self.assertEqual(len(pm.list_conversations(pid)), 25)
            pm.save_conversation(pid, {"id": ids[0], "title": "modifié"})
            self.assertEqual(len(pm.list_conversations(pid)), 25)
            self.assertEqual(pm.load_conversation(pid, ids[0])["title"], "modifié")

    def test_settings_concurrent_and_failed_replace(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda n: settings.set(f"regression_{n}", n), range(30)))
        self.assertTrue(all(settings.get(f"regression_{n}") == n for n in range(30)))
        before = settings.SETTINGS_FILE.read_bytes()
        with patch("src.backend.settings.os.replace", side_effect=OSError("disque indisponible")):
            with self.assertRaises(OSError):
                settings.set("new", "value")
        self.assertEqual(settings.SETTINGS_FILE.read_bytes(), before)
        self.assertFalse(list(settings.CONFIG_DIR.glob("settings_*.tmp")))

    def test_generated_files_stay_in_project(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            root.mkdir()
            def block(name):
                return {"filename": name, "code": "contenu", "lang": "text"}
            for name in ("../outside.txt", ".git/config", "C:/outside.txt", "/outside.txt"):
                with self.assertRaises(OSError):
                    code_tools.write_to_folder([block("first.txt"), block(name)], str(root))
                self.assertFalse((root / "first.txt").exists())
            outside = Path(d) / "outside"
            outside.mkdir()
            try:
                (root / "linked").symlink_to(outside, target_is_directory=True)
            except OSError:
                pass  # Windows sans le droit de créer un lien symbolique
            else:
                with self.assertRaises(OSError):
                    code_tools.write_to_folder([block("linked/leak.txt")], str(root))
                self.assertFalse((outside / "leak.txt").exists())
            code_tools.write_to_folder([block("src/test.py")], str(root))
            self.assertEqual((root / "src/test.py").read_text(), "contenu\n")

    def test_obliteratus_commands_and_process_lifecycle(self):
        self.assertEqual(ob.install_steps(sys.executable)[0][0], sys.executable)
        program, args = ob.launch_command(7861)
        self.assertIn("127.0.0.1", args)
        self.assertNotIn("--share", args)
        with self.assertRaises(ValueError):
            ob.launch_command(80)
        tab = ObliteratusTab()
        tab.run_steps([(sys.executable, ["-c", "print('premiere etape')"]),
                       (sys.executable, ["-c", "import os; print(os.environ['OBLITERATUS_TELEMETRY'])"])], "install")
        wait_until(lambda: not tab.mode)
        self.assertIn("Installation terminée", tab.status.text())
        self.assertIn("premiere etape", tab.log.toPlainText())
        self.assertIn("0", tab.log.toPlainText())
        tab.run_steps([(sys.executable, ["-c", "raise SystemExit(7)"]),
                       (sys.executable, ["-c", "print('NE DOIT PAS TOURNER')"])], "install")
        wait_until(lambda: not tab.mode)
        self.assertIn("Échec", tab.status.text())
        self.assertNotIn("NE DOIT PAS", tab.log.toPlainText())
        tab.run_steps([(sys.executable, ["-c", "import time; time.sleep(60)"])], "server")
        wait_until(lambda: tab.process.state() == QProcess.ProcessState.Running)
        tab.stop_process()
        wait_until(lambda: not tab.mode)
        self.assertIn("Arrêt demandé", tab.status.text())
        tab.run_steps([(str(Path(PROFILE.name) / "inexistant"), [])], "server")
        wait_until(lambda: not tab.mode)
        self.assertIn("Démarrage impossible", tab.status.text())
        tab.shutdown()

    def test_scheduler_waits_for_worker_finished(self):
        # Utiliser les vraies méthodes de la fenêtre sans lancer tous ses onglets réseau.
        class SlowWorker(QThread):
            answered = pyqtSignal(str)
            def __init__(self, *args):
                super().__init__()
            def run(self):
                self.answered.emit("réponse")
                self.msleep(120)  # answered AVANT finished : reproduction du défaut

        class Harness:
            run_task = MainWindow.run_task
            start_next_task = MainWindow.start_next_task
            on_task_finished = MainWindow.on_task_finished
            def __init__(self):
                self.task_queue = []
                self.running = set()
                self.task_worker = None
                self.current_task = None
                self.answers = []
            def on_task_answer(self, answer):
                self.answers.append(self.current_task["id"])
                self.running.discard(self.current_task["id"])
                self.current_task = None

        h = Harness()
        with patch("src.ui.main_window.ChatWorker", SlowWorker):
            h.run_task({"id": "a", "model": "test", "prompt": "a"})
            h.run_task({"id": "b", "model": "test", "prompt": "b"})
            wait_until(lambda: h.task_worker is None and not h.task_queue)
        self.assertEqual(h.answers, ["a", "b"])
        self.assertFalse(h.running)


if __name__ == "__main__":
    unittest.main()
