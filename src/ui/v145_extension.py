"""Extension v145 : atelier ErisForge."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QDoubleSpinBox,
    QVBoxLayout, QWidget,
)

from src.backend import local_jobs, settings, storage
from src.backend import obliteratus as ob
from src.backend import obliteratus_export as oe


ERIS_REV = "0d9e0de9980d61312cab0d2f0cc10e7cc27828b2"
ERIS_ARCHIVE = f"https://github.com/Tsadoq/ErisForge/archive/{ERIS_REV}.zip"


def _root():
    p = Path.home() / ".ia_manager" / "tools" / "erisforge"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _venv_python():
    v = _root() / ".venv"
    return v / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _runner():
    return Path(__file__).resolve().parent.parent / "backend" / "erisforge_runner.py"


def _default_python():
    for value in (
        settings.get("training_python"),
        settings.get("obliteratus_python"),
        ob.default_python(),
    ):
        if value:
            p = Path(str(value)).expanduser()
            if p.is_file():
                return str(p)
    return ""


def _safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip(".-")
    return value[:96] or "erisforge-model"


def _history_file():
    p = Path.home() / ".ia_manager" / "erisforge_runs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _history():
    try:
        value = json.loads(_history_file().read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save_history(rows):
    _history_file().write_text(
        json.dumps(rows[-200:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ErisForgeTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.queue = []
        self.mode = ""
        self.token = None
        self.direction_path = ""
        self.last_output = ""
        self.current_job = {}
        self.build_ui()
        self.refresh_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("⚒️ ErisForge · atelier de transformation de couches")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "ErisForge calcule une direction comportementale à partir de deux groupes "
            "d’instructions, puis peut atténuer ou renforcer cette direction sur une plage de couches."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        engine = QGroupBox("1 · Moteur ErisForge")
        el = QVBoxLayout(engine)
        form = QFormLayout()
        self.python = QLineEdit(_default_python())
        self.python.setPlaceholderText("Python 3.11+")
        form.addRow("Python de base", self.python)
        el.addLayout(form)

        row = QHBoxLayout()
        self.install_btn = QPushButton("Installer / réparer ErisForge")
        row.addWidget(self.install_btn)
        self.diag_btn = QPushButton("Diagnostic")
        row.addWidget(self.diag_btn)
        self.open_tool_btn = QPushButton("📁 Dossier moteur")
        row.addWidget(self.open_tool_btn)
        row.addStretch()
        el.addLayout(row)

        self.engine_status = QLabel()
        self.engine_status.setWordWrap(True)
        el.addWidget(self.engine_status)
        root.addWidget(engine)

        data = QGroupBox("2 · Modèle et jeux d’instructions")
        dl = QVBoxLayout(data)
        form = QFormLayout()

        self.model = QLineEdit()
        self.model.setPlaceholderText("Identifiant Hugging Face ou dossier local")
        form.addRow("Modèle", self.model)

        self.objective = QLineEdit()
        self.objective.setPlaceholderText("Un prompt par ligne")
        form.addRow("Comportement cible", self.objective)

        self.reference = QLineEdit()
        self.reference.setPlaceholderText("Un prompt par ligne")
        form.addRow("Comportement de référence", self.reference)

        self.max_inst = QSpinBox()
        self.max_inst.setRange(5, 500)
        self.max_inst.setValue(50)
        form.addRow("Instructions max / groupe", self.max_inst)

        self.batch = QSpinBox()
        self.batch.setRange(1, 32)
        self.batch.setValue(4)
        form.addRow("Batch", self.batch)
        dl.addLayout(form)

        row = QHBoxLayout()
        self.pick_model = QPushButton("Modèle local…")
        row.addWidget(self.pick_model)
        self.pick_objective = QPushButton("Fichier cible…")
        row.addWidget(self.pick_objective)
        self.pick_reference = QPushButton("Fichier référence…")
        row.addWidget(self.pick_reference)
        row.addStretch()
        dl.addLayout(row)
        root.addWidget(data)

        transform = QGroupBox("3 · Transformation")
        tl = QVBoxLayout(transform)
        form = QFormLayout()

        self.intervention = QComboBox()
        self.intervention.addItem("Atténuation / ablation", "ablation")
        self.intervention.addItem("Renforcement / addition", "addition")
        form.addRow("Intervention", self.intervention)

        self.layer_start = QSpinBox()
        self.layer_start.setRange(0, 255)
        self.layer_start.setValue(8)
        form.addRow("Première couche", self.layer_start)

        self.layer_end = QSpinBox()
        self.layer_end.setRange(0, 255)
        self.layer_end.setValue(20)
        form.addRow("Dernière couche incluse", self.layer_end)

        self.strength = QDoubleSpinBox()
        self.strength.setRange(0.0, 1.0)
        self.strength.setDecimals(2)
        self.strength.setSingleStep(0.05)
        self.strength.setValue(1.0)
        form.addRow("Intensité", self.strength)

        self.seed = QSpinBox()
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(42)
        form.addRow("Seed", self.seed)

        self.output_name = QLineEdit("modele-erisforge")
        form.addRow("Nom de sortie", self.output_name)
        tl.addLayout(form)

        row = QHBoxLayout()
        self.inspect_btn = QPushButton("🧠 Proposer les couches depuis config.json")
        row.addWidget(self.inspect_btn)
        self.preview_btn = QPushButton("👁 Aperçu paramètres")
        row.addWidget(self.preview_btn)
        row.addStretch()
        tl.addLayout(row)
        root.addWidget(transform)

        actions = QHBoxLayout()
        self.measure_btn = QPushButton("① Calculer la direction")
        self.measure_btn.setObjectName("Primary")
        actions.addWidget(self.measure_btn)

        self.apply_btn = QPushButton("② Transformer et sauvegarder")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setEnabled(False)
        actions.addWidget(self.apply_btn)

        self.stop_btn = QPushButton("■ Arrêter")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        actions.addWidget(self.stop_btn)

        self.open_output_btn = QPushButton("📁 Sortie")
        self.open_output_btn.setEnabled(False)
        actions.addWidget(self.open_output_btn)

        self.pipeline_btn = QPushButton("➡ GGUF / Ollama")
        self.pipeline_btn.setEnabled(False)
        actions.addWidget(self.pipeline_btn)
        actions.addStretch()
        root.addLayout(actions)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(6000)
        root.addWidget(self.log, 1)

        self.install_btn.clicked.connect(self.install_tool)
        self.diag_btn.clicked.connect(self.diagnostic)
        self.open_tool_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(_root())))
        )
        self.pick_model.clicked.connect(self.choose_model)
        self.pick_objective.clicked.connect(
            lambda: self.choose_text_file(self.objective, "Instructions du comportement cible")
        )
        self.pick_reference.clicked.connect(
            lambda: self.choose_text_file(self.reference, "Instructions de référence")
        )
        self.inspect_btn.clicked.connect(self.inspect_config)
        self.preview_btn.clicked.connect(self.preview)
        self.measure_btn.clicked.connect(self.measure)
        self.apply_btn.clicked.connect(self.apply_transform)
        self.stop_btn.clicked.connect(self.stop)
        self.open_output_btn.clicked.connect(self.open_output)
        self.pipeline_btn.clicked.connect(self.send_pipeline)

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def ready(self):
        return _venv_python().is_file()

    def refresh_state(self):
        self.engine_status.setText(
            "✅ ErisForge installé dans son environnement isolé."
            if self.ready()
            else "ErisForge n’est pas encore installé."
        )
        self.diag_btn.setEnabled(self.ready() and not self.busy())
        self.measure_btn.setEnabled(self.ready() and not self.busy())

    def set_busy(self, busy):
        for w in (
            self.install_btn, self.diag_btn, self.python, self.model, self.objective,
            self.reference, self.max_inst, self.batch, self.intervention,
            self.layer_start, self.layer_end, self.strength, self.seed,
            self.output_name, self.pick_model, self.pick_objective,
            self.pick_reference, self.inspect_btn, self.preview_btn,
        ):
            w.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.measure_btn.setEnabled(not busy and self.ready())
        self.apply_btn.setEnabled(
            not busy and bool(self.direction_path) and Path(self.direction_path).is_file()
        )
        self.open_output_btn.setEnabled(
            not busy and bool(self.last_output) and Path(self.last_output).exists()
        )
        self.pipeline_btn.setEnabled(
            not busy and bool(self.last_output)
            and oe.valid_checkpoint(Path(self.last_output))
        )

    def choose_model(self):
        p = QFileDialog.getExistingDirectory(self, "Choisir un modèle local")
        if p:
            self.model.setText(p)
            self.output_name.setText(_safe_name(Path(p).name + "-erisforge"))

    def choose_text_file(self, field, title):
        p, _ = QFileDialog.getOpenFileName(
            self, title, "", "Texte (*.txt);;Tous les fichiers (*)"
        )
        if p:
            field.setText(p)

    def inspect_config(self):
        p = Path(self.model.text().strip()) / "config.json"
        if not p.is_file():
            self.status.setText(
                "Choisissez un modèle local contenant config.json pour cette estimation."
            )
            return
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            n = int(
                cfg.get("num_hidden_layers")
                or (cfg.get("text_config") or {}).get("num_hidden_layers")
            )
        except Exception as exc:
            self.status.setText("Lecture impossible : " + str(exc))
            return
        start = max(1, int(n * .25))
        end = max(start, min(n - 2, int(n * .75)))
        self.layer_start.setValue(start)
        self.layer_end.setValue(end)
        self.status.setText(
            f"{n} couches détectées · plage heuristique {start} → {end}. "
            "ErisForge cherchera la direction la plus discriminante dans cette zone."
        )

    def preview(self):
        self.status.setText(
            f"{self.intervention.currentText()} · couches {self.layer_start.value()} → "
            f"{self.layer_end.value()} · intensité {self.strength.value():.2f} · "
            f"{self.max_inst.value()} instructions max par groupe · batch {self.batch.value()}."
        )

    def start_queue(self, steps, mode):
        if self.busy():
            return
        self.queue = list(steps)
        self.mode = mode
        self.set_busy(True)
        self.next_step()

    def next_step(self):
        if not self.queue:
            return
        program, args = self.queue.pop(0)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        env.insert("PYTORCH_ALLOC_CONF", "expandable_segments:True")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(_root()))
        self.process.start(str(program), list(args))

    def install_tool(self):
        base = Path(self.python.text().strip()).expanduser()
        if not base.is_file():
            self.status.setText("Choisissez un véritable exécutable Python 3.11+.")
            return
        venv = _root() / ".venv"
        vp = _venv_python()
        steps = []
        if not vp.is_file():
            steps.append((str(base), ["-m", "venv", str(venv)]))
        steps += [
            (str(vp), ["-m", "pip", "install", "--upgrade", "pip", "wheel"]),
            (str(vp), ["-m", "pip", "install", "--upgrade", ERIS_ARCHIVE, "psutil"]),
            (
                str(vp),
                [
                    "-c",
                    "import torch,erisforge,psutil;"
                    "print('ErisForge OK');"
                    "print('Torch',torch.__version__);"
                    "print('CUDA',torch.cuda.is_available());"
                    "print('GPU',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun');"
                    "print('RAM Go',round(psutil.virtual_memory().total/2**30,1))",
                ],
            ),
        ]
        self.log.clear()
        self.status.setText(
            "Installation ErisForge en cours. Son environnement est séparé d’IA Manager."
        )
        self.start_queue(steps, "install")

    def diagnostic(self):
        code = (
            "import torch,psutil;"
            "print('CUDA',torch.cuda.is_available());"
            "print('GPU',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun');"
            "print('VRAM Go',round(torch.cuda.get_device_properties(0).total_memory/2**30,1) if torch.cuda.is_available() else 0);"
            "print('RAM Go',round(psutil.virtual_memory().total/2**30,1))"
        )
        self.log.clear()
        self.start_queue([(str(_venv_python()), ["-c", code])], "diag")

    def validate_inputs(self):
        if not self.model.text().strip():
            raise ValueError("Renseignez le modèle.")
        for label, value in (
            ("comportement cible", self.objective.text().strip()),
            ("comportement de référence", self.reference.text().strip()),
        ):
            p = Path(value)
            if not p.is_file():
                raise ValueError(f"Fichier {label} introuvable.")
        if self.layer_end.value() < self.layer_start.value():
            raise ValueError("La dernière couche doit être ≥ à la première.")

    def make_job(self, action):
        self.validate_inputs()
        work = Path.home() / ".ia_manager" / "erisforge"
        work.mkdir(parents=True, exist_ok=True)
        name = _safe_name(self.output_name.text())
        direction = work / f"{name}-direction.pt"
        output = storage.app_models() / "ErisForge" / name

        if action == "transform" and output.exists() and any(output.iterdir()):
            raise ValueError("Le dossier de sortie existe déjà et n’est pas vide.")

        cfg = {
            "action": action,
            "model": self.model.text().strip(),
            "objective_file": self.objective.text().strip(),
            "reference_file": self.reference.text().strip(),
            "max_instructions": self.max_inst.value(),
            "batch_size": self.batch.value(),
            "layer_start": self.layer_start.value(),
            "layer_end": self.layer_end.value(),
            "strength": self.strength.value(),
            "intervention": self.intervention.currentData(),
            "seed": self.seed.value(),
            "direction_path": str(direction),
            "output": str(output),
        }
        cfg_path = work / f"{name}-{action}.json"
        cfg_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return cfg, cfg_path

    def reserve(self, label):
        if not local_jobs.enabled():
            return True
        self.token = local_jobs.reserve(label)
        return self.token is not None

    def measure(self):
        try:
            cfg, path = self.make_job("measure")
        except Exception as exc:
            self.status.setText(str(exc))
            return
        if not self.reserve("ErisForge direction"):
            self.status.setText("Un autre travail local utilise déjà les ressources.")
            return
        self.current_job = cfg
        self.direction_path = cfg["direction_path"]
        self.log.clear()
        self.status.setText(
            "Calcul de la direction comportementale ErisForge en cours…"
        )
        self.start_queue(
            [(str(_venv_python()), [str(_runner()), str(path)])],
            "measure",
        )

    def apply_transform(self):
        try:
            cfg, path = self.make_job("transform")
        except Exception as exc:
            self.status.setText(str(exc))
            return
        if not Path(cfg["direction_path"]).is_file():
            self.status.setText("Calculez d’abord la direction.")
            return
        if not self.reserve("ErisForge transformation"):
            self.status.setText("Un autre travail local utilise déjà les ressources.")
            return
        self.current_job = cfg
        self.last_output = cfg["output"]
        self.log.clear()
        self.status.setText(
            f"{self.intervention.currentText()} ErisForge en cours…"
        )
        self.start_queue(
            [(str(_venv_python()), [str(_runner()), str(path)])],
            "transform",
        )

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )

    def finished(self, code, status):
        self.read_output()
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit
        if ok and self.queue:
            self.next_step()
            return

        mode = self.mode
        self.mode = ""
        self.queue.clear()

        if mode in ("measure", "transform"):
            local_jobs.release(self.token)
            self.token = None

        if ok and mode == "install":
            self.status.setText("✅ ErisForge installé / réparé.")
        elif ok and mode == "diag":
            self.status.setText("✅ Diagnostic terminé.")
        elif ok and mode == "measure":
            self.status.setText("✅ Direction calculée : " + self.direction_path)
        elif ok and mode == "transform":
            self.status.setText("✅ Modèle ErisForge sauvegardé : " + self.last_output)
            rows = _history()
            item = dict(self.current_job)
            item["created"] = datetime.now().isoformat(timespec="seconds")
            rows.append(item)
            _save_history(rows)
        elif not ok:
            self.status.setText(f"❌ Échec ErisForge (code {code}). Consultez le journal.")

        self.refresh_state()
        self.set_busy(False)

    def failed(self, _error):
        if self.mode in ("measure", "transform"):
            local_jobs.release(self.token)
            self.token = None
        self.mode = ""
        self.queue.clear()
        self.status.setText("Démarrage impossible : " + self.process.errorString())
        self.refresh_state()
        self.set_busy(False)

    def stop(self):
        self.queue.clear()
        if self.busy():
            self.process.terminate()
            self.status.setText("Arrêt demandé…")

    def open_output(self):
        if self.last_output and Path(self.last_output).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output))

    def send_pipeline(self):
        output = Path(self.last_output)
        if not oe.valid_checkpoint(output):
            self.status.setText("La sortie n’est pas reconnue comme checkpoint complet.")
            return
        mk = getattr(self.window, "mergekit_tab", None)
        if mk is None or not hasattr(mk, "v133_source"):
            self.status.setText("Pipeline GGUF / Ollama indisponible.")
            return
        mk.v133_source.setText(str(output))
        mk.v133_name.setText(_safe_name(output.name.lower()))
        mk.v133_status.setText("✅ Sortie ErisForge prête pour GGUF / Ollama.")
        self.window.tabs.setCurrentWidget(mk)

    def shutdown(self):
        local_jobs.release(self.token)
        self.token = None
        if self.busy():
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)


def install_v145(window):
    if getattr(window, "_v145_erisforge", False):
        return
    tab = ErisForgeTab(window)
    window.erisforge_tab = tab

    lab = getattr(window, "abliteration_lab_tab", None)
    idx = window.tabs.indexOf(lab)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "⚒️ ErisForge")

    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(tab.shutdown)
    except Exception:
        pass

    window._v145_erisforge = True
