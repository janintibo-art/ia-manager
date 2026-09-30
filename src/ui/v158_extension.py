"""v158 : Bibliothèque IA intelligente."""
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg, storage
from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import SystemAnalyzer


def _cat(model):
    key = model.get("category")
    return reg.CATEGORIES.get(key, {}).get("label", "Autre") if key else "Autre"


def _fit_label(model, info):
    if not model:
        return "⚪ Inconnu", ""
    try:
        details = reg.compatibility_details(model, info)
        fit = details.get("fit")
        need = details.get("need_gb")
    except Exception:
        return "⚪ Inconnu", ""
    labels = {
        "gpu": "✅ GPU",
        "mixed": "⚠️ VRAM + RAM",
        "cpu": "🐢 CPU/RAM",
        "no": "❌ Trop gros",
        None: "⚪ À vérifier",
    }
    return labels.get(fit, "⚪ À vérifier"), (f"~{need:.1f} Go mémoire" if need is not None else "")


def _source(model, installed):
    if model and installed:
        return "Ollama · catalogue IA Manager"
    if model:
        return "Catalogue IA Manager"
    return "Ollama · hors catalogue"


def _quant(model_id):
    text = (model_id or "").lower()
    # Seulement si le tag lui-même contient explicitement une quantification.
    for token in ("q2_k", "q3_k_m", "q4_k_m", "q4_0", "q5_k_m", "q5_0", "q6_k", "q8_0"):
        if token in text:
            return token.upper()
    return "Gérée par Ollama"


class SmartLibraryTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.ai = AIManager()
        try:
            self.info = SystemAnalyzer.get_system_info()
        except Exception:
            self.info = None
        self.rows = []
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("📚 Bibliothèque IA intelligente")
        title.setObjectName("Title")
        root.addWidget(title)

        subtitle = QLabel(
            "Vue de gestion : spécialité, taille, compatibilité matérielle, source, quantification "
            "et état d'installation. Les informations inconnues restent explicitement marquées."
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Rechercher nom, éditeur, spécialité…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filters)
        filters.addWidget(self.search, 2)

        self.category = QComboBox()
        self.category.addItem("Toutes les spécialités", "")
        for key, value in reg.CATEGORIES.items():
            self.category.addItem(value["label"], key)
        self.category.currentIndexChanged.connect(self.apply_filters)
        filters.addWidget(self.category, 1)

        self.install_filter = QComboBox()
        self.install_filter.addItem("Tous", "all")
        self.install_filter.addItem("Installés", "installed")
        self.install_filter.addItem("Non installés", "not_installed")
        self.install_filter.currentIndexChanged.connect(self.apply_filters)
        filters.addWidget(self.install_filter)

        self.compat = QComboBox()
        self.compat.addItem("Toute compatibilité", "")
        self.compat.addItem("✅ GPU", "gpu")
        self.compat.addItem("⚠️ VRAM + RAM", "mixed")
        self.compat.addItem("🐢 CPU/RAM", "cpu")
        self.compat.addItem("❌ Trop gros", "no")
        self.compat.currentIndexChanged.connect(self.apply_filters)
        filters.addWidget(self.compat)

        refresh = QPushButton("🔄 Actualiser")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(refresh)
        root.addLayout(filters)

        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Modèle", "Installé", "Spécialité", "Taille", "Compatibilité",
            "Mémoire estimée", "Quantification", "Licence", "Source", "Idéal pour",
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.update_actions)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.details_btn = QPushButton("📄 Voir la fiche")
        self.details_btn.clicked.connect(self.open_details)
        actions.addWidget(self.details_btn)

        self.chat_btn = QPushButton("💬 Ouvrir dans Chat")
        self.chat_btn.clicked.connect(self.open_chat)
        actions.addWidget(self.chat_btn)

        self.bench_btn = QPushButton("📊 Benchmark")
        self.bench_btn.clicked.connect(self.open_benchmark)
        actions.addWidget(self.bench_btn)

        self.folder_btn = QPushButton("📁 Dossier Ollama")
        self.folder_btn.clicked.connect(self.open_folder)
        actions.addWidget(self.folder_btn)

        self.download_btn = QPushButton("⬇ Télécharger")
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self.download_selected)
        actions.addWidget(self.download_btn)

        actions.addStretch()
        root.addLayout(actions)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh(self):
        try:
            installed = list(self.ai.get_available_models(force=True))
        except Exception:
            installed = []

        installed_set = set(installed)
        known = {m["id"]: m for m in reg.MODELS}
        rows = []

        for model in reg.MODELS:
            fit, need = _fit_label(model, self.info)
            rows.append({
                "id": model["id"],
                "model": model,
                "installed": model["id"] in installed_set,
                "category_key": model.get("category") or "",
                "category": _cat(model),
                "size": float(model.get("size_gb") or 0),
                "fit": fit,
                "fit_key": (reg.compatibility_details(model, self.info).get("fit") if self.info else ""),
                "need": need,
                "quant": _quant(model["id"]),
                "license": "Non renseignée",
                "source": _source(model, model["id"] in installed_set),
                "ideal": model.get("ideal") or "",
                "editor": model.get("editor") or "",
            })

        for name in installed:
            if name in known:
                continue
            rows.append({
                "id": name,
                "model": None,
                "installed": True,
                "category_key": "",
                "category": "Autre / hors catalogue",
                "size": 0.0,
                "fit": "⚪ Inconnu",
                "fit_key": "",
                "need": "",
                "quant": _quant(name),
                "license": "Non renseignée",
                "source": "Ollama · hors catalogue",
                "ideal": "Modèle installé manuellement.",
                "editor": "",
            })

        self.rows = rows
        self.apply_filters()

    def filtered(self):
        text = self.search.text().strip().lower()
        cat = self.category.currentData()
        inst = self.install_filter.currentData()
        compat = self.compat.currentData()

        out = []
        for row in self.rows:
            if cat and row["category_key"] != cat:
                continue
            if inst == "installed" and not row["installed"]:
                continue
            if inst == "not_installed" and row["installed"]:
                continue
            if compat and row["fit_key"] != compat:
                continue
            hay = " ".join([
                row["id"], row["category"], row["ideal"], row["editor"], row["source"]
            ]).lower()
            if text and text not in hay:
                continue
            out.append(row)
        return out

    def apply_filters(self):
        rows = self.filtered()
        self.table.setRowCount(len(rows))
        installed_count = 0

        for r, row in enumerate(rows):
            if row["installed"]:
                installed_count += 1
            model = row["model"]
            name = model.get("name") if model else row["id"]
            values = [
                name,
                "✅ Oui" if row["installed"] else "—",
                row["category"],
                f"~{row['size']:.1f} Go" if row["size"] else "Inconnue",
                row["fit"],
                row["need"] or "Non calculée",
                row["quant"],
                row["license"],
                row["source"],
                row["ideal"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(r, c, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.summary.setText(
            f"{len(rows)} modèle(s) affiché(s) · {installed_count} installé(s) dans cette vue."
        )
        self.update_actions()

    def current(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        model_id = item.data(Qt.ItemDataRole.UserRole)
        return next((x for x in self.rows if x["id"] == model_id), None)

    def update_actions(self):
        row = self.current()
        has = row is not None
        installed = bool(row and row["installed"])
        self.details_btn.setEnabled(has)
        self.chat_btn.setEnabled(installed)
        self.bench_btn.setEnabled(installed)
        self.download_btn.setEnabled(bool(row and not installed and row["model"] is not None))

    def open_details(self):
        row = self.current()
        if not row:
            return
        tab = getattr(self.window, "models_tab", None)
        if tab is not None:
            try:
                tab.select_model(row["id"])
            except Exception:
                pass
            self.window.tabs.setCurrentWidget(tab)

    def open_chat(self):
        row = self.current()
        if not row or not row["installed"]:
            return
        tab = getattr(self.window, "chat_tab", None)
        if tab is None:
            return
        try:
            tab.refresh_models()
            tab.select_ref(row["id"])
        except Exception:
            pass
        self.window.tabs.setCurrentWidget(tab)

    def open_benchmark(self):
        row = self.current()
        tab = getattr(self.window, "benchmark_tab", None)
        if tab is None:
            return
        try:
            tab.refresh_models()
            target = row["id"] if row else ""
            for i in range(tab.models.count()):
                item = tab.models.item(i)
                item.setCheckState(
                    Qt.CheckState.Checked if item.text() == target else Qt.CheckState.Unchecked
                )
        except Exception:
            pass
        self.window.tabs.setCurrentWidget(tab)

    def open_folder(self):
        path = storage.ollama_models()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def download_selected(self):
        row = self.current()
        if not row or row["installed"] or row["model"] is None:
            return
        tab = getattr(self.window, "models_tab", None)
        if tab is None:
            return
        try:
            tab.select_model(row["id"])
            self.window.tabs.setCurrentWidget(tab)
            self.status.setText("Fiche ouverte dans Modèles : utilisez Télécharger pour confirmer.")
        except Exception as exc:
            self.status.setText("Ouverture impossible : " + str(exc))


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "ACCUEIL":
                pos = next((i for i, e in enumerate(entries) if e[0] == "models_tab"), len(entries)-1)
                if not any(e[0] == "smart_library_tab" for e in entries):
                    entries.insert(pos + 1, (
                        "smart_library_tab",
                        "Bibliothèque IA",
                        "Gérez modèles, compatibilité, spécialités et actions rapides."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass

    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v158(window):
    if getattr(window, "_v158_smart_library", False):
        return

    tab = SmartLibraryTab(window)
    window.smart_library_tab = tab

    models = getattr(window, "models_tab", None)
    idx = window.tabs.indexOf(models)
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "📚 Bibliothèque IA")

    _add_nav(window)
    window._v158_smart_library = True
