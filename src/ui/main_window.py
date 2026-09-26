"""Interface principale - PyQt6"""

from typing import Dict, List, Optional, Set

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QStyle, QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
)

from src.backend import code_tools, settings
from src.backend import tasks as tk
from src.ui.tabs.chat_tab import ChatTab
from src.ui.tabs.connections_tab import ConnectionsTab
from src.ui.tabs.github_tab import GithubTab
from src.ui.tabs.models_tab import ModelsTab
from src.ui.tabs.projects_tab import ProjectsTab, get_project_manager
from src.ui.tabs.setup_tab import SetupTab
from src.ui.tabs.tasks_tab import TasksTab
from src.ui.workers import ChatWorker

SCHEDULER_INTERVAL_MS = 30_000


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IA Manager — Gestionnaire d'IA locales")
        self.resize(1360, 900)
        self.setMinimumSize(1080, 720)
        self.really_quit = False
        self.tray_hint_shown = False

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.setup_tab = SetupTab()
        self.models_tab = ModelsTab()
        self.projects_tab = ProjectsTab()
        self.chat_tab = ChatTab()
        self.tasks_tab = TasksTab()
        self.connections_tab = ConnectionsTab()
        self.github_tab = GithubTab()

        self.tabs.addTab(self.setup_tab, "⚙️ Analyse")
        self.tabs.addTab(self.models_tab, "📦 Modèles")
        self.tabs.addTab(self.projects_tab, "📁 Projets")
        self.tabs.addTab(self.chat_tab, "💬 Chat")
        self.tabs.addTab(self.tasks_tab, "⏰ Tâches")
        self.tabs.addTab(self.connections_tab, "🔌 Connexions")
        self.tabs.addTab(self.github_tab, "🐙 GitHub")

        # Modèles installés ou supprimés : tous les onglets se mettent à jour
        self.setup_tab.models_changed.connect(self.on_models_changed)
        self.models_tab.models_changed.connect(self.on_models_changed)
        self.connections_tab.models_changed.connect(self.on_models_changed)
        self.connections_tab.providers_changed.connect(self.on_models_changed)
        self.setup_tab.analysis_done.connect(self.models_tab.set_system_info)
        self.setup_tab.show_model.connect(self.open_model)

        # Projets <-> Chat
        self.projects_tab.open_conversation.connect(self.open_conversation)
        self.projects_tab.new_conversation.connect(self.new_conversation)
        self.projects_tab.projects_changed.connect(self.on_projects_changed)
        self.chat_tab.conversation_saved.connect(self.projects_tab.on_conversation_saved)

        # Tâches planifiées
        self.tasks_tab.run_now.connect(self.run_task)
        self.task_queue: List[Dict] = []
        self.running: Set[str] = set()
        self.task_worker: Optional[ChatWorker] = None
        self.current_task: Optional[Dict] = None
        self.scheduler = QTimer(self)
        self.scheduler.timeout.connect(self.check_tasks)
        self.scheduler.start(SCHEDULER_INTERVAL_MS)
        QTimer.singleShot(5000, self.check_tasks)

        self.tray: Optional[QSystemTrayIcon] = None
        self.setup_tray()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

    # ------------------------------------------------------------ liens entre onglets
    def on_models_changed(self):
        self.models_tab.refresh_installed_models()
        self.chat_tab.refresh_models()
        self.setup_tab.refresh_installed()
        self.projects_tab.refresh_models()
        self.tasks_tab.refresh_models()

    def on_projects_changed(self):
        self.chat_tab.refresh_projects()
        self.chat_tab.show_hint()
        self.github_tab.refresh_projects()
        self.tasks_tab.refresh_projects()

    def open_model(self, model_id: str):
        self.models_tab.select_model(model_id)
        self.tabs.setCurrentWidget(self.models_tab)

    def open_conversation(self, pid: str, cid: str):
        self.chat_tab.load_conversation(pid, cid)
        self.tabs.setCurrentWidget(self.chat_tab)

    def new_conversation(self, pid: str):
        self.chat_tab.new_conversation_in(pid)
        self.tabs.setCurrentWidget(self.chat_tab)

    # ------------------------------------------------------------ zone de notification
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("IA Manager")
        menu = QMenu()
        open_action = QAction("Ouvrir IA Manager", self)
        open_action.triggered.connect(self.show_window)
        menu.addAction(open_action)
        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray_menu = menu
        self.tray.activated.connect(
            lambda reason: self.show_window() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self.really_quit = True
        self.close()
        QApplication.quit()

    def notify(self, title: str, text: str):
        if self.tray:
            self.tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 8000)

    def closeEvent(self, event):
        has_tasks = any(t.get("enabled") for t in tk.TaskStore().load())
        if self.tray and has_tasks and not self.really_quit:
            event.ignore()
            self.hide()
            if not self.tray_hint_shown:
                self.notify("IA Manager reste actif",
                            "Vos tâches planifiées continuent. Clic droit sur l'icône pour quitter.")
                self.tray_hint_shown = True
            return
        if self.tray:
            self.tray.hide()
        event.accept()
        QApplication.quit()

    # ------------------------------------------------------------ planificateur
    def check_tasks(self):
        for t in tk.TaskStore().due_tasks():
            self.run_task(t)

    def run_task(self, task: Dict):
        if task["id"] in self.running or any(q["id"] == task["id"] for q in self.task_queue):
            return
        self.task_queue.append(task)
        self.start_next_task()

    def start_next_task(self):
        if self.task_worker is not None and self.task_worker.isRunning():
            return
        if not self.task_queue:
            return
        task = self.task_queue.pop(0)
        self.current_task = task
        self.running.add(task["id"])
        system = ""
        if task.get("project"):
            system = get_project_manager().get_instructions(task["project"])
        if task.get("make_zip"):
            system = (system + "\n\n" + code_tools.CODE_MODE_INSTRUCTIONS).strip()
        self.task_worker = ChatWorker(task["model"], [{"role": "user", "content": task["prompt"]}], system)
        self.task_worker.answered.connect(self.on_task_answer)
        self.task_worker.start()

    def on_task_answer(self, answer: str):
        task = self.current_task or {}
        tid = task.get("id", "")
        if answer.startswith(("Erreur", "Ollama n'est pas lancé")):
            status = "❌ " + answer[:120]
        else:
            try:
                out = tk.save_result(task, answer, settings.get("projects_dir"))
                status = "✅ OK" + (" · zip créé" if "zip" in out else "")
                if out.get("project"):
                    self.projects_tab.on_conversation_saved(out["project"])
            except Exception as e:
                status = f"❌ Enregistrement impossible : {e}"
        tk.TaskStore().mark_done(tid, status)
        self.running.discard(tid)
        self.current_task = None
        self.tasks_tab.on_task_finished(tid, status)
        self.notify(f"Tâche « {task.get('name', '')} »", status)
        self.start_next_task()
