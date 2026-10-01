"""v181 : installation isolée Audio / Voix avancés."""
from __future__ import annotations

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QPlainTextEdit, QMessageBox,
)

from src.backend import audio_voice_installer as backend


class AudioVoiceInstallTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = None
        self.steps = []
        self.mode = ""

        root = QVBoxLayout(self)
        title = QLabel("Audio & Voix avancés")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Installation locale et isolée de Stable Audio Open, Whisper large-v3, Kokoro et XTTS-v2. "
            "Chaque moteur possède son propre environnement Python afin d'éviter les conflits."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.model = QComboBox()
        for mid, spec in backend.SPECS.items():
            self.model.addItem(spec["name"], mid)
        self.model.currentIndexChanged.connect(self.refresh)
        root.addWidget(self.model)

        self.info = QLabel()
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        row = QHBoxLayout()
        self.install = QPushButton("1 · Installer / réparer le moteur")
        self.install.setObjectName("Primary")
        self.weights = QPushButton("2 · Précharger les poids")
        self.verify = QPushButton("🔎 Vérifier")
        self.folder = QPushButton("📁 Ouvrir le dossier")
        row.addWidget(self.install)
        row.addWidget(self.weights)
        row.addWidget(self.verify)
        row.addWidget(self.folder)
        row.addStretch(1)
        root.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1800)
        root.addWidget(self.log, 1)

        self.install.clicked.connect(self.install_engine)
        self.weights.clicked.connect(self.preload)
        self.verify.clicked.connect(self.refresh)
        self.folder.clicked.connect(self.open_folder)
        self.refresh()

    def mid(self):
        return str(self.model.currentData() or "")

    def refresh(self):
        st = backend.state(self.mid())
        spec = backend.spec_for(self.mid())
        if not spec:
            return
        self.info.setText("<b>" + spec["name"] + "</b><br>" + spec["note"])
        busy = self.process is not None
        self.install.setEnabled(not busy)
        self.weights.setEnabled(not busy and st.get("installed", False))
        self.verify.setEnabled(not busy)
        self.folder.setEnabled(bool(st.get("base")))

        if st.get("ready"):
            self.status.setText("✅ Moteur installé et poids prêts.")
        elif st.get("installed"):
            if st.get("gated"):
                self.status.setText(
                    "🟠 Moteur installé. Les poids nécessitent une autorisation Hugging Face avant le préchargement."
                )
            else:
                self.status.setText("📦 Moteur installé. Cliquez sur « Précharger les poids ».")
        else:
            py = st.get("python") or ""
            if py:
                self.status.setText("⬇ Prêt à installer avec : " + py)
            else:
                wanted = ".".join(map(str, spec["python"]))
                self.status.setText("⚠️ Python " + wanted + " n'est pas détecté. Installez-le depuis le Centre d'installation.")

    def start_steps(self, steps, mode):
        if self.process is not None:
            return
        self.steps = list(steps)
        self.mode = mode
        self.log.clear()
        self.progress.setVisible(True)
        self.next_step()

    def next_step(self):
        if not self.steps:
            self.progress.setVisible(False)
            self.process = None
            self.status.setText("✅ Opération terminée.")
            self.refresh()
            audit = getattr(self.window, "installation_audit_tab", None)
            if audit is not None:
                audit.refresh()
            return

        step = self.steps.pop(0)
        self.status.setText("⏳ " + step["label"] + "…")
        self.log.appendPlainText("\n> " + step["label"])
        p = QProcess(self)
        self.process = p
        p.setWorkingDirectory(step["cwd"])
        env = QProcessEnvironment.systemEnvironment()
        for key, value in step.get("env", {}).items():
            env.insert(str(key), str(value))
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self.read_output(p))
        p.finished.connect(lambda code, state: self.finished(p, code))
        p.errorOccurred.connect(lambda _err: self.failed(p))
        p.start(step["program"], step["args"])

    def read_output(self, p):
        if self.process is p:
            text = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
            if text:
                self.log.insertPlainText(text)

    def finished(self, p, code):
        if self.process is not p:
            return
        self.read_output(p)
        self.process = None
        p.deleteLater()
        if code != 0:
            self.progress.setVisible(False)
            tail = self.log.toPlainText()[-1600:]
            self.status.setText("❌ Échec de l'étape. Consultez le journal.\n" + tail)
            self.steps = []
            self.refresh()
            return
        self.next_step()

    def failed(self, p):
        if self.process is p:
            self.log.appendPlainText("\n" + p.errorString())

    def install_engine(self):
        try:
            steps = backend.install_plan(self.mid())
        except Exception as exc:
            QMessageBox.warning(self, "Installation", str(exc))
            return
        self.start_steps(steps, "install")

    def preload(self):
        st = backend.state(self.mid())
        if st.get("gated"):
            reply = QMessageBox.question(
                self,
                "Accès Hugging Face requis",
                "Stable Audio Open demande une autorisation d'accès sur Hugging Face. "
                "IA Manager peut tenter le téléchargement si votre compte/jeton est déjà autorisé.\n\nContinuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            cmd = backend.preload_command(self.mid())
        except Exception as exc:
            QMessageBox.warning(self, "Poids", str(exc))
            return
        self.start_steps([cmd], "weights")

    def open_folder(self):
        try:
            path = backend.paths(self.mid())["base"]
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        except Exception as exc:
            self.status.setText("❌ " + str(exc))


def _add_navigation(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "CRÉATION" and not any(e[0] == "audio_voice_install_tab" for e in entries):
                entries.append(("audio_voice_install_tab", "Audio & Voix avancés", "Installer Whisper, Kokoro, XTTS et Stable Audio."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    for module_name in ("v165_extension", "v166_extension"):
        try:
            module = __import__("src.ui." + module_name, fromlist=[module_name])
            if hasattr(module, "SIMPLE_ATTRS"):
                module.SIMPLE_ATTRS.add("audio_voice_install_tab")
        except Exception:
            pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v181(window):
    if getattr(window, "_v181_audio_voice", False):
        return
    tab = AudioVoiceInstallTab(window)
    window.audio_voice_install_tab = tab
    target = getattr(window, "installation_audit_tab", None)
    idx = window.tabs.indexOf(target) if target is not None else -1
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "🎙 Audio & Voix")
    _add_navigation(window)
    window._v181_audio_voice = True
