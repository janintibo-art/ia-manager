"""Interface principale - PyQt6"""

from typing import Dict, List, Optional, Set

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QMainWindow, QMenu, QPushButton, QStyle, QSystemTrayIcon, QTabWidget,
    QVBoxLayout, QWidget, QLabel,
)

from src.backend import code_tools, settings
from src.ui import style
from src.ui.branding import asset
from src.ui.navigation import StudioShell
from src.backend import tasks as tk
from src.ui.tabs.bench_tab import BenchTab
from src.ui.tabs.chat_tab import ChatTab
from src.ui.tabs.comparator_tab import ComparatorTab
from src.ui.tabs.connections_tab import ConnectionsTab
from src.ui.tabs.dashboard_tab import DashboardTab
from src.ui.tabs.github_tab import GithubTab
from src.ui.tabs.models_tab import ModelsTab
from src.ui.tabs.obliteratus_tab import ObliteratusTab
from src.ui.tabs.projects_tab import ProjectsTab, get_project_manager
from src.ui.tabs.search_tab import SearchTab
from src.ui.tabs.setup_tab import SetupTab
from src.ui.tabs.tasks_tab import TasksTab
from src.ui.tabs.workspace_tab import WorkspaceTab
from src.ui.tabs.tutorial_tab import TutorialTab
from src.ui.tabs.mobile_tab import MobileTab
from src.ui.tabs.training_tab import TrainingTab
from src.ui.tabs.image_studio_tab import ImageStudioTab
from src.ui.tabs.media_studio_tab import MediaStudioTab
from src.ui.tabs.creative_tools_tab import CreativeToolsTab
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
        self.search_tab = SearchTab()
        self.projects_tab = ProjectsTab()
        self.chat_tab = ChatTab()
        self.tasks_tab = TasksTab()
        self.connections_tab = ConnectionsTab()
        self.github_tab = GithubTab()
        self.dashboard_tab = DashboardTab()
        self.comparator_tab = ComparatorTab()
        self.bench_tab = BenchTab()
        self.obliteratus_tab = ObliteratusTab()
        self.workspace_tab = WorkspaceTab()
        self.tutorial_tab = TutorialTab()
        self.mobile_tab = MobileTab()
        self.training_tab = TrainingTab()
        self.image_studio_tab = ImageStudioTab()
        self.media_studio_tab = MediaStudioTab()
        self.creative_tools_tab = CreativeToolsTab()
        self.image_studio_tab.open_tools.connect(lambda: self.tabs.setCurrentWidget(self.creative_tools_tab))
        self.media_studio_tab.open_tools.connect(lambda: self.tabs.setCurrentWidget(self.creative_tools_tab))
        self.creative_tools_tab.engine_started.connect(self.connect_creative_engine)
        self.training_tab.models_changed.connect(self.on_models_changed)
        self.tutorial_tab.open_tab.connect(self.open_named_tab)
        self.workspace_tab.apply_profile.connect(self.apply_work_profile)
        self.workspace_tab.trials.compare_models.connect(self.compare_trial_models)
        self.workspace_tab.set_models([self.chat_tab.model_select.itemData(i) for i in range(self.chat_tab.model_select.count())])

        self.tabs.addTab(self.setup_tab, "⚙️ Analyse")
        self.tabs.addTab(self.models_tab, "📦 Modèles")
        self.tabs.addTab(self.search_tab, "🔍 Recherche")
        self.tabs.addTab(self.projects_tab, "📁 Projets")
        self.tabs.addTab(self.chat_tab, "💬 Chat")
        self.tabs.addTab(self.comparator_tab, "⚖️ Comparateur")
        self.tabs.addTab(self.dashboard_tab, "📊 Tableau de bord")
        self.tabs.addTab(self.bench_tab, "🏁 Test de vitesse")
        self.tabs.addTab(self.tasks_tab, "⏰ Tâches")
        self.tabs.addTab(self.connections_tab, "🔌 Connexions")
        self.tabs.addTab(self.github_tab, "🐙 GitHub")
        self.tabs.addTab(self.obliteratus_tab, "🧪 Obliteratus")
        self.tabs.addTab(self.workspace_tab, "📚 Espace de travail")
        self.tabs.addTab(self.tutorial_tab, "📘 Tuto")
        self.tabs.addTab(self.mobile_tab, "📱 Téléphone")
        self.tabs.addTab(self.training_tab, "🧬 Entraîner / Fusionner")
        self.tabs.addTab(self.image_studio_tab, "🎨 Création d’images")
        self.tabs.addTab(self.media_studio_tab, "🎵 Audio · Vidéo · 3D")
        self.tabs.addTab(self.creative_tools_tab, "🛠️ Outils locaux")

        # Modèles installés ou supprimés : tous les onglets se mettent à jour
        self.setup_tab.models_changed.connect(self.on_models_changed)
        self.setup_tab.open_section.connect(self.open_named_tab)
        self.models_tab.models_changed.connect(self.on_models_changed)
        self.connections_tab.models_changed.connect(self.on_models_changed)
        self.connections_tab.providers_changed.connect(self.on_models_changed)
        self.setup_tab.analysis_done.connect(self.models_tab.set_system_info)
        self.setup_tab.analysis_done.connect(self.search_tab.set_system_info)
        self.setup_tab.analysis_done.connect(self.chat_tab.set_system_info)
        self.setup_tab.analysis_done.connect(self.bench_tab.set_system_info)
        self.setup_tab.analysis_done.connect(self.training_tab.set_system_info)
        self.training_tab.analyze_requested.connect(self.setup_tab.analyze_system)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.search_tab.models_changed.connect(self.on_models_changed)
        self.dashboard_tab.models_changed.connect(self.on_models_changed)
        self.setup_tab.show_model.connect(self.open_model)
        self.obliteratus_tab.open_model_chat.connect(self.open_obliteratus_chat)

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
        self.studio_shell = StudioShell(self.tabs, self.build_appearance_buttons())
        self.setCentralWidget(self.studio_shell)

    # ------------------------------------------------------------ liens entre onglets
    def connect_creative_engine(self, key, url):
        if key == 'comfyui':
            self.image_studio_tab.url.setText(url)
            settings.set('image_comfy_url', url)
        model_ids = {'comfyui': ('wan21', 'ltx-video'),
                     'audiocraft': ('musicgen-small', 'musicgen-melody', 'audiogen'),
                     'triposr': ('triposr',), 'hunyuan3d': ('hunyuan3d',)}.get(key, ())
        panel = self.media_studio_tab
        for model_id in model_ids:
            record = panel.profiles.get(model_id)
            record = dict(record) if isinstance(record, dict) else {}
            record['url'] = url
            panel.profiles[model_id] = record
        if panel.current_model and panel.current_model['id'] in model_ids:
            panel.address.setText(url)
        panel.flush()

    def on_models_changed(self):
        self.models_tab.refresh_installed_models()
        self.chat_tab.refresh_models()
        self.setup_tab.refresh_installed()
        self.projects_tab.refresh_models()
        self.tasks_tab.refresh_models()
        self.comparator_tab.refresh_models()
        self.workspace_tab.set_models([self.chat_tab.model_select.itemData(i) for i in range(self.chat_tab.model_select.count())])

    def open_named_tab(self, name: str):
        tabs = {"search": self.search_tab, "connections": self.connections_tab,
                "chat": self.chat_tab, "workspace": self.workspace_tab,
                "github": self.github_tab}
        target = tabs.get(name)
        if target is not None:
            self.tabs.setCurrentWidget(target)

    def on_tab_changed(self, _index: int):
        # Le test de vitesse lit le matériel et les modèles à la première ouverture de l'onglet
        if self.tabs.currentWidget() is self.bench_tab and self.bench_tab.hw is None:
            self.bench_tab.scan()

    def on_projects_changed(self):
        self.workspace_tab.refresh_projects()
        self.chat_tab.refresh_projects()
        self.chat_tab.show_hint()
        self.github_tab.refresh_projects()
        self.tasks_tab.refresh_projects()

    def open_model(self, model_id: str):
        self.models_tab.select_model(model_id)
        self.tabs.setCurrentWidget(self.models_tab)

    def open_obliteratus_chat(self, name: str):
        self.chat_tab.refresh_models()
        if self.chat_tab.select_ref(name):
            self.tabs.setCurrentWidget(self.chat_tab)
        else:
            self.obliteratus_tab.status.setText(
                "Modèle « " + name + " » absent d'Ollama. Vérifiez que l'import est terminé et qu'Ollama est lancé.")

    def open_conversation(self, pid: str, cid: str):
        self.chat_tab.load_conversation(pid, cid)
        self.tabs.setCurrentWidget(self.chat_tab)

    def new_conversation(self, pid: str):
        self.chat_tab.new_conversation_in(pid)
        self.tabs.setCurrentWidget(self.chat_tab)

    def compare_trial_models(self, source, result):
        comp = self.comparator_tab
        comp.refresh_models()
        indices = [comp.columns[0].combo.findData(source), comp.columns[1].combo.findData(result)]
        if not source or not result or min(indices) < 0:
            self.workspace_tab.trials.status.setText("Les deux références doivent être disponibles dans Connexions ou Ollama.")
            return
        if any(column.busy() for column in comp.columns):
            self.workspace_tab.trials.status.setText("Arrêtez la comparaison en cours avant d’en préparer une autre.")
            return
        for column, index in zip(comp.columns, indices):
            column.combo.setCurrentIndex(index)
        comp.columns[2].combo.setCurrentIndex(0)
        self.tabs.setCurrentWidget(comp)

    def apply_work_profile(self, profile):
        from src.backend import model_options
        chat = self.chat_tab
        if (chat.worker is not None and chat.worker.isRunning()) or (chat.web_worker is not None and chat.web_worker.isRunning()):
            self.workspace_tab.profile_status.setText("Arrêtez la génération ou attendez la recherche avant de changer de profil.")
            return
        ref = profile.get("model") or chat.current_ref()
        if not ref or not chat.select_ref(ref):
            self.workspace_tab.profile_status.setText("Choisissez un modèle disponible avant d’appliquer ce profil.")
            return
        chat.profile_instructions = profile.get("instructions", "")
        chat.profile_label.setText("Profil : " + profile.get("name", "personnalisé"))
        chat.web_mode.setChecked(profile.get("web", False))
        chat.code_mode.setChecked(profile.get("code", False))
        model_options.set_options(ref, {"mode": profile.get("mode", "balanced"),
            "num_ctx": profile.get("num_ctx",8192),"temperature":profile.get("temperature",.7),"gpu_layers":-1})
        self.tabs.setCurrentWidget(chat)

    # ------------------------------------------------------------ apparence
    def build_appearance_buttons(self) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(4)
        for text, tip, slot in (("A−", "Texte plus petit", lambda: self.change_appearance(delta=-1)),
                                ("A+", "Texte plus grand", lambda: self.change_appearance(delta=1)),
                                ("🌓", "Thème clair / sombre", lambda: self.change_appearance(toggle=True))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setStyleSheet("padding: 4px 10px;")
            b.clicked.connect(slot)
            lay.addWidget(b)
        return box

    def change_appearance(self, delta: int = 0, toggle: bool = False):
        theme = style.CURRENT_THEME
        if toggle:
            theme = "clair" if theme == "sombre" else "sombre"
        size = max(10, min(20, style.BASE_FONT_PT + delta))
        style.apply_theme(theme, size)
        settings.set("theme", theme)
        settings.set("font_size", size)
        app = QApplication.instance()
        app.setFont(QFont("Segoe UI", style.BASE_FONT_PT))
        app.setStyleSheet(style.build_stylesheet())
        self.studio_shell.update_brand()
        if toggle:
            self.chat_tab.status.setText("🌓 Thème changé : les nouveaux messages utilisent les nouvelles couleurs.")

    # ------------------------------------------------------------ zone de notification
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon(str(asset("ia_manager_icon.png")))
        if icon.isNull():
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
        self.creative_tools_tab.shutdown()
        self.media_studio_tab.shutdown()
        self.training_tab.shutdown()
        self.mobile_tab.shutdown()
        self.obliteratus_tab.shutdown()
        self.chat_tab.cancel_attachments()
        self.workspace_tab.cancel_import()
        if self.task_worker is not None:
            self.task_worker.stop()
        from src.ui.workers import SafeThread, StreamWorker, ChatWorker
        for worker in list(SafeThread._alive):
            if isinstance(worker, (StreamWorker, ChatWorker)):
                worker.stop()
        for worker in list(SafeThread._alive):
            if isinstance(worker, (StreamWorker, ChatWorker)):
                worker.wait(1000)
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
        if self.task_worker is not None:
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
        self.task_worker.finished.connect(self.on_task_finished)
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

    def on_task_finished(self):
        # answered peut arriver avant la fin réelle du QThread.
        self.task_worker = None
        self.start_next_task()
