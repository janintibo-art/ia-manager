"""Extension v143 : recherche Heretic + comparateur Original/Obliteratus/Heretic."""
import json
from datetime import datetime
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout,
)

from src.backend import local_jobs
from src.backend.ai_manager import AIManager
from src.ui import v142_extension as h


def _research_root():
    path = Path.home() / ".ia_manager" / "heretic" / "research"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _research_registry():
    path = _research_root() / "runs.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save_research_registry(rows):
    path = _research_root() / "runs.json"
    path.write_text(json.dumps(rows[-100:], ensure_ascii=False, indent=2), encoding="utf-8")


def install_v143(window):
    tab = getattr(window, "heretic_tab", None)
    if tab is None or getattr(window, "_v143_heretic_research", False):
        return

    # ------------------------------------------------------------------ Recherche
    research_box = QGroupBox("4 · Recherche Heretic · directions résiduelles")
    rl = QVBoxLayout(research_box)

    hint = QLabel(
        "Analyse la géométrie interne utilisée par l’abliteration. "
        "La projection PaCMAP peut être très lente sur les gros modèles et travaille aussi sur CPU."
    )
    hint.setWordWrap(True)
    rl.addWidget(hint)

    controls = QHBoxLayout()
    tab.v143_geometry = QCheckBox("Afficher la géométrie résiduelle")
    tab.v143_geometry.setChecked(True)
    controls.addWidget(tab.v143_geometry)

    tab.v143_plots = QCheckBox("Générer les projections PaCMAP + animation")
    controls.addWidget(tab.v143_plots)

    controls.addWidget(QLabel("Essais"))
    tab.v143_trials = QSpinBox()
    tab.v143_trials.setRange(5, 200)
    tab.v143_trials.setValue(20)
    controls.addWidget(tab.v143_trials)

    controls.addStretch()
    rl.addLayout(controls)

    buttons = QHBoxLayout()
    tab.v143_install_research = QPushButton("Installer les dépendances recherche")
    buttons.addWidget(tab.v143_install_research)

    tab.v143_run_research = QPushButton("🔬 Lancer l’analyse")
    tab.v143_run_research.setObjectName("Primary")
    buttons.addWidget(tab.v143_run_research)

    tab.v143_stop_research = QPushButton("■ Arrêter")
    tab.v143_stop_research.setObjectName("Danger")
    tab.v143_stop_research.setEnabled(False)
    buttons.addWidget(tab.v143_stop_research)

    tab.v143_open_research = QPushButton("📁 Ouvrir les résultats")
    buttons.addWidget(tab.v143_open_research)
    buttons.addStretch()
    rl.addLayout(buttons)

    tab.v143_research_status = QLabel("Prêt.")
    tab.v143_research_status.setWordWrap(True)
    rl.addWidget(tab.v143_research_status)

    # ------------------------------------------------------------------ Comparateur
    compare_box = QGroupBox("5 · Comparateur Original / Obliteratus / Heretic")
    cl = QVBoxLayout(compare_box)

    hint = QLabel(
        "Sélectionnez trois modèles Ollama dérivés de la même base. "
        "IA Manager ne décide pas lequel est « meilleur » : il prépare les mêmes tests "
        "de vitesse et les mêmes critères qualitatifs pour une comparaison reproductible."
    )
    hint.setWordWrap(True)
    cl.addWidget(hint)

    row = QHBoxLayout()
    row.addWidget(QLabel("Original"))
    tab.v143_original = QComboBox()
    row.addWidget(tab.v143_original, 1)

    row.addWidget(QLabel("Obliteratus"))
    tab.v143_obliteratus = QComboBox()
    row.addWidget(tab.v143_obliteratus, 1)

    row.addWidget(QLabel("Heretic"))
    tab.v143_heretic_model = QComboBox()
    row.addWidget(tab.v143_heretic_model, 1)

    tab.v143_refresh_models = QPushButton("🔄")
    row.addWidget(tab.v143_refresh_models)
    cl.addLayout(row)

    actions = QHBoxLayout()
    tab.v143_to_benchmark = QPushButton("📊 Envoyer au Benchmark")
    actions.addWidget(tab.v143_to_benchmark)

    tab.v143_original_vs_obl = QPushButton("⚖️ Qualitatif Original ↔ Obliteratus")
    actions.addWidget(tab.v143_original_vs_obl)

    tab.v143_original_vs_heretic = QPushButton("⚖️ Qualitatif Original ↔ Heretic")
    actions.addWidget(tab.v143_original_vs_heretic)

    tab.v143_obl_vs_heretic = QPushButton("⚖️ Qualitatif Obliteratus ↔ Heretic")
    actions.addWidget(tab.v143_obl_vs_heretic)
    actions.addStretch()
    cl.addLayout(actions)

    tab.v143_compare_status = QLabel("Prêt.")
    tab.v143_compare_status.setWordWrap(True)
    cl.addWidget(tab.v143_compare_status)

    root = tab.layout()
    insert_at = max(0, root.count() - 2)
    root.insertWidget(insert_at, research_box)
    root.insertWidget(insert_at + 1, compare_box)

    # Process séparé : ne perturbe pas le QProcess principal de v142.
    tab.v143_process = QProcess(tab)
    tab.v143_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v143_process.readyReadStandardOutput.connect(lambda: tab.v143_read_output())
    tab.v143_process.finished.connect(lambda c, s: tab.v143_finished(c, s))
    tab.v143_process.errorOccurred.connect(lambda e: tab.v143_failed(e))
    tab.v143_mode = ""
    tab.v143_token = None
    tab.v143_run_dir = ""

    def v143_busy(self):
        return self.v143_process.state() != QProcess.ProcessState.NotRunning

    def v143_set_busy(self, busy):
        self.v143_install_research.setEnabled(not busy)
        self.v143_run_research.setEnabled(
            not busy and h._heretic_exe().is_file()
        )
        self.v143_stop_research.setEnabled(busy)
        self.v143_geometry.setEnabled(not busy)
        self.v143_plots.setEnabled(not busy)
        self.v143_trials.setEnabled(not busy)

    def v143_start_process(self, program, args, mode):
        if self.v143_busy():
            return
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        env.insert("PYTORCH_ALLOC_CONF", "expandable_segments:True")
        self.v143_process.setProcessEnvironment(env)
        self.v143_process.setWorkingDirectory(str(h._tool_root()))
        self.v143_mode = mode
        self.v143_set_busy(True)
        self.v143_process.start(str(program), list(args))

    def v143_install_research_deps(self):
        py = h._venv_python()
        if not py.is_file():
            self.v143_research_status.setText("Installez d’abord Heretic.")
            return

        requirement = f"heretic-llm[research] @ {h.HERETIC_ARCHIVE}"
        self.log.clear()
        self.v143_research_status.setText(
            "Installation des dépendances recherche Heretic…"
        )
        self.v143_start_process(
            py,
            ["-m", "pip", "install", "--upgrade", requirement],
            "install_research",
        )

    def v143_run_analysis(self):
        model = self.model.text().strip()
        if not model:
            self.v143_research_status.setText("Indiquez d’abord le modèle source.")
            return
        if not h._heretic_exe().is_file():
            self.v143_research_status.setText("Installez d’abord Heretic.")
            return
        if not self.v143_geometry.isChecked() and not self.v143_plots.isChecked():
            self.v143_research_status.setText(
                "Activez au moins géométrie résiduelle ou projections PaCMAP."
            )
            return

        if local_jobs.enabled():
            self.v143_token = local_jobs.reserve("Heretic recherche")
            if self.v143_token is None:
                self.v143_research_status.setText(
                    "Un autre travail local utilise déjà les ressources."
                )
                return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = _research_root() / stamp
        plots = run_dir / "plots"
        output = run_dir / "adapter"
        run_dir.mkdir(parents=True, exist_ok=True)
        plots.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        self.v143_run_dir = str(run_dir)

        trials = self.v143_trials.value()
        startup = min(max(4, trials // 3), max(4, trials - 1))
        args = [
            "--model", model,
            "--n-trials", str(trials),
            "--n-startup-trials", str(startup),
            "--seed", str(self.seed.value()),
            "--checkpoint-action", "restart",
            "--trial-index", "0",
            "--model-action", "save",
            "--save-directory", str(output),
            "--export-strategy", "adapter",
            "--quantization", "bnb_4bit" if self.quant.isChecked() else "none",
        ]
        if self.v143_geometry.isChecked():
            args.append("--print-residual-geometry")
        if self.v143_plots.isChecked():
            args += ["--plot-residuals", "--residual-plot-path", str(plots)]

        self.log.clear()
        self.v143_research_status.setText(
            f"Analyse Heretic en cours · {trials} essais. "
            "PaCMAP peut prendre longtemps si activé."
        )
        self.v143_start_process(h._heretic_exe(), args, "research")

    def v143_read_output(self):
        text = bytes(self.v143_process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )

    def v143_finished(self, code, status):
        self.v143_read_output()
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit
        mode = self.v143_mode
        self.v143_mode = ""

        if mode == "research":
            local_jobs.release(self.v143_token)
            self.v143_token = None

        if ok and mode == "install_research":
            self.v143_research_status.setText(
                "✅ Dépendances recherche installées."
            )
        elif ok and mode == "research":
            rows = _research_registry()
            rows.append({
                "created": datetime.now().isoformat(timespec="seconds"),
                "model": self.model.text().strip(),
                "path": self.v143_run_dir,
                "geometry": self.v143_geometry.isChecked(),
                "plots": self.v143_plots.isChecked(),
                "trials": self.v143_trials.value(),
            })
            _save_research_registry(rows)
            self.v143_research_status.setText(
                "✅ Analyse terminée · " + self.v143_run_dir
            )
        elif not ok:
            self.v143_research_status.setText(
                f"❌ Analyse/intervention interrompue (code {code}). Consultez le journal."
            )

        self.v143_set_busy(False)

    def v143_failed(self, _error):
        if self.v143_mode == "research":
            local_jobs.release(self.v143_token)
            self.v143_token = None
        self.v143_mode = ""
        self.v143_research_status.setText(
            "Démarrage impossible : " + self.v143_process.errorString()
        )
        self.v143_set_busy(False)

    def v143_stop(self):
        if self.v143_busy():
            self.v143_process.terminate()
            self.v143_research_status.setText("Arrêt demandé…")

    def v143_open_results(self):
        target = Path(self.v143_run_dir) if self.v143_run_dir else _research_root()
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # ----------------------------------------------------------- Comparateur
    def v143_reload_models(self):
        ai = AIManager()
        models = ai.get_available_models(force=True)
        current = (
            self.v143_original.currentText(),
            self.v143_obliteratus.currentText(),
            self.v143_heretic_model.currentText(),
        )
        for combo in (
            self.v143_original, self.v143_obliteratus, self.v143_heretic_model
        ):
            combo.clear()
            combo.addItems(models)

        for combo, value in zip(
            (self.v143_original, self.v143_obliteratus, self.v143_heretic_model),
            current,
        ):
            if value:
                idx = combo.findText(value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        # Aide au préremplissage Obliteratus depuis son registre.
        obl_file = Path.home() / ".ia_manager" / "obliteratus_versions.json"
        try:
            obl_rows = json.loads(obl_file.read_text(encoding="utf-8"))
        except Exception:
            obl_rows = []
        names = [
            str(x.get("ollama_name") or "")
            for x in obl_rows if isinstance(x, dict) and x.get("ollama_name")
        ]
        if names and not current[1]:
            idx = self.v143_obliteratus.findText(names[-1])
            if idx >= 0:
                self.v143_obliteratus.setCurrentIndex(idx)

        self.v143_compare_status.setText(
            f"{len(models)} modèle(s) Ollama disponible(s)."
        )

    def v143_send_benchmark(self):
        bench = getattr(self.window, "benchmark_tab", None)
        if bench is None:
            self.v143_compare_status.setText("Onglet Benchmark indisponible.")
            return
        selected = {
            self.v143_original.currentText().strip(),
            self.v143_obliteratus.currentText().strip(),
            self.v143_heretic_model.currentText().strip(),
        }
        selected.discard("")
        bench.refresh_models()
        for i in range(bench.models.count()):
            item = bench.models.item(i)
            item.setCheckState(
                2 if item.text() in selected else 0
            )
        self.window.tabs.setCurrentWidget(bench)
        bench.status.setText(
            "✅ Original / Obliteratus / Heretic préparés pour le même benchmark."
        )

    def v143_send_qualitative(self, left, right):
        bench = getattr(self.window, "benchmark_tab", None)
        if bench is None or not hasattr(bench, "v141_before"):
            self.v143_compare_status.setText(
                "Évaluation qualitative indisponible."
            )
            return
        bench.v141_refresh_models()
        for combo, value in (
            (bench.v141_before, left),
            (bench.v141_after, right),
        ):
            idx = combo.findText(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        self.window.tabs.setCurrentWidget(bench)
        bench.v141_status.setText(
            f"✅ Comparaison préparée : {left} ↔ {right}."
        )

    def v143_pair(self, pair):
        o = self.v143_original.currentText().strip()
        b = self.v143_obliteratus.currentText().strip()
        hmodel = self.v143_heretic_model.currentText().strip()
        if pair == "orig_obl":
            self.v143_send_qualitative(o, b)
        elif pair == "orig_heretic":
            self.v143_send_qualitative(o, hmodel)
        else:
            self.v143_send_qualitative(b, hmodel)

    tab.v143_busy = MethodType(v143_busy, tab)
    tab.v143_set_busy = MethodType(v143_set_busy, tab)
    tab.v143_start_process = MethodType(v143_start_process, tab)
    tab.v143_install_research_deps = MethodType(v143_install_research_deps, tab)
    tab.v143_run_analysis = MethodType(v143_run_analysis, tab)
    tab.v143_read_output = MethodType(v143_read_output, tab)
    tab.v143_finished = MethodType(v143_finished, tab)
    tab.v143_failed = MethodType(v143_failed, tab)
    tab.v143_stop = MethodType(v143_stop, tab)
    tab.v143_open_results = MethodType(v143_open_results, tab)
    tab.v143_reload_models = MethodType(v143_reload_models, tab)
    tab.v143_send_benchmark = MethodType(v143_send_benchmark, tab)
    tab.v143_send_qualitative = MethodType(v143_send_qualitative, tab)
    tab.v143_pair = MethodType(v143_pair, tab)

    tab.v143_install_research.clicked.connect(tab.v143_install_research_deps)
    tab.v143_run_research.clicked.connect(tab.v143_run_analysis)
    tab.v143_stop_research.clicked.connect(tab.v143_stop)
    tab.v143_open_research.clicked.connect(tab.v143_open_results)
    tab.v143_refresh_models.clicked.connect(tab.v143_reload_models)
    tab.v143_to_benchmark.clicked.connect(tab.v143_send_benchmark)
    tab.v143_original_vs_obl.clicked.connect(lambda: tab.v143_pair("orig_obl"))
    tab.v143_original_vs_heretic.clicked.connect(
        lambda: tab.v143_pair("orig_heretic")
    )
    tab.v143_obl_vs_heretic.clicked.connect(
        lambda: tab.v143_pair("obl_heretic")
    )

    old_shutdown = tab.shutdown

    def shutdown(self):
        local_jobs.release(self.v143_token)
        self.v143_token = None
        if self.v143_process.state() != QProcess.ProcessState.NotRunning:
            self.v143_process.terminate()
            if not self.v143_process.waitForFinished(1500):
                self.v143_process.kill()
                self.v143_process.waitForFinished(1500)
        old_shutdown()

    tab.shutdown = MethodType(shutdown, tab)

    tab.v143_reload_models()
    tab.v143_set_busy(False)
    window._v143_heretic_research = True
