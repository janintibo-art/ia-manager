"""Onglet Test de vitesse - estimations détaillées (façon llmfit) et mesures réelles, Ollama + LM Studio"""

import html
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from src.backend import benchmark as bm
from src.backend import lmstudio
from src.backend import model_registry as reg
from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import SystemAnalyzer
from src.ui import style
from src.ui.workers import FunctionWorker

COLUMNS = ["Modèle", "Source", "Paramètres", "Quantif.", "Taille", "Contexte", "Mémoire", "Mode",
           "Ajustement", "Estimé tok/s", "Mesuré tok/s", "Lecture tok/s", "1er token", "Chargement",
           "VRAM réelle", "Score"]
CONTEXTS = [2048, 4096, 8192, 16384, 32768, 65536, 131072]


class Cell(QTableWidgetItem):
    """Cellule triable : texte affiché, valeur numérique cachée pour le tri"""

    def __init__(self, text: str, value=None):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, value if value is not None else text.lower())
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole), other.data(Qt.ItemDataRole.UserRole)
        try:
            return float(a) < float(b)
        except (TypeError, ValueError):
            return str(a) < str(b)


def fmt(value: float, unit: str = "", digits: int = 1) -> str:
    return f"{value:.{digits}f}{unit}" if value else "—"


class BenchTab(QWidget):
    """Test de vitesse et d'ajustement de chaque IA sur ce PC"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.system_info: Optional[Dict] = None
        self.hw: Optional[Dict] = None
        self.profiles: List[Dict] = []
        self.estimates: Dict[str, Dict] = {}
        self.results: Dict[str, Dict] = bm.load_results()
        self.errors: Dict[str, str] = {}
        self.queue: List[Dict] = []
        self.current: Optional[Dict] = None
        self.scan_worker: Optional[FunctionWorker] = None
        self.measure_worker: Optional[FunctionWorker] = None
        self.init_ui()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("Test de vitesse")
        title.setObjectName("Title")
        root.addWidget(title)

        hw_card = QFrame()
        hw_card.setObjectName("Card")
        hl = QVBoxLayout(hw_card)
        hl.setContentsMargins(14, 10, 14, 10)
        self.hw_label = QLabel("Cliquez sur « Analyser » pour lire le matériel et les modèles.")
        self.hw_label.setWordWrap(True)
        self.hw_label.setTextFormat(Qt.TextFormat.RichText)
        hl.addWidget(self.hw_label)
        root.addWidget(hw_card)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Usage :"))
        self.usage = QComboBox()
        for key, u in bm.USAGES.items():
            self.usage.addItem(u["label"], key)
        self.usage.currentIndexChanged.connect(self.on_usage_changed)
        controls.addWidget(self.usage)
        controls.addWidget(QLabel("Contexte :"))
        self.ctx = QComboBox()
        for c in CONTEXTS:
            self.ctx.addItem(f"{c:,}".replace(",", " ") + " tokens", c)
        self.ctx.setCurrentIndex(CONTEXTS.index(8192))
        self.ctx.currentIndexChanged.connect(lambda _i: self.recompute())
        controls.addWidget(self.ctx)
        self.catalog_check = QCheckBox("Catalogue (non installés)")
        self.catalog_check.setToolTip("Ajoute les modèles du catalogue pour voir s'ils tiendraient sur ce PC")
        self.catalog_check.toggled.connect(lambda _on: self.scan())
        controls.addWidget(self.catalog_check)
        self.cold_check = QCheckBox("Mesure à froid")
        self.cold_check.setChecked(True)
        self.cold_check.setToolTip("Décharge le modèle avant la mesure, pour chronométrer aussi son chargement "
                                   "(Ollama seulement)")
        controls.addWidget(self.cold_check)
        controls.addStretch()
        self.scan_btn = QPushButton("🔄 Analyser")
        self.scan_btn.clicked.connect(self.scan)
        controls.addWidget(self.scan_btn)
        self.measure_btn = QPushButton("▶ Mesurer la sélection")
        self.measure_btn.setObjectName("Primary")
        self.measure_btn.clicked.connect(self.measure_selected)
        controls.addWidget(self.measure_btn)
        self.measure_all_btn = QPushButton("⏩ Tout mesurer")
        self.measure_all_btn.clicked.connect(self.measure_all)
        controls.addWidget(self.measure_all_btn)
        self.stop_btn = QPushButton("⏹ Arrêter")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        controls.addWidget(self.stop_btn)
        root.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.show_details)
        splitter.addWidget(self.table)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        splitter.addWidget(self.details)
        splitter.setSizes([460, 260])
        root.addWidget(splitter, 1)

        self.status = QLabel()
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    # ------------------------------------------------------------------ données
    def set_system_info(self, info: Dict):
        self.system_info = info

    def on_usage_changed(self, _i: int):
        need = bm.USAGES[self.usage.currentData()]["ctx"]
        idx = self.ctx.findData(need)
        if idx >= 0 and idx != self.ctx.currentIndex():
            self.ctx.setCurrentIndex(idx)  # recalcule via le signal
        else:
            self.recompute()

    def scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        self.status.setText("⏳ Lecture du matériel et des modèles…")
        self.scan_btn.setEnabled(False)
        info = self.system_info
        with_catalog = self.catalog_check.isChecked()
        ai = self.ai_manager

        def collect():
            sysinfo = info or SystemAnalyzer.get_system_info()
            hw = bm.hardware_profile(sysinfo)
            lm = lmstudio.list_models()
            prov = lmstudio.find_provider()
            profiles = bm.collect_profiles(ai.get_available_models(), lm,
                                           prov["id"] if prov else lmstudio.PROVIDER_ID,
                                           reg.MODELS if with_catalog else None)
            return {"hw": hw, "profiles": profiles, "lm_up": lm is not None, "info": sysinfo}

        self.scan_worker = FunctionWorker(collect)
        self.scan_worker.done.connect(self.on_scanned)
        self.scan_worker.start()

    def on_scanned(self, ok: bool, data):
        self.scan_btn.setEnabled(True)
        if not ok:
            self.status.setText(f"❌ Analyse impossible : {html.escape(str(data))}")
            return
        self.hw = data["hw"]
        self.system_info = self.system_info or data["info"]
        self.profiles = data["profiles"]
        hw = self.hw
        self.hw_label.setText(
            f"<b>🎮 {html.escape(hw['gpu_name'])}</b> · {hw['vram_gb']:.1f} Go de VRAM "
            f"({hw['vram_budget_gb']:.1f} Go utilisables) · {hw['gpu_bw']:.0f} Go/s "
            f"<span style='color:{style.TEXT_MUTED}'>({html.escape(hw['gpu_bw_source'])})</span><br>"
            f"<b>🧠 RAM</b> {hw['ram_gb']:.1f} Go ({hw['ram_budget_gb']:.1f} Go utilisables) · "
            f"{hw['ram_bw']:.0f} Go/s <span style='color:{style.TEXT_MUTED}'>"
            f"({html.escape(hw['ram_bw_source'])})</span> · ⚙️ {hw['cpu_count']} cœurs<br>"
            f"<span style='color:{style.TEXT_MUTED}'>Ollama : {sum(p['source'] == 'ollama' for p in self.profiles)} "
            f"modèle(s) · LM Studio : "
            f"{sum(p['source'] == 'lmstudio' for p in self.profiles) if data['lm_up'] else 'non lancé'}</span>")
        self.recompute()
        n = len(self.profiles)
        self.status.setText(f"✅ {n} modèle(s) analysé(s). Sélectionnez-en un pour le détail, "
                            "ou lancez une mesure réelle." if n else
                            "Aucun modèle trouvé : installez-en un, lancez LM Studio, ou cochez « Catalogue ».")

    def recompute(self):
        if not self.hw:
            return
        ctx = self.ctx.currentData()
        usage = self.usage.currentData()
        self.estimates = {p["ref"]: bm.estimate(p, self.hw, ctx, usage) for p in self.profiles}
        self.fill_table()

    def fill_table(self):
        selected = self.selected_refs()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for p in self.profiles:
            e = self.estimates.get(p["ref"])
            if not e:
                continue
            r = self.results.get(p["ref"]) or {}
            row = self.table.rowCount()
            self.table.insertRow(row)
            src = {"ollama": "💻 Ollama", "lmstudio": "🧪 LM Studio", "catalogue": "📦 Catalogue"}[p["source"]]
            params = fmt(p["params_b"], " B") + (f" ({p['active_b']:.1f} actifs)" if p.get("active_b") else "")
            vram_real = f"{r['vram_share'] * 100:.0f} %" if r.get("vram_share") is not None else "—"
            cells = [
                Cell(p["name"]), Cell(src), Cell(params, p["params_b"]),
                Cell(p.get("quant") or "—"), Cell(fmt(p["size_gb"], " Go"), p["size_gb"]),
                Cell(f"{p['max_ctx']:,}".replace(",", " ") if p.get("max_ctx") else "—", p.get("max_ctx") or 0),
                Cell(fmt(e["total_gb"], " Go"), e["total_gb"]),
                Cell(bm.MODE_LABELS[e["mode"]] + (f" {e['gpu_share'] * 100:.0f} %" if e["mode"] in
                                                  ("cpu_gpu", "moe") else "")),
                Cell(bm.FIT_LABELS[e["fit"]], ["too_tight", "marginal", "good", "perfect"].index(e["fit"])),
                Cell(fmt(e["tps"]), e["tps"]),
                Cell(fmt(r.get("gen_tps", 0)), r.get("gen_tps", 0)),
                Cell(fmt(r.get("prompt_tps", 0), digits=0), r.get("prompt_tps", 0)),
                Cell(fmt(r.get("ttft_s", 0), " s", 2), r.get("ttft_s", 0)),
                Cell(fmt(r.get("load_s", 0), " s"), r.get("load_s", 0)),
                Cell(vram_real, r.get("vram_share") or 0),
                Cell(f"{e['overall']:.0f}", e["overall"]),
            ]
            if p["ref"] in self.errors:
                cells[10] = Cell("❌ erreur", -1)
            for col, cell in enumerate(cells):
                cell.setData(Qt.ItemDataRole.UserRole + 1, p["ref"])
                self.table.setItem(row, col, cell)
        self.table.setSortingEnabled(True)
        self.table.sortItems(len(COLUMNS) - 1, Qt.SortOrder.DescendingOrder)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1) in selected:
                self.table.selectRow(row)

    def selected_refs(self) -> List[str]:
        refs = []
        for idx in self.table.selectionModel().selectedRows() if self.table.selectionModel() else []:
            item = self.table.item(idx.row(), 0)
            if item:
                refs.append(item.data(Qt.ItemDataRole.UserRole + 1))
        return refs

    def profile(self, ref: str) -> Optional[Dict]:
        return next((p for p in self.profiles if p["ref"] == ref), None)

    # ------------------------------------------------------------------ détail
    def show_details(self):
        refs = self.selected_refs()
        if not refs:
            return
        p, e = self.profile(refs[0]), self.estimates.get(refs[0])
        if not p or not e:
            return
        r = self.results.get(p["ref"]) or {}
        muted = style.TEXT_MUTED
        bars = "".join(
            f"<tr><td>{label}</td><td><b>{e['scores'][k]:.0f}</b>/100</td></tr>"
            for k, label in (("quality", "Qualité"), ("speed", "Vitesse"), ("fit", "Ajustement"),
                             ("context", "Contexte")))
        w = bm.USAGES[self.usage.currentData()]["weights"]
        weights = " · ".join(f"{label} {w[k]:.0%}" for k, label in
                             (("quality", "qualité"), ("speed", "vitesse"), ("fit", "ajustement"),
                              ("context", "contexte")))
        parts = [
            f"<h3>{html.escape(p['name'])}</h3>",
            f"<p><b>{bm.FIT_LABELS[e['fit']]}</b> · mode <b>{bm.MODE_LABELS[e['mode']]}</b> · "
            f"{e['total_gb']:.2f} Go nécessaires pour {e['ctx']} tokens de contexte "
            f"(~{e['vram_gb']:.1f} Go VRAM + ~{e['ram_gb']:.1f} Go RAM) · "
            f"<b>≈ {e['tps']:.1f} tokens/s estimés</b></p>",
            f"<table cellspacing='6'>{bars}<tr><td><b>Score global</b></td><td><b>{e['overall']:.0f}</b>/100"
            f"</td></tr></table><p style='color:{muted}'>Pondération « {self.usage.currentText()} » : "
            f"{weights}</p>",
            "<p><b>Base de calcul</b></p><ul>" + "".join(f"<li>{html.escape(b)}</li>" for b in e["basis"])
            + "</ul>",
        ]
        if p["ref"] in self.errors:
            parts.append(f"<p>❌ Dernière mesure : {html.escape(self.errors[p['ref']])}</p>")
        if r:
            gap = ""
            if r.get("gen_tps") and e["tps"]:
                diff = (r["gen_tps"] - e["tps"]) / e["tps"] * 100
                gap = f" · écart avec l'estimation : {diff:+.0f} %"
            parts.append(
                f"<p><b>Mesure réelle</b> ({html.escape(r.get('date', ''))}, contexte {r.get('ctx', '?')}"
                f"{', à froid' if r.get('cold') else ''})</p><ul>"
                f"<li>Écriture : <b>{r.get('gen_tps', 0):.1f} tokens/s</b> ({r.get('gen_tokens', 0)} tokens){gap}</li>"
                f"<li>Lecture du message : {r.get('prompt_tps', 0):.0f} tokens/s ({r.get('prompt_tokens', 0)} tokens)</li>"
                f"<li>Premier token après : {r.get('ttft_s', 0):.2f} s · chargement : {r.get('load_s', 0):.1f} s</li>"
                + (f"<li>Réellement en VRAM : {r['vram_share'] * 100:.0f} % de {r.get('mem_gb', 0):.1f} Go</li>"
                   if r.get("vram_share") is not None else "")
                + "</ul>")
        elif p["installed"]:
            parts.append(f"<p style='color:{muted}'>Pas encore mesuré : « Mesurer la sélection » lance un vrai "
                         f"test ({bm.BENCH_TOKENS} tokens).</p>")
        self.details.setHtml("".join(parts))

    # ------------------------------------------------------------------ mesures
    def measure_selected(self):
        self.start_queue([self.profile(r) for r in self.selected_refs()])

    def measure_all(self):
        self.start_queue([p for p in self.profiles if p["installed"] and
                          self.estimates.get(p["ref"], {}).get("mode") != "none"])

    def start_queue(self, profiles: List[Optional[Dict]]):
        todo = [p for p in profiles if p and p["installed"]]
        if not todo:
            self.status.setText("Sélectionnez un modèle installé (Ollama ou LM Studio) à mesurer.")
            return
        known = {p["ref"] for p in self.queue} | ({self.current["ref"]} if self.current else set())
        self.queue += [p for p in todo if p["ref"] not in known]
        self.stop_btn.setEnabled(True)
        self.next_measure()

    def next_measure(self):
        if self.current is not None:  # une mesure est déjà en cours
            return
        if not self.queue:
            self.current = None
            self.stop_btn.setEnabled(False)
            return
        self.current = self.queue.pop(0)
        ctx = self.ctx.currentData()
        rest = f" ({len(self.queue)} en attente)" if self.queue else ""
        self.status.setText(f"⏳ Mesure de {html.escape(self.current['name'])}… cela peut prendre une minute"
                            f"{rest}.")
        self.measure_worker = FunctionWorker(bm.measure, self.current, ctx, self.cold_check.isChecked())
        self.measure_worker.done.connect(self.on_measured)
        self.measure_worker.start()

    def on_measured(self, ok: bool, result):
        p = self.current or {}
        ref = p.get("ref", "")
        if ok and isinstance(result, dict):
            self.errors.pop(ref, None)
            self.results[ref] = result
            bm.save_result(ref, result)
            self.status.setText(f"✅ {html.escape(p.get('name', ''))} : {result.get('gen_tps', 0):.1f} tokens/s "
                                f"en écriture, premier token après {result.get('ttft_s', 0):.2f} s.")
        else:
            self.errors[ref] = str(result)
            self.status.setText(f"❌ {html.escape(p.get('name', ''))} : {html.escape(str(result))}")
        self.fill_table()
        self.show_details()
        self.current = None
        self.next_measure()

    def stop(self):
        self.queue.clear()
        self.stop_btn.setEnabled(False)
        if self.current:
            self.status.setText("⏹ Arrêt après la mesure en cours.")
