"""Extension v140 : benchmark VRAM/CPU et évaluation automatique Ollama."""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil
import requests
from PyQt6.QtCore import QThread, Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend.ai_manager import AIManager


DEFAULT_PROMPTS = """Explique simplement ce qu'est une API locale en trois phrases.
Écris une fonction Python qui supprime les doublons d'une liste en conservant l'ordre.
Donne trois idées concrètes pour organiser un projet logiciel personnel.
Résume en une phrase : Un modèle local peut fonctionner sans envoyer les données vers un service distant.
Quel est le résultat de 37 × 24 ? Explique brièvement le calcul."""


def _bench_root():
    path = Path.home() / ".ia_manager" / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ns_to_s(value):
    try:
        return float(value or 0) / 1_000_000_000.0
    except Exception:
        return 0.0


def _tokens_per_s(count, duration_ns):
    seconds = _ns_to_s(duration_ns)
    return float(count or 0) / seconds if seconds else 0.0


def _ram_used_gb():
    vm = psutil.virtual_memory()
    return (vm.total - vm.available) / (1024 ** 3)


def _ollama_vram(url, model):
    try:
        r = requests.get(url + "/api/ps", timeout=4)
        if r.status_code != 200:
            return None
        for item in r.json().get("models", []):
            name = str(item.get("name") or item.get("model") or "")
            if name == model or name.split(":")[0] == model.split(":")[0]:
                raw = item.get("size_vram")
                if raw is not None:
                    return float(raw) / (1024 ** 3)
    except Exception:
        pass
    return None


