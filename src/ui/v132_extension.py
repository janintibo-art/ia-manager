"""Extension v132 : MergeKit Studio intégré à IA Manager."""
import json
import os
import re
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from src.backend import local_jobs, settings, storage
from src.backend import obliteratus as ob

MERGEKIT_REV = "9eeb539892c6753b032ea164e818b44a8c7a401b"
MERGEKIT_ARCHIVE = (
    "https://github.com/arcee-ai/mergekit/archive/"
    + MERGEKIT_REV
    + ".zip"
)

METHODS = (
    ("linear", "Linear · moyenne pondérée"),
    ("slerp", "SLERP · interpolation sphérique"),
    ("ties", "TIES · fusion avec réduction d’interférences"),
    ("dare_ties", "DARE-TIES · pruning + TIES"),
)


def _tool_root() -> Path:
    path = Path.home() / ".ia_manager" / "tools" / "mergekit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _venv_python() -> Path:
    root = _tool_root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _mergekit_exe() -> Path:
    root = _tool_root() / ".venv"
    if os.name == "nt":
        return root / "Scripts" / "mergekit-yaml.exe"
    return root / "bin" / "mergekit-yaml"


def _configs_root() -> Path:
    path = Path.home() / ".ia_manager" / "mergekit" / "configs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _outputs_root() -> Path:
    path = storage.app_models() / "Fusionnes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip(".-")
    return value[:80] or "fusion-mergekit"


def _yaml_str(value: str) -> str:
    # JSON strings are valid YAML scalars and safely escape Windows paths.
    return json.dumps(value, ensure_ascii=False)


def _build_config(model_a, model_b, method, weight_a, weight_b, density):
    if not model_a or not model_b:
        raise ValueError("Renseignez les deux modèles à fusionner.")
    if model_a == model_b:
        raise ValueError("Choisissez deux modèles différents.")

    lines = ["models:"]

    if method in {"ties", "dare_ties"}:
        lines += [
            f"  - model: {_yaml_str(model_a)}",
            "    parameters:",
            f"      weight: {weight_a:.4f}",
            f"      density: {density:.4f}",
            f"  - model: {_yaml_str(model_b)}",
            "    parameters:",
            f"      weight: {weight_b:.4f}",
            f"      density: {density:.4f}",
            f"merge_method: {method}",
            f"base_model: {_yaml_str(model_a)}",
            "parameters:",
            "  normalize: true",
            "  int8_mask: true",
        ]
    elif method == "slerp":
        total = max(weight_a + weight_b, 1e-9)
        t = weight_b / total
        lines += [
            f"  - model: {_yaml_str(model_a)}",
            f"  - model: {_yaml_str(model_b)}",
            "merge_method: slerp",
            f"base_model: {_yaml_str(model_a)}",
            "parameters:",
            f"  t: {t:.4f}",
        ]
    else:
        lines += [
            f"  - model: {_yaml_str(model_a)}",
            "    parameters:",
            f"      weight: {weight_a:.4f}",
            f"  - model: {_yaml_str(model_b)}",
            "    parameters:",
            f"      weight: {weight_b:.4f}",
            "merge_method: linear",
        ]

    lines += [
        "dtype: float16",
        "tokenizer:",
        '  source: "union"',
        'chat_template: "auto"',
        "",
    ]
    return "\n".join(lines)


