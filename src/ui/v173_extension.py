"""v173 : installation universelle des prérequis depuis IA Manager."""
from __future__ import annotations

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)

from src.backend import installer_center as center


class _UniversalInstaller:
    def __init__(self, tab):
        self.tab = tab
        self.queue = []
        self.current_id = None
        self.process = None

        box = QGroupBox("Installation universelle")
        lay = QVBoxLayout(box)

        info = QLabel(
            "Installe automatiquement les prérequis manquants pris en charge, dans le bon ordre. "
            "Les composants déjà présents sont ignorés. ComfyUI reste géré par Outils locaux."
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        row = QHBoxLayout()
        self.prepare = QPushButton("⚡ Tout préparer automatiquement")
        self.prepare.setObjectName("Primary")
        self.refresh_btn = QPushButton("🔄 Revérifier")
        row.addWidget(self.prepare)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        lay.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        lay.addWidget(self.progress)

        self.state = QLabel()
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        # Le centre d'installation v170 possède déjà son layout principal.
        tab.layout().insertWidget(2, box)

        self.box = box
        self.prepare.clicked.connect(self.start)
        self.refresh_btn.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self):
        rows = center.status_rows()
        installed = sum(1 for row in rows if row["installed"])
        missing_auto = center.automatic_install_ids()
        internal = center.remaining_internal_ids()

        total = len(rows)
        pct = int(installed * 100 / total) if total else 100
        self.progress.setValue(pct)

        if not missing_auto and not internal:
            self.state.setText("✅ Tout est prêt : tous les composants détectés sont installés.")
            self.prepare.setText("✅ Tout est prêt")
            self.prepare.setEnabled(False)
        elif missing_auto:
            names = {row["id"]: row["name"] for row in rows}
            label = ", ".join(names.get(x, x) for x in missing_auto)
            suffix = ""
            if internal:
                suffix = " · ComfyUI pourra ensuite être installé depuis Outils locaux."
            self.state.setText("À installer automatiquement : " + label + suffix)
            self.prepare.setText("⚡ Tout préparer automatiquement")
            self.prepare.setEnabled(self.process is None)
        else:
            self.state.setText("✅ Prérequis système prêts. Il reste ComfyUI à installer depuis Outils locaux.")
            self.prepare.setText("✅ Prérequis prêts")
            self.prepare.setEnabled(False)

        try:
            self.tab.refresh()
        except Exception:
            pass

    def start(self):
        if self.process is not None:
            return
        self.queue = center.automatic_install_ids()
        if not self.queue:
            self.refresh()
            return

        answer = QMessageBox.question(
            self.tab,
            "Installation universelle",
            "IA Manager va installer automatiquement les composants manquants via WinGet/npm.\n\n"
            "Les composants déjà installés seront ignorés. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.prepare.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self._next()

    def _next(self):
        if not self.queue:
            self.process = None
            self.current_id = None
            self.refresh_btn.setEnabled(True)
            self.state.setText("✅ Installation automatique terminée. Vérification finale…")
            self.refresh()
            return

        self.current_id = self.queue.pop(0)
        rows = {row["id"]: row for row in center.status_rows()}
        row = rows.get(self.current_id)

        # Une installation précédente (ex. Node.js) peut avoir rendu le composant
        # déjà détectable entre-temps.
        if row and row["installed"]:
            self._next()
            return

        try:
            cmd = center.install_command(self.current_id)
        except Exception as exc:
            self.state.setText(f"❌ {self.current_id} : {exc}")
            self.process = None
            self.refresh_btn.setEnabled(True)
            self.prepare.setEnabled(True)
            return

        name = row["name"] if row else self.current_id
        done_count = len(center.automatic_install_ids()) - len(self.queue)
        self.state.setText(f"⏳ Installation de {name}…")

        p = QProcess(self.tab)
        self.process = p
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self._read(p))
        p.finished.connect(lambda code, _status: self._finished(p, code))
        p.errorOccurred.connect(lambda _err: self._error(p))
        p.start(cmd["program"], cmd["args"])

    def _read(self, p):
        if self.process is not p:
            return
        data = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
        lines = [line.strip() for line in data.splitlines() if line.strip()]
        if lines:
            self.state.setText("⏳ " + lines[-1][-500:])

    def _finished(self, p, code):
        if self.process is not p:
            return
        self._read(p)
        p.deleteLater()
        self.process = None
        if code != 0:
            self.state.setText(
                f"❌ Installation interrompue sur {self.current_id} (code {code}). "
                "Vous pouvez relancer : les composants déjà installés seront ignorés."
            )
            self.refresh_btn.setEnabled(True)
            self.prepare.setEnabled(True)
            return
        self._next()

    def _error(self, p):
        if self.process is not p:
            return
        self.state.setText(
            f"❌ Impossible de lancer l'installation de {self.current_id} : {p.errorString()}"
        )
        self.process = None
        self.refresh_btn.setEnabled(True)
        self.prepare.setEnabled(True)


def install_v173(window):
    if getattr(window, "_v173_universal_install", False):
        return
    tab = getattr(window, "installation_center_tab", None)
    if tab is None:
        return
    window.v173_universal_installer = _UniversalInstaller(tab)
    window._v173_universal_install = True
