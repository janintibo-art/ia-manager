"""Extension v147 : check-up + polish visuel de Chirurgie IA."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ui import v142_extension as heretic_mod
from src.ui import v144_extension as ablation_mod
from src.ui import v145_extension as eris_mod


METHODS = [
    {
        "key": "obliteratus",
        "name": "Obliteratus",
        "icon": "🧪",
        "goal": "Flux intégré et direct",
        "when": "Pour lancer rapidement une variante, l’exporter vers Ollama et la comparer.",
        "best_for": "Tests rapides, versions locales, navigation simple.",
    },
    {
        "key": "heretic",
        "name": "Heretic",
        "icon": "🔥",
        "goal": "Optimisation automatique",
        "when": "Pour laisser Optuna explorer les paramètres d’abliteration.",
        "best_for": "Recherche automatique, essais multiples, recherche de compromis.",
    },
    {
        "key": "abliteration",
        "name": "Abliteration Lab",
        "icon": "🧬",
        "goal": "Contrôle géométrique fin",
        "when": "Pour tester projected, biprojected et norm-preserving couche par couche.",
        "best_for": "Expérimentation méthodique, mesures puis intervention.",
    },
    {
        "key": "erisforge",
        "name": "ErisForge",
        "icon": "⚒️",
        "goal": "Transformation comportementale",
        "when": "Pour construire une direction à partir de deux jeux d’instructions.",
        "best_for": "Création, renforcement ou atténuation d’un comportement personnalisé.",
    },
]


class ToolCard(QFrame):
    def __init__(self, parent, method):
        super().__init__(parent)
        self.parent_dashboard = parent
        self.method = method
        self.setObjectName("SurgeryCard")
        self.build()

    def build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(f"{self.method['icon']} {self.method['name']}")
        name.setObjectName("SurgeryCardTitle")
        top.addWidget(name)

        self.badge = QLabel("…")
        self.badge.setObjectName("SurgeryBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setMinimumWidth(92)
        top.addStretch()
        top.addWidget(self.badge)
        lay.addLayout(top)

        subtitle = QLabel(self.method["goal"])
        subtitle.setObjectName("SurgerySubtitle")
        lay.addWidget(subtitle)

        text = QLabel(
            f"<b>Quand l’utiliser :</b> {self.method['when']}<br>"
            f"<b>Particulièrement bien pour :</b> {self.method['best_for']}"
        )
        text.setWordWrap(True)
        lay.addWidget(text)

        buttons = QHBoxLayout()
        self.open_btn = QPushButton("Ouvrir")
        self.open_btn.clicked.connect(lambda: self.parent_dashboard.push_model_to(self.method["key"]))
        buttons.addWidget(self.open_btn)

        self.prefill_btn = QPushButton("Remplir le modèle")
        self.prefill_btn.clicked.connect(lambda: self.parent_dashboard.prefill_only(self.method["key"]))
        buttons.addWidget(self.prefill_btn)

        buttons.addStretch()
        lay.addLayout(buttons)

    def update_state(self, ok, detail):
        self.badge.setText("PRÊT" if ok else "À FAIRE")
        self.badge.setProperty("state", "ok" if ok else "todo")
        self.style().unpolish(self.badge)
        self.style().polish(self.badge)
        self.setProperty("state", "ok" if ok else "todo")
        self.style().unpolish(self)
        self.style().polish(self)
        self.open_btn.setEnabled(True)
        self.prefill_btn.setEnabled(True)


class SurgeryDashboardPolished(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cards = {}
        self.setStyleSheet("""
            QFrame#HeroPanel {
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 16px;
                padding: 4px;
            }
            QFrame#KpiCard, QFrame#SurgeryCard {
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 14px;
            }
            QLabel#HeroTitle {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#KpiValue {
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#KpiLabel {
                opacity: 0.85;
            }
            QLabel#SurgeryCardTitle {
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#SurgerySubtitle {
                font-weight: 600;
                opacity: 0.88;
            }
            QLabel#SurgeryBadge[state="ok"] {
                border: 1px solid rgba(60,180,110,0.35);
                border-radius: 999px;
                padding: 5px 10px;
                font-weight: 700;
            }
            QLabel#SurgeryBadge[state="todo"] {
                border: 1px solid rgba(220,180,70,0.35);
                border-radius: 999px;
                padding: 5px 10px;
                font-weight: 700;
            }
        """)
        self.build_ui()
        self.refresh_status()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("HeroPanel")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(16, 16, 16, 16)
        hl.setSpacing(10)

        title = QLabel("🧠 Chirurgie IA")
        title.setObjectName("HeroTitle")
        hl.addWidget(title)

        intro = QLabel(
            "Centre de commande visuel pour tout le bloc chirurgie : Obliteratus, Heretic, "
            "Abliteration Lab et ErisForge. Cette vue sert à vérifier l’état, garder une présentation "
            "claire et ouvrir rapidement le bon outil sans que l’interface paraisse fouillie."
        )
        intro.setWordWrap(True)
        hl.addWidget(intro)

        root.addWidget(hero)

        # KPI cards
        kpi_row = QHBoxLayout()
        self.kpi_ready = self.make_kpi("0", "Moteurs prêts")
        self.kpi_tabs = self.make_kpi("0", "Onglets reliés")
        self.kpi_checks = self.make_kpi("0", "Contrôles OK")
        for card in (self.kpi_ready[0], self.kpi_tabs[0], self.kpi_checks[0]):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        source_box = QGroupBox("1 · Modèle source commun")
        sl = QVBoxLayout(source_box)
        form = QFormLayout()
        self.model = QLineEdit()
        self.model.setPlaceholderText("Identifiant Hugging Face ou dossier local")
        form.addRow("Modèle", self.model)
        sl.addLayout(form)

        row = QHBoxLayout()
        self.pick = QPushButton("Dossier local…")
        self.pick.clicked.connect(self.choose_model)
        row.addWidget(self.pick)
        self.refresh_btn = QPushButton("🔄 Check-up")
        self.refresh_btn.clicked.connect(self.refresh_status)
        row.addWidget(self.refresh_btn)
        row.addStretch()
        sl.addLayout(row)
        root.addWidget(source_box)

        choice_box = QGroupBox("2 · Assistant de choix")
        cl = QVBoxLayout(choice_box)

        row = QHBoxLayout()
        row.addWidget(QLabel("Objectif"))
        self.goal = QComboBox()
        self.goal.addItem("Flux simple et intégré", "simple")
        self.goal.addItem("Optimisation automatique", "auto")
        self.goal.addItem("Contrôle géométrique fin", "geometry")
        self.goal.addItem("Transformation comportementale personnalisée", "behavior")
        row.addWidget(self.goal, 1)
        self.suggest_btn = QPushButton("✨ Proposer")
        self.suggest_btn.clicked.connect(self.suggest)
        row.addWidget(self.suggest_btn)
        cl.addLayout(row)

        self.suggestion = QLabel("Choisissez un objectif puis cliquez sur « Proposer ».")
        self.suggestion.setWordWrap(True)
        cl.addWidget(self.suggestion)
        root.addWidget(choice_box)

        tools_box = QGroupBox("3 · Outils chirurgie")
        tl = QVBoxLayout(tools_box)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for idx, method in enumerate(METHODS):
            card = ToolCard(self, method)
            self.cards[method["key"]] = card
            grid.addWidget(card, idx // 2, idx % 2)

        tl.addLayout(grid)
        root.addWidget(tools_box)

        check_box = QGroupBox("4 · Check-up des liaisons")
        xl = QVBoxLayout(check_box)
        self.checks = QTableWidget(0, 3)
        self.checks.setHorizontalHeaderLabels(["Élément", "État", "Détail"])
        self.checks.verticalHeader().hide()
        self.checks.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.checks.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.checks.horizontalHeader().setStretchLastSection(True)
        xl.addWidget(self.checks)
        root.addWidget(check_box)

        shortcut_box = QGroupBox("5 · Raccourcis")
        ql = QHBoxLayout(shortcut_box)
        self.benchmark_btn = QPushButton("📊 Benchmark")
        self.benchmark_btn.clicked.connect(self.open_benchmark)
        ql.addWidget(self.benchmark_btn)

        self.family_btn = QPushButton("🌳 Famille IA")
        self.family_btn.clicked.connect(self.open_family)
        ql.addWidget(self.family_btn)

        self.compare_btn = QPushButton("⚖️ Comparateur chirurgie")
        self.compare_btn.clicked.connect(self.open_compare)
        ql.addWidget(self.compare_btn)

        ql.addStretch()
        root.addWidget(shortcut_box)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def make_kpi(self, value, label):
        frame = QFrame()
        frame.setObjectName("KpiCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        v = QLabel(value)
        v.setObjectName("KpiValue")
        lay.addWidget(v)
        l = QLabel(label)
        l.setObjectName("KpiLabel")
        lay.addWidget(l)
        return frame, v, l

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

    def prefill_only(self, key):
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
                target = (
                    getattr(tab, "v126_model", None)
                    or getattr(tab, "source_model", None)
                    or getattr(tab, "model_input", None)
                )
                if target is not None and hasattr(target, "setText"):
                    target.setText(value)
            elif hasattr(tab, "model"):
                tab.model.setText(value)
            self.status.setText(f"✅ Modèle prérempli pour {key}.")
        except Exception as exc:
            self.status.setText("Préremplissage impossible : " + str(exc))

    def push_model_to(self, key):
        self.prefill_only(key)
        tab = self.tab_for(key)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)

    def refresh_checks(self):
        rows = [
            ("Benchmark", getattr(self.window, "benchmark_tab", None) is not None, "Onglet de mesure disponible"),
            ("Famille IA", getattr(self.window, "family_tree_tab", None) is not None, "Historique / filiation des variantes"),
            ("Comparateur chirurgie", getattr(getattr(self.window, "heretic_tab", None), "v143_original", None) is not None, "Comparateur Original / Obliteratus / Heretic"),
            ("Pipeline GGUF/Ollama", getattr(self.window, "mergekit_tab", None) is not None, "Passerelle vers conversion et import"),
            ("Tableau de bord chirurgie", getattr(self.window, "surgery_dashboard_tab", None) is not None, "Vue centrale présente"),
        ]
        self.checks.setRowCount(len(rows))
        ok_count = 0
        for r, (name, ok, detail) in enumerate(rows):
            if ok:
                ok_count += 1
            self.checks.setItem(r, 0, QTableWidgetItem(name))
            self.checks.setItem(r, 1, QTableWidgetItem("✅ OK" if ok else "⚠️ À vérifier"))
            self.checks.setItem(r, 2, QTableWidgetItem(detail))
        self.checks.resizeColumnsToContents()
        return ok_count, len(rows)

    def refresh_status(self):
        ready = 0
        for method in METHODS:
            ok, detail = self.engine_state(method["key"])
            if ok:
                ready += 1
            self.cards[method["key"]].update_state(ok, detail)

        linked_tabs = sum(
            1 for method in METHODS if self.tab_for(method["key"]) is not None
        )
        ok_checks, total_checks = self.refresh_checks()

        self.kpi_ready[1].setText(str(ready))
        self.kpi_tabs[1].setText(str(linked_tabs))
        self.kpi_checks[1].setText(f"{ok_checks}/{total_checks}")

        self.status.setText(
            f"Check-up terminé : {ready}/{len(METHODS)} moteurs prêts, "
            f"{linked_tabs}/{len(METHODS)} onglets reliés, {ok_checks}/{total_checks} contrôles OK."
        )

    def suggest(self):
        mapping = {
            "simple": ("Obliteratus", "Le plus direct pour essayer une variante sans se perdre dans les réglages."),
            "auto": ("Heretic", "Le plus adapté si vous voulez que la recherche de paramètres soit automatisée."),
            "geometry": ("Abliteration Lab", "Le plus clair pour projected, biprojected et norm-preserving."),
            "behavior": ("ErisForge", "Le plus adapté pour définir une direction comportementale à partir de deux jeux d’instructions."),
        }
        name, why = mapping[self.goal.currentData()]
        self.suggestion.setText(
            f"💡 <b>Suggestion :</b> {name}. {why} "
            "Ce conseil sert à vous orienter visuellement, il ne garantit pas à lui seul le meilleur résultat."
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
        else:
            self.status.setText("Famille IA n’est pas disponible dans cette version.")

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
        else:
            self.open_benchmark()


def install_v147(window):
    if getattr(window, "_v147_surgery_polish", False):
        return

    new_tab = SurgeryDashboardPolished(window)

    old_tab = getattr(window, "surgery_dashboard_tab", None)
    if old_tab is not None:
        index = window.tabs.indexOf(old_tab)
        if index >= 0:
            window.tabs.removeTab(index)
            window.tabs.insertTab(index, new_tab, "🧠 Chirurgie IA")
        else:
            obl = getattr(window, "obliteratus_tab", None)
            idx = window.tabs.indexOf(obl)
            insert_at = idx if idx >= 0 else window.tabs.count()
            window.tabs.insertTab(insert_at, new_tab, "🧠 Chirurgie IA")
    else:
        obl = getattr(window, "obliteratus_tab", None)
        idx = window.tabs.indexOf(obl)
        insert_at = idx if idx >= 0 else window.tabs.count()
        window.tabs.insertTab(insert_at, new_tab, "🧠 Chirurgie IA")

    window.surgery_dashboard_tab = new_tab
    window._v147_surgery_polish = True
