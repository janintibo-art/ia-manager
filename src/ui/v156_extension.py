"""v156 : Centre de santé global."""
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import creative_tools, github_tools, storage
from src.backend.ai_manager import AIManager


def _port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.6):
            return True
    except Exception:
        return False


def _run(cmd):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=flags)
        return p.returncode == 0, (p.stdout or p.stderr or "").strip()
    except Exception as exc:
        return False, str(exc)


def _disk_row(path):
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    total, used, free = shutil.disk_usage(p)
    return free / 2**30, total / 2**30


class HealthWorker(QThread):
    done = pyqtSignal(list, dict)

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def run(self):
        rows = []
        summary = {"ok": 0, "warn": 0, "bad": 0}

        def add(name, ok, detail, action="", severity="bad"):
            state = "ok" if ok else severity
            summary[state] += 1
            rows.append((name, state, detail, action))

        add("Python IA Manager", True, f"{sys.version.split()[0]} · {sys.executable}", "Analyse")

        git = shutil.which("git")
        add("Git", bool(git), git or "Git introuvable", "Outils locaux")
        gh = github_tools.tool_status().get("gh")
        add("GitHub CLI", bool(gh), gh or "GitHub CLI introuvable", "GitHub", "warn")

        ollama_bin = shutil.which("ollama")
        add("Ollama installé", bool(ollama_bin), ollama_bin or "ollama introuvable", "Analyse")
        ollama_up = _port_open(11434)
        add("Serveur Ollama", ollama_up, "Port 11434 ouvert" if ollama_up else "Port 11434 fermé", "Connexions", "warn")

        try:
            models = AIManager().get_available_models(force=True) if ollama_up else []
        except Exception:
            models = []
        add("Modèles Ollama", bool(models), f"{len(models)} modèle(s) détecté(s)", "Modèles", "warn")

        nvsmi = shutil.which("nvidia-smi")
        if nvsmi:
            ok, out = _run([nvsmi, "--query-gpu=name,memory.total", "--format=csv,noheader"])
            add("NVIDIA / VRAM", ok, out.splitlines()[0] if out else "Détection NVIDIA", "Analyse")
        else:
            add("NVIDIA / VRAM", False, "nvidia-smi introuvable", "Analyse", "warn")

        creative = getattr(self.window, "creative_tools_tab", None)
        if creative is not None:
            try:
                p = creative_tools.paths(creative.directory.text(), "comfyui")
                comfy_installed = (p["source"] / "main.py").is_file()
                comfy_py = p["python"].is_file()
                add("ComfyUI installé", comfy_installed, str(p["source"]), "Outils locaux")
                add("Python ComfyUI", comfy_py, str(p["python"]), "Outils locaux")
            except Exception as exc:
                add("ComfyUI", False, str(exc), "Outils locaux", "warn")
        else:
            add("ComfyUI", False, "Onglet Outils locaux indisponible", "Outils locaux", "warn")

        comfy_port = _port_open(8188)
        add("Serveur ComfyUI", comfy_port, "Port 8188 ouvert" if comfy_port else "Port 8188 fermé", "Outils locaux", "warn")

        model_path = storage.app_models()
        try:
            model_path.mkdir(parents=True, exist_ok=True)
            free, total = _disk_row(model_path)
            add("Stockage modèles", free >= 20, f"{free:.1f} Go libres / {total:.1f} Go · {model_path}", "Modèles", "warn")
        except Exception as exc:
            add("Stockage modèles", False, str(exc), "Modèles")

        err = Path.home() / ".ia_manager" / "erreurs.log"
        if err.is_file():
            try:
                size = err.stat().st_size / 1024
                detail = f"{size:.0f} Ko · {err}"
                add("Journal d'erreurs", size < 2048, detail, "Analyse", "warn")
            except Exception:
                add("Journal d'erreurs", True, str(err), "Analyse")
        else:
            add("Journal d'erreurs", True, "Aucune erreur enregistrée", "Analyse")

        self.done.emit(rows, summary)


class HealthTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.worker = None
        self.build_ui()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("🩺 Centre de santé")
        title.setObjectName("Title")
        root.addWidget(title)

        subtitle = QLabel(
            "Un seul écran pour vérifier l'état de Python, Git, Ollama, GPU, ComfyUI, "
            "stockage et services locaux."
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        grid = QGridLayout()
        self.ok_value = self._card(grid, 0, "✅ OK")
        self.warn_value = self._card(grid, 1, "⚠️ À vérifier")
        self.bad_value = self._card(grid, 2, "❌ Problèmes")
        root.addLayout(grid)

        actions = QHBoxLayout()
        self.scan_btn = QPushButton("🔎 Lancer le diagnostic complet")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self.scan)
        actions.addWidget(self.scan_btn)

        self.open_tools = QPushButton("🛠 Outils locaux")
        self.open_tools.clicked.connect(lambda: self.open_attr("creative_tools_tab"))
        actions.addWidget(self.open_tools)

        self.open_analysis = QPushButton("📊 Analyse PC")
        self.open_analysis.clicked.connect(lambda: self.open_attr("setup_tab"))
        actions.addWidget(self.open_analysis)

        actions.addStretch()
        root.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.status = QLabel("Cliquez sur « Lancer le diagnostic complet ».")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Contrôle", "État", "Détail", "Ouvrir"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(500)
        root.addWidget(self.table)

        root.addStretch()

    def _card(self, grid, col, label):
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        v = QLabel("—")
        v.setObjectName("BigValue")
        lay.addWidget(v)
        t = QLabel(label)
        t.setObjectName("Muted")
        lay.addWidget(t)
        grid.addWidget(card, 0, col)
        return v

    def open_attr(self, attr):
        tab = getattr(self.window, attr, None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)

    def open_named(self, name):
        mapping = {
            "Analyse": "setup_tab",
            "Outils locaux": "creative_tools_tab",
            "GitHub": "github_tab",
            "Connexions": "connections_tab",
            "Modèles": "models_tab",
        }
        self.open_attr(mapping.get(name, ""))

    def scan(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status.setText("Diagnostic en cours…")
        self.worker = HealthWorker(self.window)
        self.worker.done.connect(self.on_done)
        self.worker.start()

    def on_done(self, rows, summary):
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        self.ok_value.setText(str(summary.get("ok", 0)))
        self.warn_value.setText(str(summary.get("warn", 0)))
        self.bad_value.setText(str(summary.get("bad", 0)))

        self.table.setRowCount(len(rows))
        for r, (name, state, detail, action) in enumerate(rows):
            icon = {"ok": "✅ OK", "warn": "⚠️ À vérifier", "bad": "❌ Problème"}.get(state, state)
            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setItem(r, 1, QTableWidgetItem(icon))
            self.table.setItem(r, 2, QTableWidgetItem(detail))
            if action:
                btn = QPushButton(action)
                btn.clicked.connect(lambda _=False, a=action: self.open_named(a))
                self.table.setCellWidget(r, 3, btn)

        self.table.resizeColumnsToContents()
        if summary.get("bad", 0):
            self.status.setText(
                f"Diagnostic terminé : {summary['bad']} problème(s), "
                f"{summary['warn']} point(s) à vérifier."
            )
        else:
            self.status.setText(
                f"Diagnostic terminé : aucun problème bloquant, "
                f"{summary['warn']} point(s) à vérifier."
            )


def _add_to_navigation(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ANALYSER":
                if not any(attr == "health_tab" for attr, *_ in entries):
                    entries.insert(0, ("health_tab", "Centre de santé", "Diagnostic global et raccourcis de réparation."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v156(window):
    if getattr(window, "_v156_health_center", False):
        return

    tab = HealthTab(window)
    window.health_tab = tab

    setup = getattr(window, "setup_tab", None)
    idx = window.tabs.indexOf(setup)
    window.tabs.insertTab(idx if idx >= 0 else window.tabs.count(), tab, "🩺 Centre de santé")

    _add_to_navigation(window)
    window._v156_health_center = True
