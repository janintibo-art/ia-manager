"""v157 : gestionnaire central de téléchargements."""
import json
import math
import time
from datetime import datetime
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import download_history


STATE_FILE = Path.home() / ".ia_manager" / "download_center.json"


def _human_bytes(value):
    value = float(value or 0)
    units = ["o", "Ko", "Mo", "Go", "To"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.1f} {units[idx]}"


def _speed(value):
    return _human_bytes(value) + "/s" if value else "—"


def _eta(done, total, speed):
    if not total or not speed or speed <= 0 or done >= total:
        return "—"
    seconds = max(0, int((total - done) / speed))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


class DownloadTracker(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.jobs = {}
        self.workers = {}
        self.load()

    def load(self):
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if item.get("state") in ("running", "queued", "cancelling"):
                        item["state"] = "interrupted"
                    self.jobs[item["id"]] = item
        except Exception:
            pass

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(
            self.jobs.values(),
            key=lambda x: x.get("updated", ""),
            reverse=True,
        )[:200]
        STATE_FILE.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def start(self, job_id, name, source, total=0, target="", retry_kind="", retry_value="", worker=None):
        now = datetime.now().isoformat(timespec="seconds")
        self.jobs[job_id] = {
            "id": job_id,
            "name": name,
            "source": source,
            "done": 0,
            "total": int(total or 0),
            "speed": 0.0,
            "state": "running",
            "status": "Démarrage…",
            "target": target,
            "retry_kind": retry_kind,
            "retry_value": retry_value,
            "created": now,
            "updated": now,
            "_last_bytes": 0,
            "_last_time": time.monotonic(),
        }
        if worker is not None:
            self.workers[job_id] = worker
        self.save()
        self.changed.emit()

    def progress(self, job_id, done, total=0):
        job = self.jobs.get(job_id)
        if not job:
            return
        now_mono = time.monotonic()
        elapsed = now_mono - float(job.get("_last_time") or now_mono)
        old = int(job.get("_last_bytes") or 0)
        if elapsed >= 0.35 and done >= old:
            instant = (done - old) / elapsed
            previous = float(job.get("speed") or 0)
            job["speed"] = instant if not previous else previous * 0.65 + instant * 0.35
            job["_last_time"] = now_mono
            job["_last_bytes"] = int(done)
        job["done"] = int(done or 0)
        if total:
            job["total"] = int(total)
        job["updated"] = datetime.now().isoformat(timespec="seconds")
        self.changed.emit()

    def status(self, job_id, text):
        job = self.jobs.get(job_id)
        if not job:
            return
        job["status"] = str(text or "")
        job["updated"] = datetime.now().isoformat(timespec="seconds")
        self.changed.emit()

    def finish(self, job_id, ok, error=""):
        job = self.jobs.get(job_id)
        if not job:
            return
        job["state"] = "done" if ok else ("cancelled" if "annul" in str(error).lower() else "failed")
        job["status"] = "Terminé" if ok else str(error or "Échec")
        if ok and job.get("total"):
            job["done"] = job["total"]
        job["speed"] = 0
        job["updated"] = datetime.now().isoformat(timespec="seconds")
        job.pop("_last_bytes", None)
        job.pop("_last_time", None)
        self.workers.pop(job_id, None)
        self.save()
        self.changed.emit()

    def cancel(self, job_id):
        worker = self.workers.get(job_id)
        if worker is not None and hasattr(worker, "stop"):
            try:
                worker.stop()
                self.jobs[job_id]["state"] = "cancelling"
                self.jobs[job_id]["status"] = "Annulation demandée…"
                self.changed.emit()
                return True
            except Exception:
                pass
        return False

    def remove(self, job_id):
        if self.jobs.get(job_id, {}).get("state") in ("running", "cancelling"):
            return
        self.jobs.pop(job_id, None)
        self.save()
        self.changed.emit()


class DownloadCenter(QWidget):
    def __init__(self, window, tracker):
        super().__init__()
        self.window = window
        self.tracker = tracker
        self.build_ui()
        tracker.changed.connect(self.refresh)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("⬇ Centre de téléchargements")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Tous les téléchargements suivis par IA Manager au même endroit : progression, "
            "vitesse, temps restant, source et état."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        self.active_label = QLabel("0 actif")
        self.active_label.setObjectName("BigValue")
        top.addWidget(self.active_label)
        self.cache_label = QLabel("")
        self.cache_label.setObjectName("Muted")
        top.addWidget(self.cache_label)
        top.addStretch()

        search = QPushButton("🔎 Ouvrir Recherche")
        search.clicked.connect(lambda: self.open_attr("search_tab"))
        top.addWidget(search)

        clean = QPushButton("🧹 Nettoyer cache temporaire")
        clean.clicked.connect(self.clean_cache)
        top.addWidget(clean)
        root.addLayout(top)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Nom", "Source", "Progression", "Vitesse", "Reste", "État", "Destination", "Actions"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)

    def clean_cache(self):
        removed = download_history.cleanup_cache()
        self.status.setText(f"✅ Cache nettoyé : {removed} fichier(s) temporaire(s) supprimé(s).")
        self.refresh()

    def open_target(self, path):
        p = Path(path)
        target = p if p.is_dir() else p.parent
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def retry(self, job):
        kind = job.get("retry_kind")
        value = job.get("retry_value")
        search = getattr(self.window, "search_tab", None)
        if kind == "ollama" and search is not None and value:
            self.window.tabs.setCurrentWidget(search)
            search.start_download(value)
            return
        self.status.setText("Relance automatique indisponible pour ce téléchargement.")

    def refresh(self):
        jobs = sorted(
            self.tracker.jobs.values(),
            key=lambda x: x.get("updated", ""),
            reverse=True,
        )
        active = sum(1 for j in jobs if j.get("state") in ("running", "cancelling"))
        self.active_label.setText(f"{active} actif" + ("s" if active != 1 else ""))

        stats = download_history.cache_stats()
        self.cache_label.setText(
            f"Cache : {stats['files']} fichier(s) · {_human_bytes(stats['bytes'])}"
            + (f" · {stats['partial']} partiel(s)" if stats["partial"] else "")
        )

        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            self.table.setItem(row, 0, QTableWidgetItem(job.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(job.get("source", "")))

            cell = QWidget()
            lay = QVBoxLayout(cell)
            lay.setContentsMargins(3, 2, 3, 2)
            bar = QProgressBar()
            total = int(job.get("total") or 0)
            done = int(job.get("done") or 0)
            if total > 0:
                bar.setRange(0, 100)
                pct = min(100, int(done * 100 / total))
                bar.setValue(pct)
                bar.setFormat(f"{pct}% · {_human_bytes(done)} / {_human_bytes(total)}")
            else:
                if job.get("state") == "running":
                    bar.setRange(0, 0)
                else:
                    bar.setRange(0, 100)
                    bar.setValue(100 if job.get("state") == "done" else 0)
                bar.setFormat(_human_bytes(done) if done else "")
            lay.addWidget(bar)
            self.table.setCellWidget(row, 2, cell)

            self.table.setItem(row, 3, QTableWidgetItem(_speed(job.get("speed", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(_eta(done, total, job.get("speed", 0))))

            states = {
                "running": "⬇ En cours",
                "cancelling": "⏹ Arrêt…",
                "done": "✅ Terminé",
                "failed": "❌ Échec",
                "cancelled": "⏹ Annulé",
                "interrupted": "⚠️ Interrompu",
            }
            state_text = states.get(job.get("state"), job.get("state", ""))
            detail = job.get("status", "")
            self.table.setItem(row, 5, QTableWidgetItem(state_text + (f" · {detail}" if detail else "")))
            self.table.setItem(row, 6, QTableWidgetItem(job.get("target", "")))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 1, 2, 1)

            if job.get("state") in ("running", "cancelling"):
                stop = QPushButton("Arrêter")
                stop.setEnabled(job.get("state") == "running")
                stop.clicked.connect(lambda _=False, jid=job["id"]: self.tracker.cancel(jid))
                al.addWidget(stop)
            else:
                if job.get("retry_kind"):
                    retry = QPushButton("Relancer")
                    retry.clicked.connect(lambda _=False, j=dict(job): self.retry(j))
                    al.addWidget(retry)
                remove = QPushButton("Retirer")
                remove.clicked.connect(lambda _=False, jid=job["id"]: self.tracker.remove(jid))
                al.addWidget(remove)

            if job.get("target"):
                op = QPushButton("Dossier")
                op.clicked.connect(lambda _=False, p=job["target"]: self.open_target(p))
                al.addWidget(op)

            self.table.setCellWidget(row, 7, actions)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)


def _attach_worker(tracker, worker, job_id):
    if worker is None or getattr(worker, "_v157_tracked", False):
        return
    worker._v157_tracked = True
    if hasattr(worker, "progress"):
        worker.progress.connect(lambda done, total, jid=job_id: tracker.progress(jid, done, total))
    if hasattr(worker, "status"):
        worker.status.connect(lambda text, jid=job_id: tracker.status(jid, text))
    if hasattr(worker, "finished_ok"):
        worker.finished_ok.connect(
            lambda ok, err, jid=job_id: tracker.finish(jid, bool(ok), "" if ok else str(err))
        )


def _patch_search(window, tracker):
    tab = getattr(window, "search_tab", None)
    if tab is None or getattr(tab, "_v157_download_center", False):
        return

    original_start = tab.start_download
    original_github = tab.download_github
    original_civitai = tab.download_civitai

    def start_download(self, name, size_text=""):
        original_start(name, size_text)
        worker = self.dl_worker
        if worker is not None:
            jid = f"ollama:{name}:{id(worker)}"
            tracker.start(jid, name, "Ollama", retry_kind="ollama", retry_value=name, worker=worker)
            _attach_worker(tracker, worker, jid)

    def download_github(self, asset):
        original_github(asset)
        worker = self.github_file_worker
        if worker is not None:
            name = asset.get("asset", "GGUF")
            total = int(asset.get("size") or 0)
            jid = f"github:{name}:{id(worker)}"
            tracker.start(jid, name, "GitHub", total=total, worker=worker)
            _attach_worker(tracker, worker, jid)

    def download_civitai(self, asset):
        original_civitai(asset)
        worker = self.civitai_worker
        if worker is not None:
            name = asset.get("asset", "Civitai")
            total = int(asset.get("size") or 0)
            jid = f"civitai:{name}:{id(worker)}"
            tracker.start(jid, name, "Civitai", total=total, worker=worker)
            _attach_worker(tracker, worker, jid)

    tab.start_download = MethodType(start_download, tab)
    tab.download_github = MethodType(download_github, tab)
    tab.download_civitai = MethodType(download_civitai, tab)
    tab._v157_download_center = True


def _patch_setup(window, tracker):
    tab = getattr(window, "setup_tab", None)
    if tab is None or getattr(tab, "_v157_download_center", False):
        return
    original = tab.download

    def download(self, model_id):
        original(model_id)
        worker = self.download_worker
        if worker is not None:
            jid = f"setup:{model_id}:{id(worker)}"
            tracker.start(jid, model_id, "Ollama", retry_kind="ollama", retry_value=model_id, worker=worker)
            _attach_worker(tracker, worker, jid)

    tab.download = MethodType(download, tab)
    tab._v157_download_center = True


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ACCUEIL":
                if not any(attr == "download_center_tab" for attr, *_ in entries):
                    entries.append(
                        ("download_center_tab", "Téléchargements", "Suivez tous les téléchargements, vitesses et erreurs.")
                    )
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v157(window):
    if getattr(window, "_v157_download_center", False):
        return

    tracker = DownloadTracker()
    window.download_tracker = tracker

    tab = DownloadCenter(window, tracker)
    window.download_center_tab = tab

    search = getattr(window, "search_tab", None)
    idx = window.tabs.indexOf(search)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "⬇ Téléchargements")

    _patch_search(window, tracker)
    _patch_setup(window, tracker)
    _add_nav(window)

    window._v157_download_center = True
