"""Onglet Analyse - analyse du PC, répartition VRAM/RAM, modèles conseillés"""

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSlider, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg
from src.backend import settings
from src.backend.model_options import PRIORITY_TO_MODE
from src.backend.ai_manager import AIManager
from src.backend.allocation import AllocationCalculator
from src.backend.system_analyzer import SystemAnalyzer
from src.ui import style
from src.ui.workers import DownloadWorker

PRIORITIES = [
    ("Rapidité maximale", "⚡ Rapidité",
     "Des réponses quasi instantanées : on choisit des modèles qui tiennent entièrement dans la carte graphique."),
    ("Équilibré", "⚖️ Équilibré",
     "Le meilleur compromis : le plus gros modèle qui reste fluide sur votre PC."),
    ("Qualité maximale", "🏆 Qualité",
     "Les meilleures réponses possibles : le modèle peut déborder dans la RAM, ce qui le rend plus lent."),
]


def make_card(title: str):
    """Petite carte avec un titre et une grande valeur"""
    card = QFrame()
    card.setObjectName("Card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    t = QLabel(title)
    t.setObjectName("Muted")
    v = QLabel("—")
    v.setObjectName("BigValue")
    v.setWordWrap(True)
    d = QLabel("")
    d.setObjectName("Muted")
    d.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(v)
    lay.addWidget(d)
    lay.addStretch()
    return card, v, d


class SetupTab(QWidget):
    """Analyse du PC et recommandations"""

    analysis_done = pyqtSignal(dict)
    models_changed = pyqtSignal()
    show_model = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.analyzer = SystemAnalyzer()
        self.allocator = AllocationCalculator()
        self.ai_manager = AIManager()
        self.info: Optional[Dict] = None
        self.installed: List[str] = []
        self.download_worker: Optional[DownloadWorker] = None
        self.init_ui()
        # Analyse automatique dès que la fenêtre est affichée
        QTimer.singleShot(200, self.analyze_system)

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(14)

        # En-tête
        head = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Analyse de votre PC")
        title.setObjectName("Title")
        subtitle = QLabel("On mesure votre matériel pour vous conseiller les IA les plus adaptées.")
        subtitle.setObjectName("Subtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        head.addLayout(titles, 1)
        self.analyze_btn = QPushButton("🔍  Relancer l'analyse")
        self.analyze_btn.setObjectName("Primary")
        self.analyze_btn.clicked.connect(self.analyze_system)
        head.addWidget(self.analyze_btn, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        # Cartes matériel
        grid = QGridLayout()
        grid.setSpacing(12)
        c1, self.cpu_value, self.cpu_desc = make_card("🖥️  Processeur")
        c2, self.ram_value, self.ram_desc = make_card("💾  Mémoire vive (RAM)")
        c3, self.gpu_value, self.gpu_desc = make_card("🎮  Carte graphique")
        c4, self.vram_value, self.vram_desc = make_card("⚡  Mémoire vidéo (VRAM)")
        for i, c in enumerate((c1, c2, c3, c4)):
            grid.addWidget(c, 0, i)
        root.addLayout(grid)

        self.verdict = QLabel("")
        self.verdict.setWordWrap(True)
        self.verdict.setObjectName("Muted")
        root.addWidget(self.verdict)

        # Priorité
        prio_card = QFrame()
        prio_card.setObjectName("Card")
        prio_lay = QVBoxLayout(prio_card)
        prio_lay.setContentsMargins(18, 16, 18, 16)
        pt = QLabel("Que préférez-vous ?")
        pt.setObjectName("CardTitle")
        prio_lay.addWidget(pt)

        radios = QHBoxLayout()
        self.prio_group = QButtonGroup(self)
        for i, (_key, label, _desc) in enumerate(PRIORITIES):
            rb = QRadioButton(label)
            self.prio_group.addButton(rb, i)
            radios.addWidget(rb)
            saved_mode = settings.get("default_mode") or "balanced"
            if PRIORITY_TO_MODE.get(PRIORITIES[i][0]) == saved_mode:
                rb.setChecked(True)
        if self.prio_group.checkedId() < 0:
            self.prio_group.button(1).setChecked(True)
        radios.addStretch()
        self.prio_group.idClicked.connect(lambda _id: self.update_all())
        prio_lay.addLayout(radios)

        self.prio_desc = QLabel()
        self.prio_desc.setObjectName("Muted")
        self.prio_desc.setWordWrap(True)
        prio_lay.addWidget(self.prio_desc)
        root.addWidget(prio_card)

        # Recommandations
        reco_card = QFrame()
        reco_card.setObjectName("Card")
        reco_lay = QVBoxLayout(reco_card)
        reco_lay.setContentsMargins(18, 16, 18, 16)
        rt = QLabel("💡  Modèles conseillés pour votre PC")
        rt.setObjectName("CardTitle")
        reco_lay.addWidget(rt)
        rs = QLabel("Le meilleur choix dans chaque catégorie selon votre matériel et votre préférence.")
        rs.setObjectName("Muted")
        rs.setWordWrap(True)
        reco_lay.addWidget(rs)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Catégorie", "Modèle conseillé", "Taille", "Sur ce PC", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(360)
        reco_lay.addWidget(self.table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        reco_lay.addWidget(self.progress_bar)
        self.status_label = QLabel()
        self.status_label.setObjectName("Status")
        self.status_label.setWordWrap(True)
        reco_lay.addWidget(self.status_label)
        root.addWidget(reco_card)

        # Répartition VRAM / RAM
        alloc_card = QFrame()
        alloc_card.setObjectName("Card")
        alloc_lay = QVBoxLayout(alloc_card)
        alloc_lay.setContentsMargins(18, 16, 18, 16)
        at = QLabel("⚙️  Répartition de la mémoire (VRAM / RAM)")
        at.setObjectName("CardTitle")
        alloc_lay.addWidget(at)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Part de la VRAM utilisée :"))
        self.vram_slider = QSlider(Qt.Orientation.Horizontal)
        self.vram_slider.setRange(0, 100)
        self.vram_slider.setValue(int(settings.get("vram_percent") or 90))
        self.vram_slider.valueChanged.connect(self.update_allocation)
        slider_row.addWidget(self.vram_slider, 1)
        self.vram_label = QLabel(f"{self.vram_slider.value()} %")
        self.vram_label.setMinimumWidth(60)
        slider_row.addWidget(self.vram_label)
        alloc_lay.addLayout(slider_row)

        self.alloc_text = QLabel()
        self.alloc_text.setWordWrap(True)
        self.alloc_text.setTextFormat(Qt.TextFormat.RichText)
        alloc_lay.addWidget(self.alloc_text)
        root.addWidget(alloc_card)

        root.addStretch()

    # ------------------------------------------------------------ logique
    def priority_key(self) -> str:
        idx = max(0, self.prio_group.checkedId())
        return PRIORITIES[idx][0]

    def refresh_installed(self):
        self.installed = self.ai_manager.get_available_models()
        self.update_recommendations()

    def analyze_system(self):
        try:
            info = self.analyzer.get_system_info()
        except Exception as e:
            self.verdict.setText(f"❌ Analyse impossible : {e}")
            return
        self.info = info

        self.cpu_value.setText(f"{info['cpu_count']} cœurs")
        self.cpu_desc.setText(info["cpu"] or "")
        self.ram_value.setText(f"{info['ram_gb']:.0f} Go")
        self.ram_desc.setText(f"{info['ram_available_gb']:.1f} Go libres actuellement")
        self.gpu_value.setText(info["gpu_vendor"])
        self.gpu_desc.setText(info["gpu_type"])
        if info["vram_gb"] > 0:
            self.vram_value.setText(f"{info['vram_gb']:.1f} Go")
            self.vram_desc.setText("Mesure exacte" if info.get("vram_exact", True)
                                   else "Valeur Windows, peut être plafonnée à 4 Go")
        else:
            self.vram_value.setText("Aucune")
            self.vram_desc.setText("Les IA tourneront sur le processeur")

        self.verdict.setText("  ·  ".join(self.analyzer.get_recommendations(info)))

        self.installed = self.ai_manager.get_available_models()
        self.update_all()
        self.analysis_done.emit(info)

    def update_all(self):
        idx = max(0, self.prio_group.checkedId())
        self.prio_desc.setText(PRIORITIES[idx][2])
        settings.set("default_mode", PRIORITY_TO_MODE.get(PRIORITIES[idx][0], "balanced"))
        self.update_recommendations()
        self.update_allocation()

    def update_recommendations(self):
        if not self.info:
            return
        recos = reg.recommend(self.info, self.priority_key())
        busy = self.download_worker is not None and self.download_worker.isRunning()

        self.table.setRowCount(len(reg.RECO_CATEGORIES))
        for row, cat_key in enumerate(reg.RECO_CATEGORIES):
            cat = reg.CATEGORIES[cat_key]
            model = recos.get(cat_key)
            self.table.setItem(row, 0, QTableWidgetItem(cat["label"]))
            if model is None:
                self.table.setItem(row, 1, QTableWidgetItem("Aucun modèle adapté à ce PC"))
                self.table.setItem(row, 2, QTableWidgetItem(""))
                self.table.setItem(row, 3, QTableWidgetItem(""))
                self.table.setCellWidget(row, 4, QWidget())
                continue

            name_item = QTableWidgetItem(model["name"])
            name_item.setToolTip(model["desc"])
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(f"~{model['size_gb']:.1f} Go"))
            icon, fit_title, fit_text = reg.FIT_LABELS[reg.evaluate_fit(model, self.info)]
            fit_item = QTableWidgetItem(f"{icon} {fit_title}")
            fit_item.setToolTip(fit_text)
            self.table.setItem(row, 3, fit_item)

            actions = QWidget()
            actions.setStyleSheet("background: transparent;")
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(4, 2, 4, 2)
            lay.setSpacing(6)
            info_btn = QPushButton("Fiche")
            info_btn.clicked.connect(lambda _c, mid=model["id"]: self.show_model.emit(mid))
            lay.addWidget(info_btn)
            if model["id"] in self.installed:
                done = QLabel("✔ Installé")
                done.setStyleSheet(f"color: {style.GREEN}; background: transparent;")
                lay.addWidget(done)
            else:
                dl_btn = QPushButton("⬇ Télécharger")
                dl_btn.setObjectName("Primary")
                dl_btn.setEnabled(not busy)
                dl_btn.clicked.connect(lambda _c, mid=model["id"]: self.download(mid))
                lay.addWidget(dl_btn)
            self.table.setCellWidget(row, 4, actions)

        self.table.resizeRowsToContents()
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, max(self.table.rowHeight(row), 56))

    def update_allocation(self):
        vram_percent = self.vram_slider.value()
        self.vram_label.setText(f"{vram_percent} %")
        if int(settings.get("vram_percent") or 90) != vram_percent:
            settings.set("vram_percent", vram_percent)
        priority = self.priority_key()
        a = self.allocator.calculate_allocation(vram_percent=vram_percent, priority=priority)
        self.alloc_text.setText(
            f"<p>🎮 <b>VRAM (carte graphique) :</b> {a['vram_mb'] / 1024:.1f} Go"
            f" &nbsp;&nbsp; 💾 <b>RAM :</b> {a['ram_mb'] / 1024:.1f} Go"
            f" &nbsp;&nbsp; 📦 <b>Taille de modèle max :</b> {a['max_model_gb']:.1f} Go</p>"
            f"<p style='color:{style.TEXT_MUTED}'>💡 {a['advice']}</p>"
            f"<p style='color:{style.GREEN}'>✅ Ce réglage est réellement appliqué à toutes les IA locales "
            f"(couches en VRAM et mémoire de conversation envoyées à Ollama). Pour régler un modèle "
            f"en particulier : bouton ⚙️ à côté du choix de l'IA dans le Chat.</p>"
        )

    # ---------------------------------------------------- téléchargement
    def download(self, model_id: str):
        model = reg.get_model(model_id)
        if not model:
            return
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(
                self, "Ollama absent",
                "Ollama doit être installé et lancé pour télécharger des modèles.\n"
                "Téléchargement : https://ollama.com",
            )
            return
        self.progress_bar.setVisible(True)
        self.status_label.setText(
            f"Téléchargement de {model['name']} (~{model['size_gb']:.1f} Go)… "
            "cela peut prendre plusieurs minutes."
        )
        self.download_worker = DownloadWorker(self.ai_manager, model_id)
        self.download_worker.finished_ok.connect(self.on_download_finished)
        self.download_worker.start()
        # Reconstruire le tableau après le clic (le bouton cliqué est dans le tableau)
        QTimer.singleShot(0, self.update_recommendations)

    def on_download_finished(self, success: bool, error: str):
        self.progress_bar.setVisible(False)
        if success:
            self.status_label.setText("✅ Téléchargement terminé ! Le modèle est disponible dans le Chat.")
            self.models_changed.emit()
        else:
            self.status_label.setText(f"❌ Échec du téléchargement : {error}")
        self.refresh_installed()
