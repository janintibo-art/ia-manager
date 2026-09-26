"""Onglet Tâches - planifier des consignes envoyées automatiquement à une IA"""

from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtCore import QDateTime, Qt, QTime, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter, QTextEdit,
    QTimeEdit, QVBoxLayout, QWidget,
)

from src.backend import providers
from src.backend import tasks as tk
from src.backend.ai_manager import AIManager
from src.ui.tabs.projects_tab import get_project_manager


def fmt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m %H:%M")
    except (TypeError, ValueError):
        return "—"


class TasksTab(QWidget):
    """Liste des tâches, éditeur, résultats récents"""

    run_now = pyqtSignal(dict)
    tasks_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.store = tk.TaskStore()
        self.ai_manager = AIManager()
        self.current: Optional[Dict] = None
        self.init_ui()
        self.refresh_models()
        self.refresh_projects()
        self.reload()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("Tâches planifiées")
        title.setObjectName("Title")
        root.addWidget(title)
        sub = QLabel("Une tâche envoie une consigne à une IA à l'heure choisie (résumé du jour, script à "
                     "générer, veille…). Les tâches tournent tant qu'IA Manager est ouvert : en fermant la "
                     "fenêtre, il reste actif dans la zone de notification près de l'horloge.")
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.task_list = QListWidget()
        self.task_list.currentItemChanged.connect(self.on_task_selected)
        ll.addWidget(self.task_list, 2)
        btns = QHBoxLayout()
        new_btn = QPushButton("➕ Nouvelle tâche")
        new_btn.setObjectName("Primary")
        new_btn.clicked.connect(self.new_task)
        btns.addWidget(new_btn, 1)
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self.delete_task)
        btns.addWidget(del_btn)
        ll.addLayout(btns)

        res_title = QLabel("📄 Résultats récents (double-clic pour ouvrir)")
        res_title.setObjectName("Muted")
        ll.addWidget(res_title)
        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(
            lambda it: QDesktopServices.openUrl(QUrl.fromLocalFile(it.data(Qt.ItemDataRole.UserRole))))
        ll.addWidget(self.results, 1)
        open_res = QPushButton("📂 Dossier des résultats")
        open_res.clicked.connect(self.open_results_folder)
        ll.addWidget(open_res)
        splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("Card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 16, 18, 16)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.name_edit = QLineEdit()
        form.addRow("Nom :", self.name_edit)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setPlaceholderText("Ce que l'IA doit faire. Ex. : « Écris un script Python qui "
                                            "sauvegarde mon dossier Documents dans un zip daté. »")
        self.prompt_edit.setMinimumHeight(130)
        form.addRow("Consigne :", self.prompt_edit)
        self.model_combo = QComboBox()
        form.addRow("IA :", self.model_combo)
        self.project_combo = QComboBox()
        form.addRow("Projet :", self.project_combo)

        self.schedule_combo = QComboBox()
        for key, label in tk.SCHEDULES.items():
            self.schedule_combo.addItem(label, key)
        self.schedule_combo.currentIndexChanged.connect(self.update_schedule_fields)
        form.addRow("Fréquence :", self.schedule_combo)

        when = QHBoxLayout()
        self.at_edit = QDateTimeEdit()
        self.at_edit.setCalendarPopup(True)
        self.at_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        when.addWidget(self.at_edit)
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(tk.DAYS)
        when.addWidget(self.weekday_combo)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        when.addWidget(self.time_edit)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 999)
        when.addWidget(self.interval_spin)
        self.interval_unit = QLabel()
        when.addWidget(self.interval_unit)
        when.addStretch()
        form.addRow("Quand :", when)

        self.enabled_check = QCheckBox("Tâche activée")
        form.addRow("", self.enabled_check)
        self.zip_check = QCheckBox("📦 Si la réponse contient du code, créer un zip")
        form.addRow("", self.zip_check)
        rl.addLayout(form)

        self.info = QLabel()
        self.info.setObjectName("Muted")
        self.info.setWordWrap(True)
        rl.addWidget(self.info)
        rl.addStretch()

        actions = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        actions.addWidget(self.status, 1)
        run_btn = QPushButton("▶ Lancer maintenant")
        run_btn.clicked.connect(self.run_current)
        actions.addWidget(run_btn)
        save_btn = QPushButton("💾 Enregistrer")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.save_current)
        actions.addWidget(save_btn)
        rl.addLayout(actions)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([440, 760])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------ données
    def refresh_models(self):
        current = self.model_combo.currentData()
        self.model_combo.clear()
        for label, ref in providers.all_model_choices(self.ai_manager.get_available_models()):
            self.model_combo.addItem(label, ref)
        if current:
            idx = self.model_combo.findData(current)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def refresh_projects(self):
        current = self.project_combo.currentData()
        self.project_combo.clear()
        self.project_combo.addItem("(aucun — résultat dans le dossier des tâches)", "")
        for p in get_project_manager().list_projects():
            self.project_combo.addItem(p["name"], p["id"])
        idx = self.project_combo.findData(current or "")
        self.project_combo.setCurrentIndex(max(0, idx))

    def reload(self, select: Optional[str] = None):
        keep = select or (self.current or {}).get("id")
        tasks = self.store.load()
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for t in sorted(tasks, key=lambda t: (not t.get("enabled"), t.get("next_run") or "9999")):
            icon = "🟢" if t.get("enabled") else "⚪"
            status = f" · {t['last_status']}" if t.get("last_status") else ""
            item = QListWidgetItem(f"{icon} {t['name']}\n      {tk.describe(t)} · prochaine : "
                                   f"{fmt(t.get('next_run'))}{status}")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.task_list.addItem(item)
        self.task_list.blockSignals(False)

        row = -1
        for i in range(self.task_list.count()):
            if self.task_list.item(i).data(Qt.ItemDataRole.UserRole) == keep:
                row = i
        if row < 0 and self.task_list.count():
            row = 0
        if row >= 0:
            self.task_list.setCurrentRow(row)
            self.on_task_selected(self.task_list.currentItem(), None)
        else:
            self.show_task(None)
        self.refresh_results()

    def refresh_results(self):
        self.results.clear()
        for p in tk.list_results(30):
            item = QListWidgetItem(f"{datetime.fromtimestamp(p.stat().st_mtime):%d/%m %H:%M} · {p.stem}")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.results.addItem(item)

    def on_task_selected(self, current, _prev):
        if current is None:
            return
        tid = current.data(Qt.ItemDataRole.UserRole)
        task = next((t for t in self.store.load() if t["id"] == tid), None)
        self.show_task(task)

    def show_task(self, task: Optional[Dict]):
        self.current = task
        self.setEnabled(True)
        editable = task is not None
        for w in (self.name_edit, self.prompt_edit, self.model_combo, self.project_combo,
                  self.schedule_combo, self.enabled_check, self.zip_check):
            w.setEnabled(editable)
        if not task:
            self.name_edit.clear()
            self.prompt_edit.clear()
            self.info.setText("Créez une tâche avec « ➕ Nouvelle tâche ».")
            return
        self.name_edit.setText(task["name"])
        self.prompt_edit.setPlainText(task["prompt"])
        idx = self.model_combo.findData(task["model"])
        if idx < 0 and task["model"]:
            self.model_combo.addItem(providers.label_for(task["model"]) + " (indisponible)", task["model"])
            idx = self.model_combo.count() - 1
        self.model_combo.setCurrentIndex(max(0, idx))
        self.project_combo.setCurrentIndex(max(0, self.project_combo.findData(task.get("project", ""))))
        self.schedule_combo.setCurrentIndex(max(0, self.schedule_combo.findData(task["schedule"])))
        try:
            at = datetime.fromisoformat(task["at"])
        except ValueError:
            at = datetime.now()
        self.at_edit.setDateTime(QDateTime(at.year, at.month, at.day, at.hour, at.minute))
        h, m = tk._parse_time(task.get("time", "08:00"))
        self.time_edit.setTime(QTime(h, m))
        self.weekday_combo.setCurrentIndex(int(task.get("weekday", 0)) % 7)
        self.interval_spin.setValue(int(task.get("interval", 6)))
        self.enabled_check.setChecked(bool(task.get("enabled")))
        self.zip_check.setChecked(bool(task.get("make_zip")))
        self.update_schedule_fields()
        self.info.setText(f"Prochaine exécution : {fmt(task.get('next_run'))}  ·  "
                          f"Dernière : {fmt(task.get('last_run'))} {task.get('last_status', '')}")
        self.status.setText("")

    def update_schedule_fields(self):
        kind = self.schedule_combo.currentData()
        self.at_edit.setVisible(kind == "once")
        self.weekday_combo.setVisible(kind == "weekly")
        self.time_edit.setVisible(kind in ("daily", "weekly"))
        self.interval_spin.setVisible(kind in ("hours", "minutes"))
        self.interval_unit.setVisible(kind in ("hours", "minutes"))
        self.interval_unit.setText("heure(s)" if kind == "hours" else "minutes (5 minimum)")

    def form_task(self) -> Dict:
        t = dict(self.current or tk.new_task())
        dt = self.at_edit.dateTime()
        d, tm = dt.date(), dt.time()
        t.update({
            "name": self.name_edit.text().strip() or "Tâche",
            "prompt": self.prompt_edit.toPlainText().strip(),
            "model": self.model_combo.currentData() or "",
            "project": self.project_combo.currentData() or "",
            "schedule": self.schedule_combo.currentData(),
            "at": datetime(d.year(), d.month(), d.day(), tm.hour(), tm.minute()).isoformat(),
            "time": self.time_edit.time().toString("HH:mm"),
            "weekday": self.weekday_combo.currentIndex(),
            "interval": self.interval_spin.value(),
            "enabled": self.enabled_check.isChecked(),
            "make_zip": self.zip_check.isChecked(),
        })
        return t

    # ------------------------------------------------------------ actions
    def new_task(self):
        t = tk.new_task()
        t["model"] = self.model_combo.currentData() or ""
        self.store.upsert(t)
        self.reload(select=t["id"])
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        self.tasks_changed.emit()

    def save_current(self) -> Optional[Dict]:
        if not self.current:
            return None
        t = self.form_task()
        if not t["prompt"]:
            self.status.setText("⚠️ Écrivez une consigne.")
            return None
        if not t["model"]:
            self.status.setText("⚠️ Choisissez une IA (installez un modèle ou ajoutez une connexion).")
            return None
        message = "✅ Enregistrée."
        if t["schedule"] == "once":
            t["last_run"] = ""  # replanifier une tâche unique déjà passée
            if datetime.fromisoformat(t["at"]) < datetime.now():
                message = "ℹ️ La date est passée : la tâche va s'exécuter tout de suite."
        self.store.upsert(t)
        self.reload(select=t["id"])
        self.status.setText(message)
        self.tasks_changed.emit()
        return t

    def run_current(self):
        t = self.save_current()
        if t:
            self.status.setText("⏳ Tâche lancée… le résultat apparaîtra dans « Résultats récents ».")
            self.run_now.emit(t)

    def delete_task(self):
        if not self.current:
            return
        reply = QMessageBox.question(self, "Supprimer", f"Supprimer la tâche « {self.current['name']} » ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.store.delete(self.current["id"])
            self.current = None
            self.reload()
            self.tasks_changed.emit()

    def open_results_folder(self):
        tk.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(tk.RESULTS_DIR)))

    def on_task_finished(self, task_id: str, status: str):
        self.reload(select=(self.current or {}).get("id"))
        if self.current and self.current["id"] == task_id:
            self.status.setText(status)