class BenchmarkWorker(QThread):
    progress = pyqtSignal(str)
    row_ready = pyqtSignal(dict)
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, models, prompts, repeats=1, parent=None):
        super().__init__(parent)
        self.models = list(models)
        self.prompts = list(prompts)
        self.repeats = int(repeats)
        self.stop_event = threading.Event()
        self.url = "http://localhost:11434"

    def stop(self):
        self.stop_event.set()

    def run(self):
        campaign = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "models": self.models,
            "prompts": self.prompts,
            "repeats": self.repeats,
            "rows": [],
            "cancelled": False,
        }
        try:
            total = max(1, len(self.models) * len(self.prompts) * self.repeats)
            done = 0
            for model in self.models:
                if self.stop_event.is_set():
                    campaign["cancelled"] = True
                    break

                for repeat in range(self.repeats):
                    for prompt_index, prompt in enumerate(self.prompts, 1):
                        if self.stop_event.is_set():
                            campaign["cancelled"] = True
                            break

                        done += 1
                        self.progress.emit(
                            f"{done}/{total} · {model} · prompt {prompt_index}/{len(self.prompts)}"
                        )

                        ram_before = _ram_used_gb()
                        started = time.perf_counter()
                        response = requests.post(
                            self.url + "/api/generate",
                            json={
                                "model": model,
                                "prompt": prompt,
                                "stream": False,
                                "keep_alive": "5m",
                                "options": {"temperature": 0, "seed": 42},
                            },
                            timeout=900,
                        )
                        wall = time.perf_counter() - started
                        ram_after = _ram_used_gb()

                        if response.status_code != 200:
                            raise RuntimeError(
                                f"{model} : Ollama {response.status_code} · {response.text[:300]}"
                            )

                        data = response.json()
                        row = {
                            "model": model,
                            "repeat": repeat + 1,
                            "prompt_index": prompt_index,
                            "prompt": prompt,
                            "response": str(data.get("response") or ""),
                            "wall_s": wall,
                            "total_s": _ns_to_s(data.get("total_duration")),
                            "load_s": _ns_to_s(data.get("load_duration")),
                            "prompt_eval_s": _ns_to_s(data.get("prompt_eval_duration")),
                            "eval_s": _ns_to_s(data.get("eval_duration")),
                            "prompt_tokens": int(data.get("prompt_eval_count") or 0),
                            "output_tokens": int(data.get("eval_count") or 0),
                            "tokens_s": _tokens_per_s(
                                data.get("eval_count"), data.get("eval_duration")
                            ),
                            "ram_before_gb": ram_before,
                            "ram_after_gb": ram_after,
                            "vram_loaded_gb": _ollama_vram(self.url, model),
                            "done_reason": data.get("done_reason") or "",
                        }
                        campaign["rows"].append(row)
                        self.row_ready.emit(dict(row))

                    if self.stop_event.is_set():
                        break

            summaries = {}
            for model in self.models:
                rows = [r for r in campaign["rows"] if r["model"] == model]
                if not rows:
                    continue

                def avg(key):
                    vals = [float(r[key]) for r in rows if r.get(key) is not None]
                    return sum(vals) / len(vals) if vals else 0.0

                vram_vals = [
                    float(r["vram_loaded_gb"])
                    for r in rows if r.get("vram_loaded_gb") is not None
                ]
                summaries[model] = {
                    "tests": len(rows),
                    "avg_tokens_s": avg("tokens_s"),
                    "avg_total_s": avg("total_s"),
                    "avg_wall_s": avg("wall_s"),
                    "avg_load_s": avg("load_s"),
                    "avg_output_tokens": avg("output_tokens"),
                    "max_vram_loaded_gb": max(vram_vals) if vram_vals else None,
                    "avg_ram_after_gb": avg("ram_after_gb"),
                }
            campaign["summaries"] = summaries

            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = _bench_root() / f"benchmark-{stamp}.json"
            path.write_text(
                json.dumps(campaign, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            campaign["path"] = str(path)
            self.completed.emit(campaign)
        except Exception as exc:
            self.failed.emit(str(exc))


class BenchmarkTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.ai = AIManager()
        self.worker = None
        self.build_ui()
        self.refresh_models()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("📊 Benchmark IA")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Comparez plusieurs modèles Ollama avec exactement les mêmes prompts. "
            "Les métriques de génération viennent directement d’Ollama."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()

        models_box = QGroupBox("1 · Modèles")
        ml = QVBoxLayout(models_box)
        self.models = QListWidget()
        self.models.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        ml.addWidget(self.models)
        row = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.all_btn = QPushButton("Tout cocher")
        self.none_btn = QPushButton("Tout décocher")
        for b in (self.refresh_btn, self.all_btn, self.none_btn):
            row.addWidget(b)
        ml.addLayout(row)
        top.addWidget(models_box, 1)

        prompts_box = QGroupBox("2 · Batterie de prompts")
        pl = QVBoxLayout(prompts_box)
        self.prompts = QPlainTextEdit()
        self.prompts.setPlainText(DEFAULT_PROMPTS)
        pl.addWidget(self.prompts)
        hint = QLabel("Un prompt par ligne · température 0 · seed 42.")
        hint.setWordWrap(True)
        pl.addWidget(hint)
        top.addWidget(prompts_box, 2)

        root.addLayout(top)

        options = QHBoxLayout()
        options.addWidget(QLabel("Répétitions"))
        self.repeats = QSpinBox()
        self.repeats.setRange(1, 10)
        self.repeats.setValue(1)
        options.addWidget(self.repeats)

        self.run_btn = QPushButton("▶ Lancer le benchmark")
        self.run_btn.setObjectName("Primary")
        options.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ Arrêter après le test en cours")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        options.addWidget(self.stop_btn)

        self.open_btn = QPushButton("📁 Ouvrir les résultats")
        options.addWidget(self.open_btn)
        options.addStretch()
        root.addLayout(options)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        summary_box = QGroupBox("3 · Résumé par modèle")
        sl = QVBoxLayout(summary_box)
        self.summary = QTableWidget(0, 7)
        self.summary.setHorizontalHeaderLabels([
            "Modèle", "Tests", "Tokens/s", "Temps total", "Chargement",
            "VRAM chargée", "RAM système après",
        ])
        self.summary.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary.verticalHeader().hide()
        self.summary.horizontalHeader().setStretchLastSection(True)
        sl.addWidget(self.summary)
        root.addWidget(summary_box)

        details_box = QGroupBox("4 · Détail prompt par prompt")
        dl = QVBoxLayout(details_box)
        self.details = QTableWidget(0, 8)
        self.details.setHorizontalHeaderLabels([
            "Modèle", "Prompt", "Sortie", "Tokens/s", "Tokens sortie",
            "Temps total", "Load", "VRAM",
        ])
        self.details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.details.verticalHeader().hide()
        self.details.horizontalHeader().setStretchLastSection(True)
        dl.addWidget(self.details)
        root.addWidget(details_box, 1)

        self.refresh_btn.clicked.connect(self.refresh_models)
        self.all_btn.clicked.connect(lambda: self.set_all(True))
        self.none_btn.clicked.connect(lambda: self.set_all(False))
        self.run_btn.clicked.connect(self.start_benchmark)
        self.stop_btn.clicked.connect(self.stop_benchmark)
        self.open_btn.clicked.connect(self.open_results)

    def refresh_models(self):
        checked = {
            self.models.item(i).text()
            for i in range(self.models.count())
            if self.models.item(i).checkState() == Qt.CheckState.Checked
        }
        self.models.clear()
        for model in self.ai.get_available_models(force=True):
            item = QListWidgetItem(model)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if model in checked else Qt.CheckState.Unchecked
            )
            self.models.addItem(item)
        if self.models.count() and not checked:
            self.models.item(0).setCheckState(Qt.CheckState.Checked)
        self.status.setText(f"{self.models.count()} modèle(s) Ollama détecté(s).")

    def set_all(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.models.count()):
            self.models.item(i).setCheckState(state)

    def selected_models(self):
        return [
            self.models.item(i).text()
            for i in range(self.models.count())
            if self.models.item(i).checkState() == Qt.CheckState.Checked
        ]

    def prompt_list(self):
        return [x.strip() for x in self.prompts.toPlainText().splitlines() if x.strip()]

    def set_busy(self, busy):
        self.run_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.refresh_btn.setEnabled(not busy)
        self.models.setEnabled(not busy)
        self.prompts.setEnabled(not busy)
        self.repeats.setEnabled(not busy)

    def start_benchmark(self):
        if self.worker is not None:
            return
        models = self.selected_models()
        prompts = self.prompt_list()
        if not models:
            self.status.setText("Cochez au moins un modèle.")
            return
        if not prompts:
            self.status.setText("Ajoutez au moins un prompt.")
            return
        if not self.ai.is_ollama_running():
            self.status.setText("Ollama n’est pas lancé.")
            return

        self.details.setRowCount(0)
        self.summary.setRowCount(0)

        self.worker = BenchmarkWorker(models, prompts, self.repeats.value(), self)
        self.worker.progress.connect(self.status.setText)
        self.worker.row_ready.connect(self.add_row)
        self.worker.completed.connect(self.benchmark_done)
        self.worker.failed.connect(self.benchmark_failed)
        self.set_busy(True)
        self.worker.start()

    def add_row(self, row):
        r = self.details.rowCount()
        self.details.insertRow(r)
        vram = row.get("vram_loaded_gb")
        values = [
            row["model"],
            row["prompt"][:90],
            row["response"][:160].replace("\n", " "),
            f"{row['tokens_s']:.1f}",
            str(row["output_tokens"]),
            f"{row['total_s']:.2f} s",
            f"{row['load_s']:.2f} s",
            "—" if vram is None else f"{vram:.1f} Go",
        ]
        for c, value in enumerate(values):
            self.details.setItem(r, c, QTableWidgetItem(value))
        self.details.scrollToBottom()

    def benchmark_done(self, campaign):
        self.worker = None
        self.set_busy(False)
        summaries = campaign.get("summaries", {})
        self.summary.setRowCount(len(summaries))
        for r, (model, data) in enumerate(summaries.items()):
            vram = data.get("max_vram_loaded_gb")
            values = [
                model,
                str(data.get("tests", 0)),
                f"{data.get('avg_tokens_s', 0):.1f}",
                f"{data.get('avg_total_s', 0):.2f} s",
                f"{data.get('avg_load_s', 0):.2f} s",
                "—" if vram is None else f"{vram:.1f} Go",
                f"{data.get('avg_ram_after_gb', 0):.1f} Go",
            ]
            for c, value in enumerate(values):
                self.summary.setItem(r, c, QTableWidgetItem(value))
        self.summary.resizeColumnsToContents()
        self.status.setText(
            f"✅ Benchmark enregistré · {len(campaign.get('rows', []))} test(s) · "
            f"{campaign.get('path', '')}"
        )

    def benchmark_failed(self, error):
        self.worker = None
        self.set_busy(False)
        self.status.setText("❌ Benchmark interrompu : " + error)

    def stop_benchmark(self):
        if self.worker is not None:
            self.worker.stop()
            self.status.setText("Arrêt demandé · fin après la requête Ollama en cours.")

    def open_results(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(_bench_root())))

    def shutdown(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(2000)


def install_v140(window):
    if getattr(window, "_v140_benchmark", False):
        return
    tab = BenchmarkTab(window)
    window.benchmark_tab = tab
    family = getattr(window, "family_tree_tab", None)
    idx = window.tabs.indexOf(family)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "📊 Benchmark")

    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(tab.shutdown)
    except Exception:
        pass

    window._v140_benchmark = True
