"""Extension v141 : évaluation qualitative explicite avant/après."""
import ast
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from types import MethodType

import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

DEFAULT_TESTS = [
    {
        "prompt": "Quel est le résultat de 37 × 24 ? Réponds uniquement par le nombre.",
        "type": "nombre",
        "expected": "888",
    },
    {
        "prompt": "Réponds exactement par : IA locale",
        "type": "exact",
        "expected": "IA locale",
    },
    {
        "prompt": "Donne une phrase contenant le mot confidentialité.",
        "type": "contient",
        "expected": "confidentialité",
    },
    {
        "prompt": "Écris une fonction Python add(a, b) qui retourne a+b.",
        "type": "python",
        "expected": "",
    },
]

TYPES = ["contient", "exact", "regex", "nombre", "python", "manuel"]


def _qual_root():
    path = Path.home() / ".ia_manager" / "benchmarks" / "qualitatif"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_number(text):
    m = re.search(r"[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)", text or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _extract_python(text):
    text = text or ""
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.S | re.I)
    return blocks[0].strip() if blocks else text.strip()


def _evaluate(response, kind, expected):
    kind = (kind or "").strip().lower()
    expected = (expected or "").strip()
    response = response or ""

    if kind == "manuel":
        return None, "À vérifier manuellement"

    if kind == "contient":
        ok = expected.casefold() in response.casefold()
        return ok, "texte attendu présent" if ok else "texte attendu absent"

    if kind == "exact":
        ok = response.strip() == expected
        return ok, "correspondance exacte" if ok else "réponse différente"

    if kind == "regex":
        try:
            ok = re.search(expected, response, flags=re.I | re.S) is not None
            return ok, "regex trouvée" if ok else "regex absente"
        except re.error as exc:
            return False, "regex invalide : " + str(exc)

    if kind == "nombre":
        got = _extract_number(response)
        wanted = _extract_number(expected)
        if got is None or wanted is None:
            return False, "nombre introuvable"
        ok = abs(got - wanted) <= max(1e-9, abs(wanted) * 1e-9)
        return ok, f"{got:g} / attendu {wanted:g}"

    if kind == "python":
        try:
            ast.parse(_extract_python(response))
            return True, "syntaxe Python valide"
        except SyntaxError as exc:
            return False, f"syntaxe Python invalide : ligne {exc.lineno}"

    return False, "type de test inconnu"


