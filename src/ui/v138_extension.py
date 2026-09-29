"""Extension v138 : Dataset Studio pour préparer les jeux de données Unsloth."""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import training_lab as lab


def _dataset_root():
    path = lab.lab_root() / "datasets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_any(path):
    path = Path(path)
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("Dataset limité à 100 Mo dans Dataset Studio.")

    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            for key in ("data", "examples", "rows", "dataset"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            raise ValueError("Le JSON doit contenir une liste d’exemples.")
        return data

    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            rows.append({"__invalid__": f"Ligne {n} : JSON invalide · {exc.msg}"})
    return rows


def _normalize_space(value):
    value = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    value = unicodedata.normalize("NFC", value)
    value = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in value.split("\n"))
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _canonical(row):
    return json.dumps(
        {
            "instruction": row["instruction"].casefold(),
            "input": row["input"].casefold(),
            "output": row["output"].casefold(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _convert_item(item):
    if not isinstance(item, dict):
        return None, "objet JSON attendu"

    if "__invalid__" in item:
        return None, item["__invalid__"]

    instruction = item.get("instruction")
    context = item.get("input", "")
    output = item.get("output")

    # Quelques formats très courants sont acceptés à l'import.
    if instruction is None and "question" in item:
        instruction = item.get("question")
    if output is None and "answer" in item:
        output = item.get("answer")
    if output is None and "response" in item:
        output = item.get("response")
    if not context and "context" in item:
        context = item.get("context", "")

    if instruction is None and "prompt" in item:
        instruction = item.get("prompt")
    if output is None and "completion" in item:
        output = item.get("completion")

    # Format conversation simple : messages [{role,content}, ...]
    messages = item.get("messages")
    if (instruction is None or output is None) and isinstance(messages, list):
        user_parts, assistant_parts = [], []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "")).lower()
            content = msg.get("content", "")
            if role == "user":
                user_parts.append(str(content))
            elif role == "assistant":
                assistant_parts.append(str(content))
        if instruction is None and user_parts:
            instruction = "\n".join(user_parts)
        if output is None and assistant_parts:
            output = "\n".join(assistant_parts)

    if not isinstance(instruction, str) or not isinstance(output, str):
        return None, "instruction/output introuvables ou non textuels"
    if not isinstance(context, str):
        context = str(context or "")

    row = {
        "instruction": _normalize_space(instruction),
        "input": _normalize_space(context),
        "output": _normalize_space(output),
    }
    if not row["instruction"]:
        return None, "instruction vide"
    if not row["output"]:
        return None, "output vide"
    return row, ""


def _clean(items, max_chars, remove_duplicates, remove_too_long):
    clean = []
    rejected = []
    seen = set()
    duplicates = 0
    too_long = 0

    for index, item in enumerate(items, 1):
        row, reason = _convert_item(item)
        if row is None:
            rejected.append((index, reason))
            continue

        total = len(row["instruction"]) + len(row["input"]) + len(row["output"])
        if remove_too_long and total > max_chars:
            too_long += 1
            rejected.append((index, f"trop long · {total} caractères"))
            continue

        key = _canonical(row)
        if remove_duplicates and key in seen:
            duplicates += 1
            continue
        seen.add(key)
        clean.append(row)

    return clean, rejected, duplicates, too_long


def install_v138(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(window, "_v138_dataset_studio", False):
        return

    page = QWidget()
    root = QVBoxLayout(page)

    title = QLabel("🧹 Dataset Studio")
    title.setObjectName("Title")
    root.addWidget(title)

    intro = QLabel(
        "Importez un JSONL ou JSON, contrôlez sa qualité, nettoyez les textes, "
        "dédupliquez les exemples et créez une copie prête pour Unsloth. "
        "Le fichier original n’est jamais modifié."
    )
    intro.setWordWrap(True)
    root.addWidget(intro)

    source_box = QGroupBox("1 · Source")
    sl = QVBoxLayout(source_box)
    form = QFormLayout()
    tab.v138_path = QLineEdit()
    tab.v138_path.setPlaceholderText("Fichier .jsonl ou .json")
    form.addRow("Dataset", tab.v138_path)
    sl.addLayout(form)

    row = QHBoxLayout()
    tab.v138_choose = QPushButton("Choisir un fichier…")
    row.addWidget(tab.v138_choose)
    tab.v138_analyze = QPushButton("🔎 Analyser")
    row.addWidget(tab.v138_analyze)
    row.addStretch()
    sl.addLayout(row)
    root.addWidget(source_box)

    rules_box = QGroupBox("2 · Nettoyage")
    rl = QVBoxLayout(rules_box)
    form = QFormLayout()

    tab.v138_dedupe = QCheckBox("Supprimer les doublons exacts")
    tab.v138_dedupe.setChecked(True)
    form.addRow(tab.v138_dedupe)

    tab.v138_remove_long = QCheckBox("Écarter les exemples trop longs")
    tab.v138_remove_long.setChecked(True)
    form.addRow(tab.v138_remove_long)

    tab.v138_max_chars = QSpinBox()
    tab.v138_max_chars.setRange(1000, 100000)
    tab.v138_max_chars.setSingleStep(1000)
    tab.v138_max_chars.setValue(16000)
    form.addRow("Longueur maximale", tab.v138_max_chars)

    rl.addLayout(form)
    root.addWidget(rules_box)

    tab.v138_stats = QLabel("Aucun dataset analysé.")
    tab.v138_stats.setWordWrap(True)
    root.addWidget(tab.v138_stats)

    preview_box = QGroupBox("3 · Aperçu")
    pl = QVBoxLayout(preview_box)
    tab.v138_table = QTableWidget(0, 4)
    tab.v138_table.setHorizontalHeaderLabels(
        ["#", "Instruction", "Contexte", "Réponse"]
    )
    tab.v138_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tab.v138_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tab.v138_table.verticalHeader().hide()
    tab.v138_table.horizontalHeader().setStretchLastSection(True)
    tab.v138_table.setMinimumHeight(240)
    pl.addWidget(tab.v138_table)

    tab.v138_rejects = QPlainTextEdit()
    tab.v138_rejects.setReadOnly(True)
    tab.v138_rejects.setMaximumHeight(120)
    tab.v138_rejects.setPlaceholderText(
        "Les lignes rejetées et leurs raisons apparaîtront ici."
    )
    pl.addWidget(tab.v138_rejects)
    root.addWidget(preview_box, 1)

    actions = QHBoxLayout()
    tab.v138_save = QPushButton("💾 Créer le dataset propre")
    tab.v138_save.setObjectName("Primary")
    tab.v138_save.setEnabled(False)
    actions.addWidget(tab.v138_save)

    tab.v138_use = QPushButton("🚀 Utiliser pour l’entraînement")
    tab.v138_use.setEnabled(False)
    actions.addWidget(tab.v138_use)

    tab.v138_open = QPushButton("📁 Ouvrir le dossier datasets")
    actions.addWidget(tab.v138_open)
    actions.addStretch()
    root.addLayout(actions)

    tab.v138_rows = []
    tab.v138_rejected = []
    tab.v138_saved = ""

    def choose():
        path, _ = QFileDialog.getOpenFileName(
            tab,
            "Choisir un dataset",
            "",
            "Datasets (*.jsonl *.json);;JSONL (*.jsonl);;JSON (*.json)",
        )
        if path:
            tab.v138_path.setText(path)
            analyze()

    def analyze():
        path = tab.v138_path.text().strip()
        if not path:
            tab.v138_stats.setText("Choisissez un dataset.")
            return
        try:
            raw = _load_any(path)
            clean, rejected, duplicates, too_long = _clean(
                raw,
                tab.v138_max_chars.value(),
                tab.v138_dedupe.isChecked(),
                tab.v138_remove_long.isChecked(),
            )
        except Exception as exc:
            tab.v138_stats.setText("❌ " + str(exc))
            tab.v138_rows = []
            tab.v138_save.setEnabled(False)
            tab.v138_use.setEnabled(False)
            return

        tab.v138_rows = clean
        tab.v138_rejected = rejected
        tab.v138_saved = ""

        lengths = [
            len(r["instruction"]) + len(r["input"]) + len(r["output"])
            for r in clean
        ]
        avg = (sum(lengths) / len(lengths)) if lengths else 0
        longest = max(lengths) if lengths else 0

        tab.v138_stats.setText(
            f"📊 Source : {len(raw)} entrée(s) · "
            f"valides après nettoyage : {len(clean)} · "
            f"doublons retirés : {duplicates} · "
            f"rejets : {len(rejected)} · "
            f"trop longs : {too_long} · "
            f"longueur moyenne : {avg:.0f} caractères · max : {longest}."
            + (
                " ✅ Suffisant pour lancer un essai."
                if len(clean) >= 10
                else " ⚠️ Moins de 10 exemples valides : entraînement impossible pour l’instant."
            )
        )

        show = clean[:100]
        tab.v138_table.setRowCount(len(show))
        for i, row in enumerate(show):
            vals = (
                str(i + 1),
                row["instruction"][:180],
                row["input"][:120],
                row["output"][:180],
            )
            for col, value in enumerate(vals):
                tab.v138_table.setItem(i, col, QTableWidgetItem(value))
        tab.v138_table.resizeColumnsToContents()
        tab.v138_table.horizontalHeader().setStretchLastSection(True)

        if rejected:
            lines = [f"Ligne {n} · {reason}" for n, reason in rejected[:100]]
            if len(rejected) > 100:
                lines.append(f"… {len(rejected) - 100} autre(s) rejet(s).")
            tab.v138_rejects.setPlainText("\n".join(lines))
        else:
            tab.v138_rejects.setPlainText("Aucun rejet.")

        tab.v138_save.setEnabled(bool(clean))
        tab.v138_use.setEnabled(False)

    def save_clean():
        if not tab.v138_rows:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        source_name = Path(tab.v138_path.text()).stem
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", source_name).strip(".-") or "dataset"
        out = _dataset_root() / f"{safe}-propre-{stamp}.jsonl"
        out.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in tab.v138_rows
            ),
            encoding="utf-8",
        )
        report = out.with_suffix(".rapport.json")
        report.write_text(
            json.dumps(
                {
                    "source": tab.v138_path.text(),
                    "output": str(out),
                    "valid_rows": len(tab.v138_rows),
                    "rejected_rows": len(tab.v138_rejected),
                    "max_chars": tab.v138_max_chars.value(),
                    "deduplicate": tab.v138_dedupe.isChecked(),
                    "remove_too_long": tab.v138_remove_long.isChecked(),
                    "rejected": [
                        {"line": n, "reason": reason}
                        for n, reason in tab.v138_rejected[:1000]
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        tab.v138_saved = str(out)
        tab.v138_use.setEnabled(len(tab.v138_rows) >= 10)
        tab.v138_stats.setText(
            tab.v138_stats.text()
            + f"\n✅ Dataset propre sauvegardé : {out}"
        )

    def use_for_training():
        if not tab.v138_saved:
            return
        tab.use_dataset(tab.v138_saved)
        tab.pages.setCurrentIndex(0)
        tab.status.setText(
            f"✅ Dataset Studio : {len(tab.v138_rows)} exemples propres sélectionnés pour Unsloth."
        )

    def open_folder():
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(_dataset_root())))

    tab.v138_choose.clicked.connect(choose)
    tab.v138_analyze.clicked.connect(analyze)
    tab.v138_save.clicked.connect(save_clean)
    tab.v138_use.clicked.connect(use_for_training)
    tab.v138_open.clicked.connect(open_folder)

    # Ré-analyse lorsque les règles changent si une source est déjà chargée.
    tab.v138_dedupe.toggled.connect(
        lambda _: analyze() if tab.v138_path.text().strip() else None
    )
    tab.v138_remove_long.toggled.connect(
        lambda _: analyze() if tab.v138_path.text().strip() else None
    )
    tab.v138_max_chars.valueChanged.connect(
        lambda _: analyze() if tab.v138_path.text().strip() else None
    )

    tab.pages.insertTab(4, page, "Dataset Studio")
    window._v138_dataset_studio = True
