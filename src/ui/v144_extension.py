"""Extension v144 : Abliteration Lab (projected / norm-preserving)."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QDoubleSpinBox,
    QVBoxLayout, QWidget,
)

from src.backend import local_jobs, settings, storage
from src.backend import obliteratus as ob
from src.backend import obliteratus_export as oe

LAB_REV = "ca6e223843f3aec83b47a0926f5b4c78859c120b"
LAB_ARCHIVE = f"https://github.com/jim-plus/llm-abliteration/archive/{LAB_REV}.zip"


def _tool_root():
    p = Path.home() / ".ia_manager" / "tools" / "llm-abliteration"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _source_root():
    return _tool_root() / "source"


def _venv_python():
    root = _tool_root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _default_python():
    for value in (
        settings.get("training_python"),
        settings.get("obliteratus_python"),
        ob.default_python(),
    ):
        if value and Path(str(value)).expanduser().is_file():
            return str(Path(str(value)).expanduser())
    return ""


def _safe_name(text):
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", (text or "").strip()).strip(".-")
    return text[:96] or "abliterated-model"


def _runs_file():
    p = Path.home() / ".ia_manager" / "abliteration_lab_runs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_runs():
    try:
        value = json.loads(_runs_file().read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save_runs(rows):
    _runs_file().write_text(
        json.dumps(rows[-200:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class AbliterationLab(QWidget):
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
        self.measurement = ""
        self.last_output = ""
        self.build_ui()
        self.refresh_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🧬 Abliteration Lab")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Laboratoire pour comparer plusieurs variantes d’abliteration : conventionnelle, "
            "projected, biprojected et norm-preserving. Le modèle source est toujours conservé."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        install = QGroupBox("1 · Moteur")
        il = QVBoxLayout(install)
        form = QFormLayout()
        self.python = QLineEdit(_default_python())
        self.python.setPlaceholderText("Python 3.11+")
        form.addRow("Python de base", self.python)
        il.addLayout(form)

        row = QHBoxLayout()
        self.install_btn = QPushButton("Installer / réparer le laboratoire")
        row.addWidget(self.install_btn)
        self.diag_btn = QPushButton("Diagnostic CUDA")
        row.addWidget(self.diag_btn)
        self.open_tool_btn = QPushButton("📁 Dossier moteur")
        row.addWidget(self.open_tool_btn)
        row.addStretch()
        il.addLayout(row)

        self.engine_status = QLabel()
        self.engine_status.setWordWrap(True)
        il.addWidget(self.engine_status)
        root.addWidget(install)

        source = QGroupBox("2 · Modèle et méthode")
        sl = QVBoxLayout(source)
        form = QFormLayout()

        self.model = QLineEdit()
        self.model.setPlaceholderText("Identifiant Hugging Face ou dossier local")
        form.addRow("Modèle source", self.model)

        self.method = QComboBox()
        self.method.addItem("Conventionnelle", "classic")
        self.method.addItem("Projected", "projected")
        self.method.addItem("Biprojected", "biprojected")
        self.method.addItem("Norm-preserving biprojected / MPOA", "mpoa")
        self.method.setCurrentIndex(3)
        form.addRow("Méthode", self.method)

        self.quant_measure = QCheckBox("Mesure en 4 bits")
        self.quant_measure.setChecked(True)
        form.addRow(self.quant_measure)

        self.batch = QComboBox()
        for v in (1, 2, 4, 8, 16, 32):
            self.batch.addItem(str(v), v)
        self.batch.setCurrentIndex(2)
        form.addRow("Batch mesure", self.batch)

        sl.addLayout(form)
        row = QHBoxLayout()
        self.pick_model = QPushButton("Dossier local…")
        row.addWidget(self.pick_model)
        self.inspect_btn = QPushButton("🔎 Lire config.json")
        row.addWidget(self.inspect_btn)
        row.addStretch()
        sl.addLayout(row)
        root.addWidget(source)

        layers = QGroupBox("3 · Couches ciblées")
        ll = QVBoxLayout(layers)
        form = QFormLayout()

        self.layer_start = QSpinBox()
        self.layer_start.setRange(0, 255)
        self.layer_start.setValue(10)
        form.addRow("Première couche", self.layer_start)

        self.layer_end = QSpinBox()
        self.layer_end.setRange(0, 255)
        self.layer_end.setValue(20)
        form.addRow("Dernière couche", self.layer_end)

        self.measure_layer = QSpinBox()
        self.measure_layer.setRange(0, 255)
        self.measure_layer.setValue(15)
        form.addRow("Direction mesurée sur", self.measure_layer)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.0, 3.0)
        self.scale.setDecimals(2)
        self.scale.setSingleStep(0.05)
        self.scale.setValue(1.0)
        form.addRow("Force", self.scale)

        self.output_name = QLineEdit("modele-mpoa")
        form.addRow("Nom de sortie", self.output_name)

        ll.addLayout(form)

        self.layer_hint = QLabel(
            "Les couches sont réglables manuellement. Le bouton config propose une plage heuristique "
            "au milieu / fin du réseau ; elle reste à vérifier avec vos mesures."
        )
        self.layer_hint.setWordWrap(True)
        ll.addWidget(self.layer_hint)
        root.addWidget(layers)

        actions = QHBoxLayout()
        self.measure_btn = QPushButton("① Mesurer les directions")
        self.measure_btn.setObjectName("Primary")
        actions.addWidget(self.measure_btn)

        self.ablate_btn = QPushButton("② Appliquer l’intervention")
        self.ablate_btn.setObjectName("Primary")
        self.ablate_btn.setEnabled(False)
        actions.addWidget(self.ablate_btn)

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
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(_tool_root())))
        )
        self.pick_model.clicked.connect(self.choose_model)
        self.inspect_btn.clicked.connect(self.inspect_config)
        self.method.currentIndexChanged.connect(self.describe_method)
        self.measure_btn.clicked.connect(self.measure)
        self.ablate_btn.clicked.connect(self.ablate)
        self.stop_btn.clicked.connect(self.stop)
        self.open_output_btn.clicked.connect(self.open_output)
        self.pipeline_btn.clicked.connect(self.send_pipeline)
        self.describe_method()

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def refresh_state(self):
        ready = (
            _venv_python().is_file()
            and (_source_root() / "measure.py").is_file()
            and (_source_root() / "sharded_ablate.py").is_file()
        )
        self.engine_status.setText(
            "✅ Laboratoire installé." if ready
            else "Le moteur llm-abliteration n’est pas encore installé."
        )
        self.measure_btn.setEnabled(ready and not self.busy())
        self.diag_btn.setEnabled(ready and not self.busy())

    def set_busy(self, busy):
        for w in (
            self.install_btn, self.diag_btn, self.python, self.model, self.pick_model,
            self.inspect_btn, self.method, self.quant_measure, self.batch,
            self.layer_start, self.layer_end, self.measure_layer, self.scale,
            self.output_name,
        ):
            w.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.measure_btn.setEnabled(
            not busy and (_source_root() / "measure.py").is_file()
        )
        self.ablate_btn.setEnabled(
            not busy and bool(self.measurement) and Path(self.measurement).is_file()
        )
        self.open_output_btn.setEnabled(
            not busy and bool(self.last_output) and Path(self.last_output).exists()
        )
        self.pipeline_btn.setEnabled(
            not busy and bool(self.last_output)
            and oe.valid_checkpoint(Path(self.last_output))
        )

    def describe_method(self):
        desc = {
            "classic": "Abliteration conventionnelle : direction harmful − harmless.",
            "projected": "Projected : retire de la direction de refus sa composante alignée avec la direction harmless.",
            "biprojected": "Biprojected : projection pendant la mesure et nouvelle orthogonalisation lors de l’intervention.",
            "mpoa": "Norm-preserving biprojected : biprojection + préservation des normes des poids modifiés.",
        }
        self.status.setText(desc.get(self.method.currentData(), ""))

    def choose_model(self):
        p = QFileDialog.getExistingDirectory(self, "Choisir un modèle local")
        if p:
            self.model.setText(p)
            self.output_name.setText(_safe_name(Path(p).name + "-mpoa"))

    def inspect_config(self):
        value = self.model.text().strip()
        if not value:
            self.status.setText("Choisissez d’abord un modèle local.")
            return
        p = Path(value) / "config.json"
        if not p.is_file():
            self.status.setText(
                "Pour l’estimation automatique des couches, choisissez un dossier local contenant config.json."
            )
            return
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            n = int(
                cfg.get("num_hidden_layers")
                or (cfg.get("text_config") or {}).get("num_hidden_layers")
            )
        except Exception as exc:
            self.status.setText("Lecture config impossible : " + str(exc))
            return

        start = max(0, int(n * 0.40))
        end = max(start, min(n - 1, int(n * 0.70)))
        measure = max(start, min(end, int(n * 0.55)))
        self.layer_start.setValue(start)
        self.layer_end.setValue(end)
        self.measure_layer.setValue(measure)
        self.layer_hint.setText(
            f"{n} couches détectées · suggestion heuristique {start} → {end}, "
            f"direction couche {measure}. Vérifiez-la avec vos mesures."
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
        program, args, cwd = self.queue.pop(0)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("TOKENIZERS_PARALLELISM", "false")
        env.insert("PYTORCH_ALLOC_CONF", "expandable_segments:True")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(cwd))
        self.process.start(str(program), list(args))

    def install_tool(self):
        base = Path(self.python.text().strip()).expanduser()
        if not base.is_file():
            self.status.setText("Choisissez un véritable exécutable Python.")
            return

        venv = _tool_root() / ".venv"
        vp = _venv_python()
        source = _source_root()

        fetch_code = (
            "import io,urllib.request,zipfile,shutil,pathlib;"
            f"url={LAB_ARCHIVE!r};"
            f"dst=pathlib.Path({str(source)!r});"
            "shutil.rmtree(dst,ignore_errors=True);dst.mkdir(parents=True,exist_ok=True);"
            "data=urllib.request.urlopen(url,timeout=120).read();"
            "z=zipfile.ZipFile(io.BytesIO(data));"
            "names=z.namelist();root=names[0].split('/')[0]+'/';"
            "[(lambda rel,b: ((dst/rel).parent.mkdir(parents=True,exist_ok=True),(dst/rel).write_bytes(b)))"
            "(n[len(root):],z.read(n)) for n in names if n.startswith(root) and n!=root and not n.endswith('/')];"
            "print('Source installé',dst)"
        )

        steps = []
        if not vp.is_file():
            steps.append((str(base), ["-m", "venv", str(venv)], _tool_root()))
        steps += [
            (str(vp), ["-m", "pip", "install", "--upgrade", "pip", "wheel"], _tool_root()),
            (str(vp), ["-c", fetch_code], _tool_root()),
            (
                str(vp),
                ["-m", "pip", "install", "-r", str(source / "requirements.txt")],
                _tool_root(),
            ),
            (
                str(vp),
                ["-c", "import torch,transformers; print('Torch',torch.__version__); print('CUDA',torch.cuda.is_available()); print('GPU',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun')"],
                _tool_root(),
            ),
        ]
        self.log.clear()
        self.status.setText("Installation du laboratoire en cours…")
        self.start_queue(steps, "install")

    def diagnostic(self):
        py = _venv_python()
        if not py.is_file():
            return
        code = (
            "import torch,psutil;"
            "print('CUDA',torch.cuda.is_available());"
            "print('GPU',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun');"
            "print('VRAM Go',round(torch.cuda.get_device_properties(0).total_memory/2**30,1) if torch.cuda.is_available() else 0);"
            "print('RAM Go',round(psutil.virtual_memory().total/2**30,1))"
        )
        self.log.clear()
        self.start_queue([(str(py), ["-c", code], _source_root())], "diag")

    def reserve(self, label):
        if not local_jobs.enabled():
            return True
        self.token = local_jobs.reserve(label)
        return self.token is not None

    def measure(self):
        model = self.model.text().strip()
        if not model:
            self.status.setText("Renseignez un modèle source.")
            return
        if not self.reserve("Abliteration Lab mesure"):
            self.status.setText("Un autre travail local utilise déjà les ressources.")
            return

        work = Path.home() / ".ia_manager" / "abliteration_lab"
        work.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        measurement = work / f"measure-{stamp}.pt"

        args = [
            str(_source_root() / "measure.py"),
            "-m", model,
            "-o", str(measurement),
            "--batch-size", str(self.batch.currentData()),
        ]
        if self.quant_measure.isChecked():
            args += ["--quant-measure", "4bit"]
        if self.method.currentData() in ("projected", "biprojected", "mpoa"):
            args.append("--projected")

        self.measurement = str(measurement)
        self.log.clear()
        self.status.setText("Mesure des directions en cours…")
        self.start_queue([(str(_venv_python()), args, _source_root())], "measure")

    def make_yaml(self, output):
        start = self.layer_start.value()
        end = self.layer_end.value()
        if end < start:
            raise ValueError("La dernière couche doit être ≥ à la première.")
        m = self.measure_layer.value()
        scale = self.scale.value()
        lines = [
            f"model: {json.dumps(self.model.text().strip(), ensure_ascii=False)}",
            f"measurements: {json.dumps(self.measurement, ensure_ascii=False)}",
            f"output: {json.dumps(str(output), ensure_ascii=False)}",
            f"scale: {scale}",
            "ablate:",
        ]
        for layer in range(start, end + 1):
            lines += [
                f"  - layer: {layer}",
                f"    measurement: {m}",
                "    scale: 1.0",
                "    sparsity: 0.0",
            ]
        return "\n".join(lines) + "\n"

    def ablate(self):
        if not self.measurement or not Path(self.measurement).is_file():
            self.status.setText("Mesurez d’abord les directions.")
            return
        if not self.reserve("Abliteration Lab intervention"):
            self.status.setText("Un autre travail local utilise déjà les ressources.")
            return

        name = _safe_name(self.output_name.text())
        output = storage.app_models() / "AbliterationLab" / name
        if output.exists() and any(output.iterdir()):
            local_jobs.release(self.token)
            self.token = None
            self.status.setText("Le dossier de sortie existe déjà et n’est pas vide.")
            return
        output.mkdir(parents=True, exist_ok=True)

        cfg_dir = Path.home() / ".ia_manager" / "abliteration_lab" / "configs"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = cfg_dir / f"{name}.yml"
        try:
            cfg.write_text(self.make_yaml(output), encoding="utf-8")
        except Exception as exc:
            local_jobs.release(self.token)
            self.token = None
            self.status.setText(str(exc))
            return

        args = [str(_source_root() / "sharded_ablate.py"), str(cfg)]
        method = self.method.currentData()
        if method in ("biprojected", "mpoa"):
            args.append("--projected")
        if method == "mpoa":
            args.append("--normpreserve")

        self.last_output = str(output)
        self.log.clear()
        self.status.setText(
            f"Intervention {self.method.currentText()} en cours…"
        )
        self.start_queue([(str(_venv_python()), args, _source_root())], "ablate")

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)
            self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def finished(self, code, status):
        self.read_output()
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit

        if ok and self.queue:
            self.next_step()
            return

        mode = self.mode
        self.mode = ""
        self.queue.clear()

        if mode in ("measure", "ablate"):
            local_jobs.release(self.token)
            self.token = None

        if ok and mode == "install":
            self.status.setText("✅ Abliteration Lab installé.")
        elif ok and mode == "diag":
            self.status.setText("✅ Diagnostic terminé.")
        elif ok and mode == "measure":
            self.status.setText("✅ Mesures enregistrées : " + self.measurement)
        elif ok and mode == "ablate":
            self.status.setText("✅ Modèle modifié : " + self.last_output)
            rows = _load_runs()
            rows.append({
                "created": datetime.now().isoformat(timespec="seconds"),
                "source": self.model.text().strip(),
                "method": self.method.currentData(),
                "measurement": self.measurement,
                "output": self.last_output,
                "layer_start": self.layer_start.value(),
                "layer_end": self.layer_end.value(),
                "measurement_layer": self.measure_layer.value(),
                "scale": self.scale.value(),
            })
            _save_runs(rows)
        else:
            if not ok:
                self.status.setText(f"❌ Échec (code {code}). Consultez le journal.")

        self.refresh_state()
        self.set_busy(False)

    def failed(self, _error):
        if self.mode in ("measure", "ablate"):
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
        if not self.last_output:
            return
        output = Path(self.last_output)
        if not oe.valid_checkpoint(output):
            self.status.setText("La sortie n’est pas encore reconnue comme checkpoint complet.")
            return
        mk = getattr(self.window, "mergekit_tab", None)
        if mk is None or not hasattr(mk, "v133_source"):
            self.status.setText("Pipeline GGUF / Ollama indisponible.")
            return
        mk.v133_source.setText(str(output))
        mk.v133_name.setText(_safe_name(output.name.lower()))
        mk.v133_status.setText("✅ Sortie Abliteration Lab prête pour GGUF / Ollama.")
        self.window.tabs.setCurrentWidget(mk)

    def shutdown(self):
        local_jobs.release(self.token)
        self.token = None
        if self.busy():
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)


def install_v144(window):
    if getattr(window, "_v144_abliteration_lab", False):
        return
    tab = AbliterationLab(window)
    window.abliteration_lab_tab = tab

    heretic = getattr(window, "heretic_tab", None)
    idx = window.tabs.indexOf(heretic)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "🧬 Abliteration Lab")

    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(tab.shutdown)
    except Exception:
        pass

    window._v144_abliteration_lab = True
