"""v183 : assistant Stable Audio Open + TRELLIS/WSL2."""
from __future__ import annotations

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QPlainTextEdit, QMessageBox,
)

from src.backend import final_blockers, settings


class FinalBlockersTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = None

        root = QVBoxLayout(self)
        title = QLabel("Derniers blocages d’installation")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Stable Audio Open et TRELLIS ont des contraintes externes que IA Manager ne doit pas masquer. "
            "Cette page vérifie ces prérequis et automatise tout ce qui peut l'être proprement."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        hf_box = QGroupBox("Stable Audio Open — accès Hugging Face")
        hf_lay = QVBoxLayout(hf_box)
        self.hf_state = QLabel()
        self.hf_state.setWordWrap(True)
        hf_lay.addWidget(self.hf_state)

        hf_row = QHBoxLayout()
        self.hf_token = QLineEdit(str(settings.get("huggingface_token") or ""))
        self.hf_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_token.setPlaceholderText("Jeton Hugging Face (hf_...)")
        save = QPushButton("💾 Enregistrer le jeton")
        check = QPushButton("🔎 Vérifier l’accès")
        open_audio = QPushButton("🎙 Ouvrir Audio & Voix")
        hf_row.addWidget(self.hf_token, 1)
        hf_row.addWidget(save)
        hf_row.addWidget(check)
        hf_row.addWidget(open_audio)
        hf_lay.addLayout(hf_row)
        root.addWidget(hf_box)

        tr_box = QGroupBox("TRELLIS — WSL2 / CUDA")
        tr_lay = QVBoxLayout(tr_box)
        self.tr_state = QLabel()
        self.tr_state.setWordWrap(True)
        tr_lay.addWidget(self.tr_state)

        tr_row = QHBoxLayout()
        self.wsl_install = QPushButton("⬇ Installer WSL2 + Ubuntu")
        self.wsl_prepare = QPushButton("🛠 Préparer TRELLIS dans WSL")
        self.open_advanced = QPushButton("🎬 Ouvrir Vidéo & 3D avancés")
        tr_row.addWidget(self.wsl_install)
        tr_row.addWidget(self.wsl_prepare)
        tr_row.addWidget(self.open_advanced)
        tr_row.addStretch(1)
        tr_lay.addLayout(tr_row)
        root.addWidget(tr_box)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1600)
        root.addWidget(self.log, 1)

        save.clicked.connect(self.save_token)
        check.clicked.connect(self.refresh)
        open_audio.clicked.connect(lambda: window.tabs.setCurrentWidget(window.audio_voice_install_tab))
        self.wsl_install.clicked.connect(self.install_wsl)
        self.wsl_prepare.clicked.connect(self.prepare_trellis)
        open_advanced.clicked.connect(lambda: window.tabs.setCurrentWidget(window.advanced_video3d_tab))

        self.refresh()

    def save_token(self):
        final_blockers.save_hf_token(self.hf_token.text())
        self.refresh()

    def refresh(self):
        try:
            stable = final_blockers.stable_audio_status()
            eng = stable["engine"]
            acc = stable["access"]
            access = (
                "✅ Accès Hugging Face valide" if acc["ok"] else
                ("🔐 Jeton présent mais accès refusé" if acc["token"] else "🔐 Jeton Hugging Face absent / accès requis")
            )
            engine = "✅ moteur installé" if eng.get("installed") else "⬇ moteur à installer"
            weights = "✅ poids prêts" if eng.get("ready") else "📦 poids non préchargés"
            self.hf_state.setText(f"{access} · {engine} · {weights}\n" + str(acc.get("message") or ""))
        except Exception as exc:
            self.hf_state.setText("Vérification Stable Audio impossible : " + str(exc))

        try:
            st = final_blockers.trellis_status()
            bits = [
                "✅ WSL détecté" if st["wsl"] else "⚠️ WSL absent",
                "✅ WSL2 détecté" if st["wsl2"] else "🟠 WSL2 non confirmé",
                "✅ NVIDIA" if st["nvidia"] else "⚠️ nvidia-smi absent",
                "✅ CUDA Toolkit" if st["nvcc"] else "🟠 nvcc absent côté Windows",
                "✅ dépôt TRELLIS local" if st["source_ready"] else "📦 dépôt TRELLIS non préparé",
            ]
            self.tr_state.setText(" · ".join(bits))
            self.wsl_install.setEnabled(not st["wsl2"] and self.process is None)
            self.wsl_prepare.setEnabled(st["wsl"] and self.process is None)
        except Exception as exc:
            self.tr_state.setText("Diagnostic TRELLIS impossible : " + str(exc))

        audit = getattr(self.window, "installation_audit_tab", None)
        if audit is not None:
            audit.refresh()

    def start_command(self, cmd, label):
        if self.process is not None:
            return
        p = QProcess(self)
        self.process = p
        p.setWorkingDirectory(cmd["cwd"])
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self.read_output(p))
        p.finished.connect(lambda code, state: self.finished(p, code, label))
        p.errorOccurred.connect(lambda _e: self.log.appendPlainText("\n" + p.errorString()))
        self.log.appendPlainText("\n> " + label)
        p.start(cmd["program"], cmd["args"])

    def read_output(self, p):
        if self.process is p:
            text = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
            if text:
                self.log.insertPlainText(text)

    def finished(self, p, code, label):
        if self.process is not p:
            return
        self.read_output(p)
        self.process = None
        p.deleteLater()
        self.log.appendPlainText("\n" + ("✅ " if code == 0 else "❌ ") + label + f" · code {code}")
        self.refresh()

    def install_wsl(self):
        reply = QMessageBox.question(
            self,
            "Installer WSL2",
            "Windows va demander une autorisation administrateur (UAC) pour installer WSL2 et Ubuntu. "
            "Un redémarrage peut être nécessaire.\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            cmd = final_blockers.wsl_install_command()
        except Exception as exc:
            QMessageBox.warning(self, "WSL2", str(exc))
            return
        self.start_command(cmd, "Installation WSL2 + Ubuntu")

    def prepare_trellis(self):
        reply = QMessageBox.question(
            self,
            "Préparer TRELLIS dans WSL",
            "Cette étape installe les paquets Linux nécessaires et clone le dépôt TRELLIS dans votre HOME WSL. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            cmd = final_blockers.trellis_wsl_bootstrap_command()
        except Exception as exc:
            QMessageBox.warning(self, "TRELLIS", str(exc))
            return
        self.start_command(cmd, "Préparation TRELLIS dans WSL")


def _add_navigation(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "SYSTÈME" and not any(e[0] == "final_blockers_tab" for e in entries):
                entries.append(("final_blockers_tab", "Derniers blocages", "Hugging Face gated et TRELLIS/WSL2."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    for module_name in ("v165_extension", "v166_extension"):
        try:
            module = __import__("src.ui." + module_name, fromlist=[module_name])
            if hasattr(module, "SIMPLE_ATTRS"):
                module.SIMPLE_ATTRS.add("final_blockers_tab")
        except Exception:
            pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v183(window):
    if getattr(window, "_v183_final_blockers", False):
        return
    tab = FinalBlockersTab(window)
    window.final_blockers_tab = tab
    target = getattr(window, "advanced_video3d_tab", None)
    idx = window.tabs.indexOf(target) if target is not None else -1
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "🧩 Derniers blocages")
    _add_navigation(window)
    window._v183_final_blockers = True
