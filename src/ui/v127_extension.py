"""Extension v127 : préparation locale automatique des sources Hugging Face pour Obliteratus."""
from pathlib import Path
from types import MethodType
import re

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from src.backend import local_jobs, storage
from src.backend import obliteratus as ob


def _safe_repo_dir(repo_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "--", (repo_id or "").strip())
    return value.strip(".-") or "modele"


def source_root() -> Path:
    path = storage.app_models() / "HuggingFace"
    path.mkdir(parents=True, exist_ok=True)
    return path


def local_source_for(repo_id: str) -> Path:
    return source_root() / _safe_repo_dir(repo_id)


def _looks_local(value: str) -> bool:
    try:
        return Path(value).expanduser().is_dir()
    except (OSError, ValueError):
        return False


def _checkpoint_ready(path: Path) -> bool:
    if not path.is_dir():
        return False
    config = path / "config.json"
    tokenizer = path / "tokenizer_config.json"
    weights = list(path.glob("*.safetensors"))
    indexed = list(path.glob("*.safetensors.index.json"))
    return config.is_file() and tokenizer.is_file() and bool(weights or indexed)


def _download_command(repo_id: str, destination: Path):
    python = ob.environment_python()
    if not python.is_file():
        raise ValueError("Installez d'abord Obliteratus : son environnement fournit huggingface_hub.")
    code = (
        "from huggingface_hub import snapshot_download;"
        "import sys;"
        "p=snapshot_download(repo_id=sys.argv[1],local_dir=sys.argv[2],"
        "local_dir_use_symlinks=False,resume_download=True);"
        "print('IA_MANAGER_SOURCE_READY='+str(p), flush=True)"
    )
    return str(python), ["-u", "-c", code, repo_id, str(destination)]


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if value < 1024 or unit == "To":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} o"


