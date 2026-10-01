"""v182 : CogVideoX-2B / InstantMesh / TRELLIS."""
from __future__ import annotations

from PyQt6.QtCore import QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QPlainTextEdit, QMessageBox,
)

from src.backend import advanced_video3d_installer as backend


class AdvancedVideo3DTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = None
        self.steps = []

        root = QVBoxLayout(self)
        title = QLabel("Vidéo & 3D avancés")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Installation isolée de CogVideoX-2B et InstantMesh. "
            "TRELLIS est préparé et diagnostiqué, mais reste guidé sous Windows car son installation officielle privilégie Linux/WSL2."
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
        self.install = QPushButton("1 · Installer / préparer")
        self.install.setObjectName("Primary")
        self.weights = QPushButton("2 · Précharger les poids")
        self.launch = QPushButton("▶ Démarrer")
        self.verify = QPushButton("🔎 Vérifier")
        self.folder = QPushButton("📁 Ouvrir le dossier")
        for b in (self.install, self.weights, self.launch, self.verify, self.folder):
            row.addWidget(b)
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
        self.log.setMaximumBlockCount(2000)
        root.addWidget(self.log, 1)

        self.install.clicked.connect(self.install_engine)
        self.weights.clicked.connect(self.preload)
        self.launch.clicked.connect(self.launch_engine)
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
        self.weights.setVisible(spec["kind"] != "guided")
        self.weights.setEnabled(not busy and st.get("installed", False))
        self.launch.setVisible(self.mid() == "instantmesh")
        self.launch.setEnabled(not busy and st.get("ready", False))
        self.verify.setEnabled(not busy)
        self.folder.setEnabled(True)

        if spec["kind"] == "guided":
            self.status.setText(
                "🟠 TRELLIS reste guidé sous Windows. IA Manager peut cloner le dépôt et diagnostiquer WSL/CUDA, "
                "mais ne le marque pas automatique tant que les extensions CUDA ne sont pas correctement compilées."
            )
        elif st.get("ready"):
            self.status.setText("✅ Moteur installé et poids prêts.")
        elif st.get("installed"):
            self.status.setText("📦 Moteur installé. Préchargez maintenant les poids.")
        elif st.get("python"):
            self.status.setText("⬇ Prêt à installer avec : " + st["python"])
        else:
            wanted = ".".join(map(str, spec["python"]))
            self.status.setText("⚠️ Python " + wanted + " requis.")

    def start_steps(self, steps):
        if self.process is not None:
            return
        self.steps = list(steps)
        self.log.clear()
        self.progress.setVisible(True)
        self.next_step()

    def next_step(self):
        if not self.steps:
            self.process = None
            self.progress.setVisible(False)
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
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self.read_output(p))
        p.finished.connect(lambda code, state: self.finished(p, code))
        p.errorOccurred.connect(lambda _e: self.log.appendPlainText("\n" + p.errorString()))
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
            self.steps = []
            self.status.setText("❌ Échec d'une étape. Consultez le journal.")
            self.refresh()
            return
        self.next_step()

    def install_engine(self):
        try:
            steps = backend.install_plan(self.mid())
        except Exception as exc:
            QMessageBox.warning(self, "Installation", str(exc))
            return
        self.start_steps(steps)

    def preload(self):
        try:
            cmd = backend.prepare_command(self.mid())
        except Exception as exc:
            QMessageBox.warning(self, "Poids", str(exc))
            return
        if self.mid() == "cogvideox-2b":
            reply = QMessageBox.question(
                self, "Téléchargement volumineux",
                "CogVideoX-2B représente environ 13,8 Go. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.start_steps([cmd])

    def launch_engine(self):
        try:
            cmd = backend.launch_command(self.mid())
        except Exception as exc:
            QMessageBox.warning(self, "Démarrage", str(exc))
            return
        self.start_steps([cmd])

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
            if section == "CRÉATION" and not any(e[0] == "advanced_video3d_tab" for e in entries):
                entries.append(("advanced_video3d_tab", "Vidéo & 3D avancés", "CogVideoX, InstantMesh et diagnostic TRELLIS."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    for module_name in ("v165_extension", "v166_extension"):
        try:
            module = __import__("src.ui." + module_name, fromlist=[module_name])
            if hasattr(module, "SIMPLE_ATTRS"):
                module.SIMPLE_ATTRS.add("advanced_video3d_tab")
        except Exception:
            pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v182(window):
    if getattr(window, "_v182_advanced_video3d", False):
        return
    tab = AdvancedVideo3DTab(window)
    window.advanced_video3d_tab = tab
    target = getattr(window, "audio_voice_install_tab", None)
    idx = window.tabs.indexOf(target) if target is not None else -1
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "🎬 Vidéo & 3D avancés")
    _add_navigation(window)
    window._v182_advanced_video3d = True