class QualWorker(QThread):
    progress = pyqtSignal(str)
    row_ready = pyqtSignal(dict)
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, before, after, tests, parent=None):
        super().__init__(parent)
        self.before = before
        self.after = after
        self.tests = tests
        self.stop_event = threading.Event()
        self.url = "http://localhost:11434"

    def stop(self):
        self.stop_event.set()

    def ask(self, model, prompt):
        r = requests.post(
            self.url + "/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "5m",
                "options": {"temperature": 0, "seed": 42},
            },
            timeout=900,
        )
        if r.status_code != 200:
            raise RuntimeError(f"{model} : Ollama {r.status_code} · {r.text[:250]}")
        return str(r.json().get("response") or "")

    def run(self):
        campaign = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "before": self.before,
            "after": self.after,
            "tests": self.tests,
            "rows": [],
            "cancelled": False,
        }
        try:
            for i, test in enumerate(self.tests, 1):
                if self.stop_event.is_set():
                    campaign["cancelled"] = True
                    break

                self.progress.emit(f"{i}/{len(self.tests)} · test du modèle avant…")
                before_text = self.ask(self.before, test["prompt"])
                before_ok, before_note = _evaluate(
                    before_text, test["type"], test["expected"]
                )

                if self.stop_event.is_set():
                    campaign["cancelled"] = True
                    break

                self.progress.emit(f"{i}/{len(self.tests)} · test du modèle après…")
                after_text = self.ask(self.after, test["prompt"])
                after_ok, after_note = _evaluate(
                    after_text, test["type"], test["expected"]
                )

                row = {
                    "index": i,
                    "prompt": test["prompt"],
                    "type": test["type"],
                    "expected": test["expected"],
                    "before_response": before_text,
                    "after_response": after_text,
                    "before_ok": before_ok,
                    "after_ok": after_ok,
                    "before_note": before_note,
                    "after_note": after_note,
                }
                campaign["rows"].append(row)
                self.row_ready.emit(dict(row))

            scorable = [
                r for r in campaign["rows"]
                if r["before_ok"] is not None and r["after_ok"] is not None
            ]
            before_pass = sum(1 for r in scorable if r["before_ok"])
            after_pass = sum(1 for r in scorable if r["after_ok"])

            campaign["summary"] = {
                "scorable": len(scorable),
                "before_pass": before_pass,
                "after_pass": after_pass,
                "before_rate": (before_pass / len(scorable) * 100) if scorable else None,
                "after_rate": (after_pass / len(scorable) * 100) if scorable else None,
            }

            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out = _qual_root() / f"qualitatif-{stamp}.json"
            out.write_text(
                json.dumps(campaign, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            campaign["path"] = str(out)
            self.completed.emit(campaign)

        except Exception as exc:
            self.failed.emit(str(exc))


def install_v141(window):
    tab = getattr(window, "benchmark_tab", None)
    if tab is None or getattr(window, "_v141_qualitative", False):
        return

    group = QGroupBox("5 · Évaluation qualitative Avant / Après")
    layout = QVBoxLayout(group)

    hint = QLabel(
        "Mesure uniquement des critères explicites. Un taux de réussite élevé ne signifie pas "
        "qu’un modèle est globalement meilleur : lisez aussi les réponses complètes."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    selectors = QHBoxLayout()
    selectors.addWidget(QLabel("Avant"))
    tab.v141_before = QComboBox()
    selectors.addWidget(tab.v141_before, 1)
    selectors.addWidget(QLabel("Après"))
    tab.v141_after = QComboBox()
    selectors.addWidget(tab.v141_after, 1)
    tab.v141_refresh = QPushButton("🔄 Modèles")
    selectors.addWidget(tab.v141_refresh)
    layout.addLayout(selectors)

    tab.v141_tests = QTableWidget(0, 3)
    tab.v141_tests.setHorizontalHeaderLabels(["Prompt", "Critère", "Attendu"])
    tab.v141_tests.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tab.v141_tests.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(tab.v141_tests)

    edit_row = QHBoxLayout()
    tab.v141_add = QPushButton("＋ Ajouter un test")
    edit_row.addWidget(tab.v141_add)
    tab.v141_remove = QPushButton("− Supprimer")
    edit_row.addWidget(tab.v141_remove)
    tab.v141_defaults = QPushButton("↺ Tests d’exemple")
    edit_row.addWidget(tab.v141_defaults)
    edit_row.addStretch()
    layout.addLayout(edit_row)

    action_row = QHBoxLayout()
    tab.v141_run = QPushButton("▶ Comparer Avant / Après")
    tab.v141_run.setObjectName("Primary")
    action_row.addWidget(tab.v141_run)
    tab.v141_stop = QPushButton("■ Arrêter après la requête en cours")
    tab.v141_stop.setObjectName("Danger")
    tab.v141_stop.setEnabled(False)
    action_row.addWidget(tab.v141_stop)
    tab.v141_open = QPushButton("📁 Historique qualitatif")
    action_row.addWidget(tab.v141_open)
    action_row.addStretch()
    layout.addLayout(action_row)

    tab.v141_status = QLabel("Prêt.")
    tab.v141_status.setWordWrap(True)
    layout.addWidget(tab.v141_status)

    tab.v141_results = QTableWidget(0, 8)
    tab.v141_results.setHorizontalHeaderLabels([
        "#", "Critère", "Avant", "Après",
        "Réponse avant", "Réponse après", "Diagnostic avant", "Diagnostic après"
    ])
    tab.v141_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tab.v141_results.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(tab.v141_results)

    tab.layout().addWidget(group)
    tab.v141_worker = None

    def v141_refresh_models(self):
        current_before = self.v141_before.currentText()
        current_after = self.v141_after.currentText()
        models = self.ai.get_available_models(force=True)
        self.v141_before.clear()
        self.v141_after.clear()
        self.v141_before.addItems(models)
        self.v141_after.addItems(models)
        if current_before:
            idx = self.v141_before.findText(current_before)
            if idx >= 0:
                self.v141_before.setCurrentIndex(idx)
        if current_after:
            idx = self.v141_after.findText(current_after)
            if idx >= 0:
                self.v141_after.setCurrentIndex(idx)
        elif len(models) > 1:
            self.v141_after.setCurrentIndex(1)
        self.v141_status.setText(f"{len(models)} modèle(s) disponible(s).")

    def v141_add_test(self, data=None):
        data = data or {"prompt": "", "type": "contient", "expected": ""}
        row = self.v141_tests.rowCount()
        self.v141_tests.insertRow(row)
        self.v141_tests.setItem(row, 0, QTableWidgetItem(data.get("prompt", "")))
        combo = QComboBox()
        combo.addItems(TYPES)
        idx = combo.findText(data.get("type", "contient"))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.v141_tests.setCellWidget(row, 1, combo)
        self.v141_tests.setItem(row, 2, QTableWidgetItem(data.get("expected", "")))

    def v141_load_defaults(self):
        self.v141_tests.setRowCount(0)
        for item in DEFAULT_TESTS:
            self.v141_add_test(item)

    def v141_remove_test(self):
        rows = sorted(
            {idx.row() for idx in self.v141_tests.selectionModel().selectedRows()},
            reverse=True
        )
        for row in rows:
            self.v141_tests.removeRow(row)

    def v141_collect_tests(self):
        tests = []
        for row in range(self.v141_tests.rowCount()):
            prompt_item = self.v141_tests.item(row, 0)
            expected_item = self.v141_tests.item(row, 2)
            combo = self.v141_tests.cellWidget(row, 1)
            prompt = prompt_item.text().strip() if prompt_item else ""
            expected = expected_item.text().strip() if expected_item else ""
            kind = combo.currentText() if combo else "manuel"
            if not prompt:
                continue
            if kind not in ("python", "manuel") and not expected:
                raise ValueError(f"Test {row + 1} : valeur attendue manquante.")
            tests.append({"prompt": prompt, "type": kind, "expected": expected})
        if not tests:
            raise ValueError("Ajoutez au moins un test.")
        return tests

    def v141_set_busy(self, busy):
        self.v141_run.setEnabled(not busy)
        self.v141_stop.setEnabled(busy)
        self.v141_refresh.setEnabled(not busy)
        self.v141_before.setEnabled(not busy)
        self.v141_after.setEnabled(not busy)
        self.v141_tests.setEnabled(not busy)
        self.v141_add.setEnabled(not busy)
        self.v141_remove.setEnabled(not busy)
        self.v141_defaults.setEnabled(not busy)

    def v141_start(self):
        if self.v141_worker is not None:
            return
        before = self.v141_before.currentText().strip()
        after = self.v141_after.currentText().strip()
        if not before or not after:
            self.v141_status.setText("Choisissez deux modèles.")
            return
        try:
            tests = self.v141_collect_tests()
        except Exception as exc:
            self.v141_status.setText(str(exc))
            return

        self.v141_results.setRowCount(0)
        worker = QualWorker(before, after, tests, self)
        self.v141_worker = worker
        worker.progress.connect(self.v141_status.setText)
        worker.row_ready.connect(self.v141_add_result)
        worker.completed.connect(self.v141_done)
        worker.failed.connect(self.v141_failed)
        self.v141_set_busy(True)
        worker.start()

    def v141_add_result(self, row):
        r = self.v141_results.rowCount()
        self.v141_results.insertRow(r)

        def mark(value):
            if value is None:
                return "manuel"
            return "✅" if value else "❌"

        values = [
            str(row["index"]),
            row["type"],
            mark(row["before_ok"]),
            mark(row["after_ok"]),
            row["before_response"][:180].replace("\n", " "),
            row["after_response"][:180].replace("\n", " "),
            row["before_note"],
            row["after_note"],
        ]
        for c, value in enumerate(values):
            self.v141_results.setItem(r, c, QTableWidgetItem(value))

    def v141_done(self, campaign):
        self.v141_worker = None
        self.v141_set_busy(False)
        s = campaign.get("summary", {})
        if s.get("scorable"):
            self.v141_status.setText(
                f"✅ Tests terminés · Avant {s['before_pass']}/{s['scorable']} "
                f"({s['before_rate']:.0f} %) · Après {s['after_pass']}/{s['scorable']} "
                f"({s['after_rate']:.0f} %) · {campaign.get('path','')}"
            )
        else:
            self.v141_status.setText(
                "✅ Tests terminés · uniquement des critères manuels · "
                + campaign.get("path", "")
            )

    def v141_failed(self, error):
        self.v141_worker = None
        self.v141_set_busy(False)
        self.v141_status.setText("❌ Évaluation interrompue : " + error)

    def v141_stop_run(self):
        if self.v141_worker is not None:
            self.v141_worker.stop()
            self.v141_status.setText(
                "Arrêt demandé · fin après la requête Ollama en cours."
            )

    def v141_open_history(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(_qual_root())))

    tab.v141_refresh_models = MethodType(v141_refresh_models, tab)
    tab.v141_add_test = MethodType(v141_add_test, tab)
    tab.v141_load_defaults = MethodType(v141_load_defaults, tab)
    tab.v141_remove_test = MethodType(v141_remove_test, tab)
    tab.v141_collect_tests = MethodType(v141_collect_tests, tab)
    tab.v141_set_busy = MethodType(v141_set_busy, tab)
    tab.v141_start = MethodType(v141_start, tab)
    tab.v141_add_result = MethodType(v141_add_result, tab)
    tab.v141_done = MethodType(v141_done, tab)
    tab.v141_failed = MethodType(v141_failed, tab)
    tab.v141_stop_run = MethodType(v141_stop_run, tab)
    tab.v141_open_history = MethodType(v141_open_history, tab)

    tab.v141_refresh.clicked.connect(tab.v141_refresh_models)
    tab.v141_add.clicked.connect(lambda: tab.v141_add_test())
    tab.v141_remove.clicked.connect(tab.v141_remove_test)
    tab.v141_defaults.clicked.connect(tab.v141_load_defaults)
    tab.v141_run.clicked.connect(tab.v141_start)
    tab.v141_stop.clicked.connect(tab.v141_stop_run)
    tab.v141_open.clicked.connect(tab.v141_open_history)

    old_shutdown = tab.shutdown
    def shutdown(self):
        if self.v141_worker is not None:
            self.v141_worker.stop()
            self.v141_worker.wait(2000)
        old_shutdown()
    tab.shutdown = MethodType(shutdown, tab)

    tab.v141_load_defaults()
    tab.v141_refresh_models()
    window._v141_qualitative = True