class MergeKitStudio(QWidget):
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
        self.resource_token = None
        self.last_output = ""
        self.build_ui()
        self.refresh_state()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🧩 MergeKit Studio")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Fusionnez deux checkpoints Hugging Face compatibles pour combiner leurs "
            "caractéristiques. MergeKit fonctionne en local, sur CPU ou GPU, et peut "
            "travailler avec une mémoire limitée grâce au chargement progressif."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        install_box = QGroupBox("1 · Installation isolée")
        install_layout = QVBoxLayout(install_box)
        form = QFormLayout()
        default_python = str(
            settings.get("obliteratus_python")
            or getattr(getattr(self.window, "obliteratus_tab", None), "python", None).text()
            if getattr(getattr(self.window, "obliteratus_tab", None), "python", None)
            else ""
        )
        if not default_python:
            default_python = ob.default_python()
        self.python = QLineEdit(default_python)
        form.addRow("Python", self.python)
        install_layout.addLayout(form)

        row = QHBoxLayout()
        self.install_btn = QPushButton("Installer / réparer MergeKit")
        self.install_btn.clicked.connect(self.install_mergekit)
        row.addWidget(self.install_btn)
        self.detect_btn = QPushButton("Actualiser l’état")
        self.detect_btn.clicked.connect(self.refresh_state)
        row.addWidget(self.detect_btn)
        row.addStretch()
        install_layout.addLayout(row)

        self.install_status = QLabel()
        self.install_status.setWordWrap(True)
        install_layout.addWidget(self.install_status)
        root.addWidget(install_box)

        merge_box = QGroupBox("2 · Préparer la fusion")
        merge_layout = QVBoxLayout(merge_box)
        form = QFormLayout()

        self.model_a = QLineEdit()
        self.model_a.setPlaceholderText("Ex. Qwen/Qwen3-8B ou dossier local")
        form.addRow("Modèle A · base", self._path_row(self.model_a))

        self.model_b = QLineEdit()
        self.model_b.setPlaceholderText("Ex. autre checkpoint compatible")
        form.addRow("Modèle B", self._path_row(self.model_b))

        self.method = QComboBox()
        for key, label in METHODS:
            self.method.addItem(label, key)
        self.method.currentIndexChanged.connect(self.method_changed)
        form.addRow("Méthode", self.method)

        self.weight_a = QDoubleSpinBox()
        self.weight_a.setRange(-4.0, 4.0)
        self.weight_a.setSingleStep(0.05)
        self.weight_a.setValue(0.5)
        form.addRow("Poids A", self.weight_a)

        self.weight_b = QDoubleSpinBox()
        self.weight_b.setRange(-4.0, 4.0)
        self.weight_b.setSingleStep(0.05)
        self.weight_b.setValue(0.5)
        form.addRow("Poids B", self.weight_b)

        self.density = QDoubleSpinBox()
        self.density.setRange(0.01, 1.0)
        self.density.setSingleStep(0.05)
        self.density.setValue(0.5)
        form.addRow("Densité TIES / DARE", self.density)

        self.output_name = QLineEdit("fusion-mergekit")
        form.addRow("Nom de sortie", self.output_name)

        self.cuda = QCheckBox("Accélération CUDA")
        self.cuda.setToolTip(
            "Active --cuda. Laissez décoché pour une fusion CPU plus lente mais moins exigeante en VRAM."
        )
        form.addRow(self.cuda)

        merge_layout.addLayout(form)

        self.method_hint = QLabel()
        self.method_hint.setWordWrap(True)
        merge_layout.addWidget(self.method_hint)

        action_row = QHBoxLayout()
        self.preview_btn = QPushButton("👁 Voir le YAML")
        self.preview_btn.clicked.connect(self.preview_yaml)
        action_row.addWidget(self.preview_btn)
        self.run_btn = QPushButton("▶ Lancer la fusion")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self.run_merge)
        action_row.addWidget(self.run_btn)
        self.stop_btn = QPushButton("■ Arrêter")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(self.stop)
        action_row.addWidget(self.stop_btn)
        self.open_btn = QPushButton("📁 Ouvrir la dernière sortie")
        self.open_btn.clicked.connect(self.open_output)
        action_row.addWidget(self.open_btn)
        action_row.addStretch()
        merge_layout.addLayout(action_row)

        self.merge_status = QLabel(
            "Conseil : utilisez des modèles de même architecture et de taille compatible."
        )
        self.merge_status.setWordWrap(True)
        merge_layout.addWidget(self.merge_status)
        root.addWidget(merge_box)

        root.addWidget(QLabel("3 · Journal"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        root.addWidget(self.log, 1)

        self.method_changed()

    def _path_row(self, edit):
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit, 1)
        button = QPushButton("Dossier…")
        button.clicked.connect(lambda: self.choose_model_dir(edit))
        row.addWidget(button)
        return box

    def choose_model_dir(self, edit):
        path = QFileDialog.getExistingDirectory(
            self, "Choisir un checkpoint Hugging Face", str(storage.app_models())
        )
        if path:
            edit.setText(path)

    def method_changed(self):
        method = self.method.currentData()
        self.density.setEnabled(method in {"ties", "dare_ties"})
        hints = {
            "linear": "Linear : moyenne pondérée simple, idéale pour deux checkpoints proches.",
            "slerp": "SLERP : interpolation sphérique entre deux modèles. Le poids B détermine la position entre A et B.",
            "ties": "TIES : fusion de task vectors avec réduction des conflits de signe. Le modèle A sert de base.",
            "dare_ties": "DARE‑TIES : ajoute un pruning aléatoire avant TIES pour limiter les interférences.",
        }
        self.method_hint.setText(hints.get(method, ""))

    def refresh_state(self):
        ready = _venv_python().is_file() and _mergekit_exe().is_file()
        if ready:
            self.install_status.setText(
                "✅ MergeKit installé dans un environnement Python isolé · "
                + str(_tool_root())
            )
        else:
            self.install_status.setText(
                "MergeKit n’est pas encore installé. L’installation reste séparée de l’environnement principal d’IA Manager."
            )
        self.update_buttons()

    def update_buttons(self):
        busy = self.process.state() != QProcess.ProcessState.NotRunning
        ready = _venv_python().is_file() and _mergekit_exe().is_file()
        self.install_btn.setEnabled(not busy)
        self.detect_btn.setEnabled(not busy)
        self.preview_btn.setEnabled(not busy)
        self.run_btn.setEnabled(not busy and ready)
        self.stop_btn.setEnabled(busy)
        self.open_btn.setEnabled(bool(self.last_output) and Path(self.last_output).is_dir())
        for widget in (
            self.python, self.model_a, self.model_b, self.method,
            self.weight_a, self.weight_b, self.density, self.output_name, self.cuda,
        ):
            widget.setEnabled(not busy)

    def install_mergekit(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        python = Path(self.python.text().strip()).expanduser()
        if not python.is_file():
            self.install_status.setText(
                "Python introuvable. Utilisez le même Python que dans l’onglet Obliteratus ou choisissez python.exe."
            )
            return

        root = _tool_root()
        venv = root / ".venv"
        vp = _venv_python()

        steps = []
        if not vp.is_file():
            steps.append((str(python), ["-m", "venv", str(venv)]))
        steps += [
            (str(vp), ["-m", "pip", "install", "--upgrade", "pip"]),
            (str(vp), ["-m", "pip", "install", "--upgrade", MERGEKIT_ARCHIVE]),
        ]
        self.log.clear()
        self.install_status.setText("Installation de MergeKit en cours…")
        self.start_queue(steps, "install")

    def preview_yaml(self):
        try:
            yaml = self.current_yaml()
        except Exception as exc:
            self.merge_status.setText(str(exc))
            return
        self.log.setPlainText(yaml)
        self.merge_status.setText("Configuration YAML générée. Elle sera sauvegardée automatiquement au lancement.")

    def current_yaml(self):
        return _build_config(
            self.model_a.text().strip(),
            self.model_b.text().strip(),
            self.method.currentData(),
            self.weight_a.value(),
            self.weight_b.value(),
            self.density.value(),
        )

    def run_merge(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if not _mergekit_exe().is_file():
            self.merge_status.setText("Installez MergeKit avant de lancer une fusion.")
            return
        try:
            yaml = self.current_yaml()
        except Exception as exc:
            self.merge_status.setText(str(exc))
            return

        name = _safe_name(self.output_name.text())
        output = _outputs_root() / name
        if output.exists() and any(output.iterdir()):
            QMessageBox.warning(
                self, "Dossier déjà utilisé",
                "Le dossier de sortie existe déjà et n’est pas vide. Choisissez un autre nom pour préserver la fusion précédente."
            )
            return

        output.mkdir(parents=True, exist_ok=True)
        config = _configs_root() / f"{name}.yml"
        config.write_text(yaml, encoding="utf-8")

        args = [str(config), str(output), "--lazy-unpickle"]
        if self.cuda.isChecked():
            args.append("--cuda")

        self.last_output = str(output)
        self.log.clear()
        self.merge_status.setText(
            "Fusion en cours · le premier chargement peut télécharger plusieurs gigaoctets depuis Hugging Face."
        )
        self.start_queue([(str(_mergekit_exe()), args)], "merge")

    def start_queue(self, steps, mode):
        if local_jobs.enabled():
            self.resource_token = local_jobs.reserve("MergeKit " + mode)
            if self.resource_token is None:
                target = self.install_status if mode == "install" else self.merge_status
                target.setText("Un autre travail local utilise déjà les ressources. Attendez sa fin.")
                return
        self.queue = list(steps)
        self.mode = mode
        self.update_buttons()
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
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(_tool_root()))
        self.process.start(program, args)

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if text:
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(text)

    def finished(self, code, exit_status):
        self.read_output()
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if ok and self.queue:
            self.next_step()
            return

        local_jobs.release(self.resource_token)
        self.resource_token = None
        mode = self.mode
        self.mode = ""
        self.queue.clear()

        if ok and mode == "install":
            self.install_status.setText("✅ MergeKit installé / réparé.")
        elif ok and mode == "merge":
            self.merge_status.setText(
                "✅ Fusion terminée. Le résultat Hugging Face est prêt dans : " + self.last_output
            )
        else:
            target = self.install_status if mode == "install" else self.merge_status
            target.setText(f"❌ Échec MergeKit (code {code}). Consultez le journal.")
        self.refresh_state()

    def failed(self, _error):
        local_jobs.release(self.resource_token)
        self.resource_token = None
        target = self.install_status if self.mode == "install" else self.merge_status
        target.setText("Démarrage impossible : " + self.process.errorString())
        self.mode = ""
        self.queue.clear()
        self.update_buttons()

    def stop(self):
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.queue.clear()
        self.process.terminate()
        self.merge_status.setText("Arrêt demandé…")

    def open_output(self):
        if self.last_output and Path(self.last_output).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output))

    def shutdown(self):
        self.queue.clear()
        local_jobs.release(self.resource_token)
        self.resource_token = None
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1500)


def install_v132(window):
    if getattr(window, "_v132_mergekit", False):
        return

    tab = MergeKitStudio(window)
    window.mergekit_tab = tab

    obl_index = window.tabs.indexOf(getattr(window, "obliteratus_tab", None))
    insert_at = obl_index + 1 if obl_index >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "🧩 MergeKit")

    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(tab.shutdown)

    window._v132_mergekit = True