def install_v127(window):
    tab = getattr(window, "obliteratus_tab", None)
    if tab is None or not hasattr(tab, "v126_source") or getattr(window, "_v127_obliteratus", False):
        return

    # Ajouter les contrôles dans le bloc natif de v126, juste sous le champ source.
    parent_layout = tab.v126_source.parentWidget().layout()
    source_tools = QHBoxLayout()
    tab.v127_prepare = QPushButton("⬇ Préparer / télécharger la source HF")
    tab.v127_prepare.setToolTip(
        "Télécharge le checkpoint Hugging Face complet dans le stockage IA Manager, "
        "puis l'utilise localement dans Obliteratus."
    )
    source_tools.addWidget(tab.v127_prepare)

    tab.v127_open = QPushButton("📁 Ouvrir la source")
    tab.v127_open.setEnabled(False)
    source_tools.addWidget(tab.v127_open)
    source_tools.addStretch()

    tab.v127_info = QLabel("Source distante · non préparée localement.")
    tab.v127_info.setWordWrap(True)

    # Le QFormLayout est le parent direct du champ source dans v126.
    try:
        form = tab.v126_source.parentWidget().layout()
        if hasattr(form, "addRow"):
            form.addRow("", source_tools)
            form.addRow("État source", tab.v127_info)
        else:
            tab.layout().insertLayout(3, source_tools)
            tab.layout().insertWidget(4, tab.v127_info)
    except Exception:
        tab.layout().insertLayout(3, source_tools)
        tab.layout().insertWidget(4, tab.v127_info)

    tab.v127_process = QProcess(tab)
    tab.v127_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v127_resource_token = None
    tab.v127_repo_id = ""
    tab.v127_local_path = ""
    tab.v127_output_buffer = ""

    def v127_set_busy(self, busy):
        self.v127_prepare.setEnabled(not busy)
        self.v127_open.setEnabled(not busy and bool(self.v127_local_path) and Path(self.v127_local_path).is_dir())
        self.v126_run.setEnabled(not busy and self.v126_process.state() == QProcess.ProcessState.NotRunning)
        self.v126_source.setEnabled(not busy)
        if busy:
            self.v127_info.setText("⏳ Téléchargement/préparation de la source en cours…")
        else:
            v127_refresh_source_state(self)

    def v127_refresh_source_state(self):
        value = self.v126_source.text().strip()
        if not value:
            self.v127_repo_id = ""
            self.v127_local_path = ""
            self.v127_info.setText("Aucune source sélectionnée.")
            self.v127_open.setEnabled(False)
            return

        if _looks_local(value):
            path = Path(value).expanduser()
            self.v127_local_path = str(path)
            size = _dir_size(path)
            ready = _checkpoint_ready(path)
            if ready:
                self.v127_info.setText(f"✅ Checkpoint local prêt · {_human_size(size)} · {path}")
            else:
                self.v127_info.setText(f"⚠️ Dossier local détecté mais checkpoint incomplet · {path}")
            self.v127_open.setEnabled(path.is_dir())
            return

        self.v127_repo_id = value
        candidate = local_source_for(value)
        if _checkpoint_ready(candidate):
            self.v127_local_path = str(candidate)
            size = _dir_size(candidate)
            self.v127_info.setText(
                f"✅ Source déjà téléchargée · {_human_size(size)} · cliquez sur Préparer pour l'utiliser localement."
            )
            self.v127_open.setEnabled(True)
        else:
            self.v127_local_path = ""
            self.v127_info.setText(
                f"☁️ Source Hugging Face : {value} · sera stockée dans {candidate}"
            )
            self.v127_open.setEnabled(False)

    def v127_read_output(self):
        text = bytes(self.v127_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not text:
            return
        self.v127_output_buffer += text
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)

    def v127_prepare_source(self):
        if self.v127_process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.v126_process.state() != QProcess.ProcessState.NotRunning or self.mode or self.detecting:
            self.v127_info.setText("Une autre opération locale est déjà en cours.")
            return

        value = self.v126_source.text().strip()
        if not value:
            self.v127_info.setText("Choisissez d'abord un modèle source.")
            return

        if _looks_local(value):
            v127_refresh_source_state(self)
            if _checkpoint_ready(Path(value).expanduser()):
                self.v127_info.setText("✅ Cette source est déjà locale et prête pour Obliteratus.")
            return

        repo_id = value
        destination = local_source_for(repo_id)
        if _checkpoint_ready(destination):
            self.v127_repo_id = repo_id
            self.v127_local_path = str(destination)
            self.v126_source.setText(str(destination))
            self.v127_info.setText("✅ Source locale réutilisée, aucun téléchargement nécessaire.")
            self.v127_open.setEnabled(True)
            return

        try:
            program, args = _download_command(repo_id, destination)
        except Exception as exc:
            self.v127_info.setText(str(exc))
            return

        if local_jobs.enabled():
            self.v127_resource_token = local_jobs.reserve("Téléchargement source Hugging Face")
            if self.v127_resource_token is None:
                self.v127_info.setText("Un autre travail local utilise déjà les ressources.")
                return

        destination.mkdir(parents=True, exist_ok=True)
        self.v127_repo_id = repo_id
        self.v127_local_path = str(destination)
        self.v127_output_buffer = ""
        self.log.clear()

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        self.v127_process.setProcessEnvironment(env)
        self.v127_process.setWorkingDirectory(str(source_root()))
        v127_set_busy(self, True)
        self.v127_process.start(program, args)

    def v127_finished(self, code, exit_status):
        v127_read_output(self)
        local_jobs.release(self.v127_resource_token)
        self.v127_resource_token = None
        ok = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        path = Path(self.v127_local_path) if self.v127_local_path else None
        if ok and path and _checkpoint_ready(path):
            self.v126_source.setText(str(path))
            self.v127_info.setText(
                f"✅ Source prête · {_human_size(_dir_size(path))} · Obliteratus utilisera désormais ce checkpoint local."
            )
            self.v126_status.setText(
                "✅ Checkpoint Hugging Face préparé localement. Vous pouvez lancer Obliteratus."
            )
        else:
            self.v127_info.setText(
                "❌ Préparation incomplète. Consultez le journal. "
                "Un modèle privé/gated peut nécessiter une connexion Hugging Face préalable."
            )
        v127_set_busy(self, False)

    def v127_failed(self, _error):
        local_jobs.release(self.v127_resource_token)
        self.v127_resource_token = None
        self.v127_info.setText("Démarrage impossible : " + self.v127_process.errorString())
        v127_set_busy(self, False)

    def v127_open_source(self):
        if self.v127_local_path and Path(self.v127_local_path).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.v127_local_path))

    tab.v127_set_busy = MethodType(v127_set_busy, tab)
    tab.v127_refresh_source_state = MethodType(v127_refresh_source_state, tab)
    tab.v127_read_output = MethodType(v127_read_output, tab)
    tab.v127_prepare_source = MethodType(v127_prepare_source, tab)
    tab.v127_finished = MethodType(v127_finished, tab)
    tab.v127_failed = MethodType(v127_failed, tab)
    tab.v127_open_source = MethodType(v127_open_source, tab)

    tab.v127_process.readyReadStandardOutput.connect(tab.v127_read_output)
    tab.v127_process.finished.connect(tab.v127_finished)
    tab.v127_process.errorOccurred.connect(tab.v127_failed)
    tab.v127_prepare.clicked.connect(tab.v127_prepare_source)
    tab.v127_open.clicked.connect(tab.v127_open_source)
    tab.v126_source.textChanged.connect(tab.v127_refresh_source_state)

    # Quand v126 reçoit un modèle depuis le catalogue, rafraîchir immédiatement l'état.
    old_select = tab.v126_select_source

    def v126_select_source(self, model_id):
        old_select(model_id)
        self.v127_refresh_source_state()

    tab.v126_select_source = MethodType(v126_select_source, tab)

    # Arrêt propre à la fermeture.
    old_shutdown = tab.shutdown

    def shutdown(self):
        if self.v127_process.state() != QProcess.ProcessState.NotRunning:
            self.v127_process.terminate()
            if not self.v127_process.waitForFinished(1500):
                self.v127_process.kill()
                self.v127_process.waitForFinished(1500)
        local_jobs.release(self.v127_resource_token)
        self.v127_resource_token = None
        old_shutdown()

    tab.shutdown = MethodType(shutdown, tab)
    tab.v127_refresh_source_state()
    window._v127_obliteratus = True
