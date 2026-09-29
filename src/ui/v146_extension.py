"""Extension v146 : tableau de bord Chirurgie IA unifié."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ui import v142_extension as heretic_mod
from src.ui import v144_extension as ablation_mod
from src.ui import v145_extension as eris_mod


METHODS = [
    {
        "key": "obliteratus",
        "name": "Obliteratus",
        "icon": "🧪",
        "goal": "Modification guidée et intégrée",
        "when": "Quand vous voulez un flux simple avec versions, comparaison et export Ollama.",
    },
    {
        "key": "heretic",
        "name": "Heretic",
        "icon": "🔥",
        "goal": "Recherche automatique de paramètres",
        "when": "Quand vous voulez qu’Optuna explore automatiquement les réglages d’abliteration.",
    },
    {
        "key": "abliteration",
        "name": "Abliteration Lab",
        "icon": "🧬",
        "goal": "Projected / biprojected / norm-preserving",
        "when": "Quand vous voulez contrôler explicitement la géométrie de l’intervention et les couches.",
    },
    {
        "key": "erisforge",
        "name": "ErisForge",
        "icon": "⚒️",
        "goal": "Transformation comportementale générale",
        "when": "Quand vous voulez calculer une direction à partir de deux jeux d’instructions et l’atténuer ou la renforcer.",
    },
]


class SurgeryDashboard(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.build_ui()
        self.refresh_status()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🧠 Chirurgie IA")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Poste de commande commun pour Obliteratus, Heretic, Abliteration Lab et ErisForge. "
            "Ce tableau de bord ne modifie aucun modèle : il prépare les outils, transmet le modèle source "
            "et centralise les accès au benchmark et à la filiation."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        source_box = QGroupBox("1 · Modèle source commun")
        sl = QVBoxLayout(source_box)
        form = QFormLayout()
        self.model = QLineEdit()
        self.model.setPlaceholderText("Identifiant Hugging Face ou dossier local")
        form.addRow("Modèle", self.model)
        sl.addLayout(form)

        row = QHBoxLayout()
        self.pick = QPushButton("Dossier local…")
        row.addWidget(self.pick)
        self.refresh_btn = QPushButton("🔄 Actualiser l’état des moteurs")
        row.addWidget(self.refresh_btn)
        row.addStretch()
        sl.addLayout(row)
        root.addWidget(source_box)

        choose_box = QGroupBox("2 · Assistant de choix")
        cl = QVBoxLayout(choose_box)

        row = QHBoxLayout()
        row.addWidget(QLabel("Objectif"))
        self.goal = QComboBox()
        self.goal.addItem("Flux simple et intégré", "simple")
        self.goal.addItem("Optimisation automatique", "auto")
        self.goal.addItem("Contrôle géométrique fin", "geometry")
        self.goal.addItem("Créer / supprimer un comportement personnalisé", "behavior")
        row.addWidget(self.goal, 1)

        self.suggest_btn = QPushButton("✨ Proposer un outil")
        row.addWidget(self.suggest_btn)
        cl.addLayout(row)

        self.suggestion = QLabel()
        self.suggestion.setWordWrap(True)
        cl.addWidget(self.suggestion)
        root.addWidget(choose_box)

        table_box = QGroupBox("3 · Outils disponibles")
        tl = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Outil", "État", "Approche", "Quand l’utiliser", "Ouvrir"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        tl.addWidget(self.table)
        root.addWidget(table_box, 1)

        shortcuts = QGroupBox("4 · Après la chirurgie")
        ql = QHBoxLayout(shortcuts)

        self.benchmark_btn = QPushButton("📊 Benchmark")
        ql.addWidget(self.benchmark_btn)

        self.family_btn = QPushButton("🌳 Famille IA")
        ql.addWidget(self.family_btn)

        self.compare_btn = QPushButton("⚖️ Comparaison Original / Variantes")
        ql.addWidget(self.compare_btn)

        ql.addStretch()
        root.addWidget(shortcuts)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.pick.clicked.connect(self.choose_model)
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.suggest_btn.clicked.connect(self.suggest)
        self.benchmark_btn.clicked.connect(self.open_benchmark)
        self.family_btn.clicked.connect(self.open_family)
        self.compare_btn.clicked.connect(self.open_compare)

    def choose_model(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir un modèle local")
        if path:
            self.model.setText(path)

    def engine_state(self, key):
        if key == "obliteratus":
            tab = getattr(self.window, "obliteratus_tab", None)
            return tab is not None, "intégré à IA Manager"
        if key == "heretic":
            ok = heretic_mod._venv_python().is_file() and heretic_mod._heretic_exe().is_file()
            return ok, "installé" if ok else "à installer"
        if key == "abliteration":
            ok = (
                ablation_mod._venv_python().is_file()
                and (ablation_mod._source_root() / "measure.py").is_file()
                and (ablation_mod._source_root() / "sharded_ablate.py").is_file()
            )
            return ok, "installé" if ok else "à installer"
        if key == "erisforge":
            ok = eris_mod._venv_python().is_file()
            return ok, "installé" if ok else "à installer"
        return False, "inconnu"

    def tab_for(self, key):
        return {
            "obliteratus": getattr(self.window, "obliteratus_tab", None),
            "heretic": getattr(self.window, "heretic_tab", None),
            "abliteration": getattr(self.window, "abliteration_lab_tab", None),
            "erisforge": getattr(self.window, "erisforge_tab", None),
        }.get(key)

    def push_model_to(self, key):
        value = self.model.text().strip()
        if not value:
            self.status.setText("Renseignez d’abord un modèle source.")
            return

        tab = self.tab_for(key)
        if tab is None:
            self.status.setText("Onglet indisponible.")
            return

        try:
            if key == "obliteratus":
                # v126/v127 ont ajouté un champ source intégré ; on cherche les noms connus.
                target = (
                    getattr(tab, "v126_model", None)
                    or getattr(tab, "source_model", None)
                    or getattr(tab, "model_input", None)
                )
                if target is not None and hasattr(target, "setText"):
                    target.setText(value)
            elif key in ("heretic", "abliteration", "erisforge"):
                if hasattr(tab, "model"):
                    tab.model.setText(value)
        except Exception:
            pass

        self.window.tabs.setCurrentWidget(tab)
        self.status.setText(f"✅ Modèle envoyé vers {key}.")

    def refresh_status(self):
        self.table.setRowCount(len(METHODS))
        for row, method in enumerate(METHODS):
            ok, detail = self.engine_state(method["key"])
            state = ("✅ " if ok else "⚪ ") + detail

            values = [
                f"{method['icon']} {method['name']}",
                state,
                method["goal"],
                method["when"],
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

            button = QPushButton("Ouvrir")
            button.clicked.connect(
                lambda _checked=False, key=method["key"]: self.push_model_to(key)
            )
            self.table.setCellWidget(row, 4, button)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

        ready = sum(1 for m in METHODS if self.engine_state(m["key"])[0])
        self.status.setText(f"{ready}/{len(METHODS)} moteurs prêts.")

    def suggest(self):
        mapping = {
            "simple": ("Obliteratus", "Flux le plus direct pour tester une variante et l’envoyer vers Ollama."),
            "auto": ("Heretic", "Le moteur explore automatiquement ses paramètres avec Optuna."),
            "geometry": ("Abliteration Lab", "Permet de choisir projected, biprojected, norm-preserving et les couches."),
            "behavior": ("ErisForge", "Conçu pour définir une direction à partir de deux jeux d’instructions."),
        }
        name, why = mapping[self.goal.currentData()]
        self.suggestion.setText(
            f"💡 Suggestion : {name}. {why} "
            "Cette suggestion décrit le workflow, pas une garantie de résultat."
        )

    def open_benchmark(self):
        tab = getattr(self.window, "benchmark_tab", None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)

    def open_family(self):
        tab = getattr(self.window, "family_tree_tab", None)
        if tab is not None:
            try:
                tab.refresh()
            except Exception:
                pass
            self.window.tabs.setCurrentWidget(tab)

    def open_compare(self):
        heretic = getattr(self.window, "heretic_tab", None)
        if heretic is not None and hasattr(heretic, "v143_original"):
            self.window.tabs.setCurrentWidget(heretic)
            try:
                heretic.v143_reload_models()
                heretic.v143_compare_status.setText(
                    "✅ Comparateur Original / Obliteratus / Heretic prêt."
                )
            except Exception:
                pass
            return
        self.open_benchmark()


def install_v146(window):
    if getattr(window, "_v146_surgery_dashboard", False):
        return

    tab = SurgeryDashboard(window)
    window.surgery_dashboard_tab = tab

    obl = getattr(window, "obliteratus_tab", None)
    idx = window.tabs.indexOf(obl)
    insert_at = idx if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "🧠 Chirurgie IA")

    window._v146_surgery_dashboard = True
