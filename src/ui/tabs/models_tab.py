"""Onglet Modèles - catalogue classé par catégorie, fiches détaillées, téléchargement"""

import html
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QSplitter, QTextBrowser,
    QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg
from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import SystemAnalyzer
from src.ui import style
from src.ui.workers import DownloadWorker

INSTALLED_FILTER = "__installed__"
DISCOVERY_FILTER = "__discovery__"


def stars(n: int, total: int = 5) -> str:
    return "★" * n + "☆" * (total - n)


class ModelsTab(QWidget):
    """Catalogue des modèles"""

    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.download_worker: Optional[DownloadWorker] = None
        self.installed: List[str] = []
        self.current_filter: Optional[str] = None
        self.current_id: Optional[str] = None
        try:
            self.system_info: Optional[Dict] = SystemAnalyzer.get_system_info()
        except Exception:
            self.system_info = None

        self.init_ui()
        self.refresh_installed_models()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("Catalogue des modèles")
        title.setObjectName("Title")
        root.addWidget(title)
        subtitle = QLabel("Choisissez une catégorie, puis un modèle pour voir sa fiche. 🔍 = modèle moins connu. "
                          "✅ rapide sur ce PC · ⚠️ plus lent · 🐢 lent (sans carte graphique) · ❌ trop gros")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self.category_desc = QLabel()
        self.category_desc.setObjectName("Muted")
        self.category_desc.setWordWrap(True)
        root.addWidget(self.category_desc)

        # Catégories | liste | fiche
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(210)
        self.category_list.setMaximumWidth(270)
        self.filters = [(None, "📚 Tous")] + [(k, v["label"]) for k, v in reg.CATEGORIES.items()]
        self.filters += [(DISCOVERY_FILTER, "🔍 Découvertes"), (INSTALLED_FILTER, "✔ Installés")]
        for key, label in self.filters:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.category_list.addItem(item)
        self.category_list.currentRowChanged.connect(self.on_category_changed)
        splitter.addWidget(self.category_list)

        middle = QWidget()
        middle_lay = QVBoxLayout(middle)
        middle_lay.setContentsMargins(0, 0, 0, 0)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Rechercher (nom, éditeur, usage…)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self.populate_list())
        search_row.addWidget(self.search, 1)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Actualiser les modèles installés")
        refresh_btn.clicked.connect(self.refresh_installed_models)
        search_row.addWidget(refresh_btn)
        middle_lay.addLayout(search_row)
        self.model_list = QListWidget()
        self.model_list.currentItemChanged.connect(self.on_item_changed)
        middle_lay.addWidget(self.model_list, 1)
        splitter.addWidget(middle)

        detail_card = QFrame()
        detail_card.setObjectName("Card")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(16, 16, 16, 16)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        self.detail.setStyleSheet("border: none; background: transparent;")
        detail_layout.addWidget(self.detail, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        detail_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        self.status_label.setObjectName("Status")
        self.status_label.setWordWrap(True)
        detail_layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.download_btn = QPushButton("⬇  Télécharger")
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self.download_model)
        buttons.addWidget(self.download_btn)
        self.delete_btn = QPushButton("🗑  Supprimer")
        self.delete_btn.setObjectName("Danger")
        self.delete_btn.clicked.connect(self.delete_model)
        buttons.addWidget(self.delete_btn)
        buttons.addStretch()
        detail_layout.addLayout(buttons)

        splitter.addWidget(detail_card)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([230, 430, 620])
        root.addWidget(splitter, 1)

        self.category_list.blockSignals(True)
        self.category_list.setCurrentRow(0)
        self.category_list.blockSignals(False)

    # ------------------------------------------------------------ données
    def set_system_info(self, info: Dict):
        """Appelé après l'analyse du PC : met à jour les pastilles de compatibilité"""
        self.system_info = info
        self.populate_list()

    def on_category_changed(self, row: int):
        if 0 <= row < len(self.filters):
            self.set_filter(self.filters[row][0])

    def update_category_counts(self):
        for i, (key, label) in enumerate(self.filters):
            if key is None:
                n = len(reg.MODELS)
            elif key == INSTALLED_FILTER:
                n = len(self.installed)
            elif key == DISCOVERY_FILTER:
                n = sum(1 for m in reg.MODELS if m.get("discovery"))
            else:
                n = len(reg.models_in(key))
            self.category_list.item(i).setText(f"{label}  ({n})")

    def set_filter(self, key: Optional[str]):
        self.current_filter = key
        self.update_category_counts()
        if key is None:
            self.category_desc.setText(f"{len(reg.MODELS)} modèles au total, toutes catégories confondues.")
        elif key == DISCOVERY_FILTER:
            self.category_desc.setText("Modèles moins connus mais intéressants : petits éditeurs, laboratoires "
                                       "de recherche, modèles spécialisés. À essayer !")
        elif key == INSTALLED_FILTER:
            self.category_desc.setText("Modèles déjà téléchargés sur ce PC.")
        else:
            self.category_desc.setText(reg.CATEGORIES[key]["desc"])
        self.populate_list()

    def refresh_installed_models(self):
        self.installed = self.ai_manager.get_available_models()
        self.set_filter(self.current_filter)

    def is_installed(self, model_id: str) -> bool:
        return model_id in self.installed

    def visible_models(self) -> List[Dict]:
        if self.current_filter == INSTALLED_FILTER:
            models = [m for m in reg.MODELS if self.is_installed(m["id"])]
            known = {m["id"] for m in reg.MODELS}
            for name in self.installed:
                if name not in known:
                    models.append({"id": name, "name": name, "category": None, "extra": True})
            return self.apply_search(models)
        if self.current_filter == DISCOVERY_FILTER:
            return self.apply_search([m for m in reg.MODELS if m.get("discovery")])
        return self.apply_search(reg.models_in(self.current_filter))

    def apply_search(self, models: List[Dict]) -> List[Dict]:
        text = self.search.text().strip().lower() if hasattr(self, "search") else ""
        if not text:
            return models
        out = []
        for m in models:
            hay = " ".join(str(m.get(k, "")) for k in ("id", "name", "editor", "desc", "ideal"))
            if text in hay.lower():
                out.append(m)
        return out

    def populate_list(self):
        keep = self.current_id
        self.model_list.blockSignals(True)
        self.model_list.clear()

        models = self.visible_models()
        for m in models:
            if m.get("extra"):
                text = f"✔  {m['name']}\n      Installé hors catalogue"
            else:
                icon = reg.FIT_LABELS[reg.evaluate_fit(m, self.system_info)][0]
                inst = "   ✔ installé" if self.is_installed(m["id"]) else ""
                if m.get("discovery"):
                    inst = "  🔍" + inst
                cat = reg.CATEGORIES[m["category"]]["label"]
                text = (f"{icon}  {m['name']}{inst}\n"
                        f"      {cat} · {m['params']} · ~{m['size_gb']:.1f} Go")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.model_list.addItem(item)

        self.model_list.blockSignals(False)

        if not models:
            self.current_id = None
            self.detail.setHtml(self.empty_html())
            self.update_buttons()
            return

        row = 0
        for i in range(self.model_list.count()):
            if self.model_list.item(i).data(Qt.ItemDataRole.UserRole) == keep:
                row = i
                break
        self.model_list.setCurrentRow(row)
        self.on_item_changed(self.model_list.currentItem(), None)

    def select_model(self, model_id: str):
        """Afficher la fiche d'un modèle précis (depuis l'onglet Analyse)"""
        self.current_id = model_id
        self.search.clear()
        self.category_list.blockSignals(True)
        self.category_list.setCurrentRow(0)
        self.category_list.blockSignals(False)
        self.set_filter(None)

    # ------------------------------------------------------------ fiche
    def on_item_changed(self, current, _previous):
        if current is None:
            return
        self.current_id = current.data(Qt.ItemDataRole.UserRole)
        model = reg.get_model(self.current_id)
        if model:
            self.detail.setHtml(self.model_html(model))
        else:
            self.detail.setHtml(
                f"<h2>{html.escape(self.current_id)}</h2>"
                f"<p style='color:{style.TEXT_MUTED}'>Modèle installé qui ne fait pas partie du "
                f"catalogue. Il est utilisable dans l'onglet Chat.</p>"
            )
        self.update_buttons()

    def update_buttons(self):
        busy = self.download_worker is not None and self.download_worker.isRunning()
        has = self.current_id is not None
        installed = has and self.is_installed(self.current_id)
        in_catalog = has and reg.get_model(self.current_id) is not None
        self.download_btn.setVisible(in_catalog and not installed)
        self.download_btn.setEnabled(not busy)
        self.delete_btn.setVisible(installed)
        self.delete_btn.setEnabled(not busy)

    def empty_html(self) -> str:
        if self.current_filter == INSTALLED_FILTER:
            if not self.ai_manager.is_ollama_running():
                return ("<h2>Ollama n'est pas lancé</h2>"
                        "<p>Installez Ollama depuis <a href='https://ollama.com'>ollama.com</a>, "
                        "lancez-le, puis cliquez sur Actualiser.</p>")
            return "<h2>Aucun modèle installé</h2><p>Choisissez une catégorie pour en télécharger un.</p>"
        return "<p>Aucun modèle dans cette catégorie.</p>"

    def model_html(self, m: Dict) -> str:
        fit = reg.evaluate_fit(m, self.system_info)
        icon, fit_title, fit_text = reg.FIT_LABELS[fit]
        fit_color = {"gpu": style.GREEN, "mixed": style.ORANGE,
                     "cpu": style.ORANGE, "no": style.RED}[fit]
        need = reg.memory_needed_gb(m)
        cat = reg.CATEGORIES[m["category"]]
        installed = self.is_installed(m["id"])

        if self.system_info:
            vram = self.system_info.get("vram_gb", 0.0)
            ram = self.system_info.get("ram_gb", 0.0)
            pc_line = f"Votre PC : {vram:.1f} Go de VRAM, {ram:.0f} Go de RAM."
        else:
            pc_line = "Lancez l'analyse du PC pour une évaluation précise."

        strengths = "".join(f"<li>{html.escape(s)}</li>" for s in m["strengths"])
        weaknesses = "".join(f"<li>{html.escape(s)}</li>" for s in m["weaknesses"])
        muted = style.TEXT_MUTED

        def row(label, value):
            return (f"<tr><td style='color:{muted}; padding:5px 18px 5px 0'>{label}</td>"
                    f"<td style='padding:5px 0'><b>{value}</b></td></tr>")

        installed_badge = (f" &nbsp;<span style='color:{style.GREEN}'>✔ installé</span>"
                           if installed else "")
        if m.get("discovery"):
            installed_badge += f" &nbsp;<span style='color:{style.ACCENT_HOVER}'>🔍 Découverte</span>"

        return f"""
<h1 style='margin-bottom:0'>{html.escape(m['name'])}</h1>
<p style='color:{muted}; margin-top:4px'>{cat['label']} · {html.escape(m['editor'])}{installed_badge}</p>

<table width='100%' cellpadding='12' style='background-color:{style.SURFACE_2}; margin:8px 0'>
<tr><td>
<span style='color:{fit_color}; font-weight:600'>{icon} {fit_title} sur ce PC</span><br>
<span style='color:{muted}'>{fit_text}. Besoin : ~{need:.1f} Go. {pc_line}</span>
</td></tr></table>

<p>{html.escape(m['desc'])}</p>

<table cellspacing='0'>
{row("Taille", f"{m['params']} de paramètres")}
{row("Téléchargement", f"~{m['size_gb']:.1f} Go")}
{row("Mémoire nécessaire", f"~{need:.1f} Go (VRAM + RAM)")}
{row("Contexte", f"{m['context']} tokens")}
{row("Qualité", f"<span style='color:{style.ORANGE}'>{stars(m['quality'])}</span>")}
{row("Français", f"<span style='color:{style.ORANGE}'>{stars(m['french'], 3)}</span>")}
{row("Nom Ollama", f"<code>{html.escape(m['id'])}</code>")}
</table>

<h3 style='color:{style.GREEN}'>Points forts</h3><ul>{strengths}</ul>
<h3 style='color:{style.ORANGE}'>Limites</h3><ul>{weaknesses}</ul>
<h3>Idéal pour</h3><p>{html.escape(m['ideal'])}</p>
"""

    # ---------------------------------------------------- téléchargement
    def download_model(self):
        model = reg.get_model(self.current_id) if self.current_id else None
        if not model:
            return
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(
                self, "Ollama absent",
                "Ollama doit être installé et lancé pour télécharger des modèles.\n"
                "Téléchargement : https://ollama.com",
            )
            return
        if reg.evaluate_fit(model, self.system_info) == "no":
            reply = QMessageBox.question(
                self, "Modèle trop gros",
                f"{model['name']} demande ~{reg.memory_needed_gb(model):.0f} Go de mémoire, "
                "c'est plus que ce PC. Il risque de ne pas fonctionner.\n\nTélécharger quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.progress_bar.setVisible(True)
        self.status_label.setText(
            f"Téléchargement de {model['name']} (~{model['size_gb']:.1f} Go)… "
            "cela peut prendre plusieurs minutes."
        )
        self.download_worker = DownloadWorker(self.ai_manager, model["id"])
        self.download_worker.finished_ok.connect(self.on_download_finished)
        self.download_worker.start()
        self.update_buttons()

    def on_download_finished(self, success: bool, error: str):
        self.progress_bar.setVisible(False)
        if success:
            self.status_label.setText("✅ Téléchargement terminé ! Le modèle est disponible dans le Chat.")
            self.refresh_installed_models()
            self.models_changed.emit()
        else:
            self.status_label.setText(f"❌ Échec du téléchargement : {error}")
        self.update_buttons()

    def delete_model(self):
        if not self.current_id:
            return
        reply = QMessageBox.question(
            self, "Confirmation", f"Supprimer « {self.current_id} » de ce PC ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = self.ai_manager.delete_model(self.current_id)
            self.status_label.setText("🗑 Modèle supprimé." if ok else "❌ Suppression impossible.")
            self.refresh_installed_models()
            self.models_changed.emit()
