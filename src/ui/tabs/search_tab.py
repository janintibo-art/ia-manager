"""Onglet Recherche - moteur de recherche d'IA (Hugging Face) + téléchargement dans Ollama"""

import html
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QSplitter, QTextBrowser, QVBoxLayout, QWidget,
)

from src.backend import model_registry as reg
from src.backend import model_search as ms
from src.backend import providers as pv
from src.backend import download_history
from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import SystemAnalyzer
from src.ui import style
from src.ui.workers import DownloadWorker, FileDownloadWorker, FunctionWorker


def gb(size: int) -> str:
    return f"{size / (1024 ** 3):.1f} Go"


class SearchTab(QWidget):
    """Trouver de nouvelles IA à télécharger"""

    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.results: List[Dict] = []
        self.details: Optional[Dict] = None
        self.search_worker: Optional[FunctionWorker] = None
        self.detail_worker: Optional[FunctionWorker] = None
        self.dl_worker: Optional[DownloadWorker] = None
        self.github_worker: Optional[FunctionWorker] = None
        self.github_file_worker: Optional[FileDownloadWorker] = None
        self.civitai_worker: Optional[FileDownloadWorker] = None
        self.request_id = 0
        self.detail_request = 0
        try:
            self.system_info: Optional[Dict] = SystemAnalyzer.get_system_info()
        except Exception:
            self.system_info = None
        self.init_ui()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("Moteur de recherche d'IA")
        title.setObjectName("Title")
        root.addWidget(title)
        sub = QLabel("Cherchez des modèles sur Hugging Face ou GitHub, puis installez les fichiers GGUF "
                     "compatibles directement dans Ollama.")
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("🔎 Nom ou mot-clé : mistral, qwen, coder, vision, french…")
        self.query.setClearButtonEnabled(True)
        self.query.returnPressed.connect(self.search)
        row.addWidget(self.query, 3)
        self.source = QComboBox()
        self.source.addItems(["🤗 Hugging Face", "🐙 GitHub (GGUF)", "🌏 ModelScope", "🎨 Civitai (image)"])
        self.source.currentIndexChanged.connect(self.source_changed)
        row.addWidget(self.source, 1)
        self.category = QComboBox()
        self.category.addItems(list(ms.CATEGORIES))
        row.addWidget(self.category, 1)
        self.sort = QComboBox()
        self.sort.addItems(list(ms.SORTS))
        row.addWidget(self.sort, 1)
        self.french = QCheckBox("🇫🇷 Déclarés en français")
        row.addWidget(self.french)
        self.search_btn = QPushButton("Rechercher")
        self.search_btn.setObjectName("Primary")
        self.search_btn.clicked.connect(self.search)
        row.addWidget(self.search_btn)
        root.addLayout(row)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        hint = QLabel("Idées :")
        hint.setObjectName("Muted")
        chips.addWidget(hint)
        for label, term in ms.SUGGESTIONS:
            b = QPushButton(label)
            b.setObjectName("Chip")
            b.setStyleSheet("font-size: 11pt; padding: 4px 10px;")
            b.clicked.connect(lambda _c, t=term: self.quick_search(t))
            chips.addWidget(b)
        chips.addStretch()
        root.addLayout(chips)

        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.result_list = QListWidget()
        self.result_list.currentItemChanged.connect(self.on_result_selected)
        splitter.addWidget(self.result_list)

        detail_card = QFrame()
        detail_card.setObjectName("Card")
        dl = QVBoxLayout(detail_card)
        dl.setContentsMargins(16, 14, 16, 14)
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        self.detail.setStyleSheet("border: none; background: transparent;")
        dl.addWidget(self.detail, 3)

        qt = QLabel("Versions disponibles (plus le fichier est gros, plus les réponses sont fidèles) :")
        qt.setObjectName("Muted")
        qt.setWordWrap(True)
        dl.addWidget(qt)
        self.quant_list = QListWidget()
        self.quant_list.setMaximumHeight(220)
        self.quant_list.currentItemChanged.connect(lambda _c, _p: self.update_buttons())
        dl.addWidget(self.quant_list, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        dl.addWidget(self.progress)
        self.dl_status = QLabel()
        self.dl_status.setObjectName("Status")
        self.dl_status.setWordWrap(True)
        dl.addWidget(self.dl_status)
        self.cancel_btn = QPushButton("⏹ Annuler le téléchargement")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        dl.addWidget(self.cancel_btn)

        btns = QHBoxLayout()
        self.download_btn = QPushButton("⬇ Télécharger cette version")
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self.download_selected)
        btns.addWidget(self.download_btn)
        self.hf_btn = QPushButton("🌐 Voir sur Hugging Face")
        self.hf_btn.clicked.connect(self.open_on_hf)
        btns.addWidget(self.hf_btn)
        btns.addStretch()
        dl.addLayout(btns)
        splitter.addWidget(detail_card)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([480, 720])
        root.addWidget(splitter, 1)

        # Ollama par nom
        ol = QHBoxLayout()
        lbl = QLabel("Bibliothèque Ollama :")
        lbl.setObjectName("Muted")
        ol.addWidget(lbl)
        self.ollama_name = QLineEdit()
        self.ollama_name.setPlaceholderText("nom exact vu sur ollama.com, ex. qwen3.5:9b")
        ol.addWidget(self.ollama_name, 1)
        ol_dl = QPushButton("⬇ Télécharger")
        ol_dl.clicked.connect(self.download_ollama_name)
        ol.addWidget(ol_dl)
        ol_site = QPushButton("🌐 Chercher sur ollama.com")
        ol_site.clicked.connect(self.open_ollama_site)
        ol.addWidget(ol_site)
        root.addLayout(ol)

        history_row = QHBoxLayout()
        self.history_label = QLabel("Historique : aucun modèle téléchargé depuis GitHub")
        self.history_label.setObjectName("Muted")
        history_row.addWidget(self.history_label, 1)
        history_btn = QPushButton("🧹 Nettoyer le cache")
        history_btn.clicked.connect(self.clean_download_cache)
        history_row.addWidget(history_btn)
        root.addLayout(history_row)
        self.refresh_history()

        self.detail.setHtml(self.welcome_html())
        self.update_buttons()

    def welcome_html(self) -> str:
        return (f"<h2>Trouvez de nouvelles IA</h2>"
                f"<p>Tapez un nom ou cliquez sur une idée, puis choisissez un modèle dans la liste.</p>"
                f"<p style='color:{style.TEXT_MUTED}'>Astuce : les dépôts de <b>unsloth</b>, "
                f"<b>bartowski</b>, <b>lmstudio-community</b> et <b>MaziyarPanahi</b> proposent des "
                f"versions GGUF fiables des modèles connus.</p>")

    # ------------------------------------------------------------ recherche
    def set_system_info(self, info: Dict):
        self.system_info = info
        if self.details:
            self.show_details(self.details)

    def quick_search(self, term: str):
        self.query.setText(term)
        self.search()

    def source_changed(self):
        github = self.source.currentIndex() == 1
        modelscope = self.source.currentIndex() == 2
        civitai = self.source.currentIndex() == 3
        self.category.setVisible(not github and not modelscope and not civitai)
        self.sort.setVisible(not github and not modelscope and not civitai)
        self.french.setVisible(not github and not modelscope and not civitai)
        self.hf_btn.setText("🌐 Voir sur GitHub" if github else ("🌐 Voir sur ModelScope" if modelscope else ("🌐 Voir sur Civitai" if civitai else "🌐 Voir sur Hugging Face")))
        self.result_list.clear(); self.quant_list.clear(); self.details = None
        self.detail.setHtml(self.welcome_html())
        self.update_buttons()

    def search(self):
        self.request_id += 1
        rid = self.request_id
        self.status.setText("⏳ Recherche en cours…")
        self.search_btn.setEnabled(False)
        if self.source.currentIndex() == 1:
            self.search_worker = FunctionWorker(ms.search_github, self.query.text())
        elif self.source.currentIndex() == 2:
            self.search_worker = FunctionWorker(ms.search_modelscope, self.query.text())
        elif self.source.currentIndex() == 3:
            self.search_worker = FunctionWorker(ms.search_civitai, self.query.text())
        else:
            self.search_worker = FunctionWorker(
                ms.search_hf, self.query.text(), ms.CATEGORIES[self.category.currentText()],
                ms.SORTS[self.sort.currentText()], self.french.isChecked())
        self.search_worker.done.connect(lambda ok, res, r=rid: self.on_results(r, ok, res))
        self.search_worker.start()

    def on_results(self, rid: int, ok: bool, result):
        if rid != self.request_id:
            return  # une recherche plus récente a été lancée
        self.search_btn.setEnabled(True)
        if not ok:
            self.status.setText(f"❌ Recherche impossible (connexion Internet ?) : {result}")
            return
        self.results = list(result)
        self.result_list.clear()
        github = self.source.currentIndex() == 1
        modelscope = self.source.currentIndex() == 2
        civitai = self.source.currentIndex() == 3
        for m in self.results:
            if github:
                item = QListWidgetItem(f"🐙 {m['id']}\n      ⭐ {ms.human_number(m['downloads'])} · {m.get('description','')[:100]}")
            elif modelscope:
                item = QListWidgetItem(f"🌏 {m['id']}\n      ⬇ {ms.human_number(m['downloads'])} · {m.get('description','')[:100]}")
            elif civitai:
                item = QListWidgetItem(f"🎨 {m['name']} · {m.get('type','')}\n      ⬇ {ms.human_number(m['downloads'])} · {m['author']}")
            else:
                lock = " 🔒" if m["gated"] else ""
                kind = "🖼️ " if m["pipeline"] == "image-text-to-text" else ""
                item = QListWidgetItem(
                    f"{kind}{m['name']}{lock}\n      {m['author']} · ⬇ {ms.human_number(m['downloads'])} · "
                    f"♥ {ms.human_number(m['likes'])} · {ms.fmt_date(m['updated'])}")
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            item.setToolTip(m["id"])
            self.result_list.addItem(item)
        q = self.query.text().strip()
        self.status.setText(f"{len(self.results)} résultat(s)" + (f" pour « {q} »" if q else "") +
                            (". Essayez un autre mot-clé." if not self.results else "."))

    # ------------------------------------------------------------ fiche
    def on_result_selected(self, current, _prev):
        if current is None:
            return
        repo = current.data(Qt.ItemDataRole.UserRole)
        self.detail_request += 1
        rid = self.detail_request
        self.details = None
        self.quant_list.clear()
        self.detail.setHtml(f"<h2>{html.escape(repo)}</h2><p>⏳ Chargement de la fiche…</p>")
        self.update_buttons()
        detail_fn = ms.github_details if self.source.currentIndex() == 1 else (ms.modelscope_details if self.source.currentIndex() == 2 else (ms.civitai_details if self.source.currentIndex() == 3 else ms.model_details))
        self.detail_worker = FunctionWorker(detail_fn, repo)
        self.detail_worker.done.connect(lambda ok, res, r=rid, rp=repo: self.on_details(r, rp, ok, res))
        self.detail_worker.start()

    def on_details(self, rid: int, repo: str, ok: bool, result):
        if rid != self.detail_request:
            return
        if not ok:
            self.detail.setHtml(f"<h2>{html.escape(repo)}</h2><p>❌ Fiche indisponible : "
                                f"{html.escape(str(result))}</p>")
            return
        self.show_details(result)

    def show_details(self, d: Dict):
        self.details = d
        muted = style.TEXT_MUTED
        rows = []

        def row(label, value):
            if value:
                rows.append(f"<tr><td style='color:{muted}; padding:4px 16px 4px 0'>{label}</td>"
                            f"<td style='padding:4px 0'><b>{html.escape(str(value))}</b></td></tr>")

        if d.get("pipeline") == "github":
            row("Source", "GitHub · releases GGUF")
            row("Dépôt", d["id"])
        elif d.get("pipeline") == "modelscope":
            row("Source", "ModelScope · catalogue public")
            row("Dépôt", d["id"])
        elif d.get("pipeline") == "civitai":
            row("Source", "Civitai · modèles image")
            row("Type", d.get("type", ""))
        else:
            row("Auteur", d["author"])
        row("Taille", ms.readable_params(d["params"]) + (" de paramètres" if d["params"] else ""))
        row("Architecture", d["architecture"])
        row("Contexte", f"{d['context']:,} tokens".replace(",", " ") if d["context"] else "")
        row("Modèle d'origine", d["base_model"])
        row("Licence", d["license"])
        row("Langues", ", ".join(d["languages"][:12]))
        row("Type", "Comprend les images" if d["pipeline"] == "image-text-to-text" else
            ("Texte" if d["pipeline"] else ""))
        row("Popularité", f"⬇ {ms.human_number(d['downloads'])} · ♥ {ms.human_number(d['likes'])}")
        row("Mis à jour", ms.fmt_date(d["updated"]))

        readme = d.get("readme", "")
        readme = re.sub(r"<[^>]+>", "", readme)
        readme = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", readme)
        excerpt = "<br>".join(html.escape(line) for line in readme.splitlines()[:25] if line.strip())

        gated = (f"<p style='color:{style.ORANGE}'>🔒 Accès restreint : il faut accepter les conditions sur "
                 f"Hugging Face, le téléchargement direct peut échouer.</p>") if d["gated"] else ""
        notice = (f"<p style='color:{muted}'>ℹ️ Ce dépôt ModelScope peut contenir des formats Python, Safetensors ou Diffusers. "
                  "Il est consultable ici, mais l'installation automatique dans Ollama nécessite un fichier GGUF.</p>"
                  if d.get("pipeline") == "modelscope" else (f"<p style='color:{muted}'>🎨 Civitai fournit des modèles d'image, LoRA et embeddings. "
                  "Ouvrez la fiche pour télécharger le fichier avec l'outil image adapté ; ces fichiers ne sont pas installables dans Ollama.</p>"
                  if d.get("pipeline") == "civitai" else ""))
        self.detail.setHtml(
            f"<h2>{html.escape(d['id'].split('/')[-1])}</h2>{gated}"
            f"<table cellspacing='0'>{''.join(rows)}</table>"
            + notice
            + (f"<h3>Présentation (extrait)</h3><p style='color:{muted}'>{excerpt}</p>" if excerpt else ""))

        best = ms.best_quant(d["quants"], self.system_info) if d.get("pipeline") not in ("github", "civitai") else next(
            (q["quant"] for q in d["quants"] if not q["split"]), None)
        installed = set(self.ai_manager.get_available_models())
        self.quant_list.clear()
        for q in reversed(d["quants"]):
            fit = ms.fit_for_size(q["size"], self.system_info)
            icon, fit_title, _ = reg.FIT_LABELS[fit]
            name = ms.ollama_name(d["id"], q["quant"]) if d.get("pipeline") not in ("github", "civitai") else q.get("asset", "")
            extras = []
            if q["quant"] == best:
                extras.append("⭐ conseillé")
            if q["split"]:
                extras.append("en plusieurs fichiers : non pris en charge")
            if name in installed or f"{name}".lower() in {i.lower() for i in installed}:
                extras.append("✔ installé")
            item = QListWidgetItem(f"{icon} {q['quant']}  ·  {gb(q['size'])}  ·  {fit_title}"
                                   + (f"  ·  {' · '.join(extras)}" if extras else ""))
            item.setData(Qt.ItemDataRole.UserRole, q["quant"])
            self.quant_list.addItem(item)
            if q["quant"] == best:
                self.quant_list.setCurrentItem(item)
        if not d["quants"]:
            self.quant_list.addItem("Aucun fichier GGUF utilisable dans ce dépôt.")
        self.update_buttons()

    def selected_quant(self) -> Optional[Dict]:
        item = self.quant_list.currentItem()
        if not item or not self.details:
            return None
        q = item.data(Qt.ItemDataRole.UserRole)
        return next((x for x in self.details["quants"] if x["quant"] == q), None)

    def update_buttons(self):
        busy = any(worker is not None and worker.isRunning()
                   for worker in (self.dl_worker, self.github_worker, self.github_file_worker, self.civitai_worker))
        q = self.selected_quant()
        self.download_btn.setEnabled(bool(q) and not q["split"] and not busy)
        self.download_btn.setText("⬇ Télécharger pour outil image" if self.details and self.details.get("pipeline") == "civitai" else "⬇ Télécharger cette version")
        self.hf_btn.setEnabled(self.details is not None or self.result_list.currentItem() is not None)

    def open_on_hf(self):
        item = self.result_list.currentItem()
        if item:
            if self.source.currentIndex() == 1:
                url = f"{ms.GITHUB_SITE}/{item.data(Qt.ItemDataRole.UserRole)}"
            elif self.source.currentIndex() == 2:
                url = f"{ms.MODELSCOPE_SITE}/{item.data(Qt.ItemDataRole.UserRole)}"
            elif self.source.currentIndex() == 3:
                url = f"{ms.CIVITAI_SITE}/{item.data(Qt.ItemDataRole.UserRole)}"
            else:
                url = f"{ms.HF_SITE}/{item.data(Qt.ItemDataRole.UserRole)}"
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------------------ téléchargement
    def start_download(self, name: str, size_text: str = ""):
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(self, "Ollama absent", "Ollama doit être installé et lancé pour "
                                                       "télécharger des modèles (ollama.com).")
            return
        self.progress.setVisible(True)
        self.dl_status.setText(f"⏳ Téléchargement de {name} {size_text}… cela peut prendre du temps.")
        self.dl_worker = DownloadWorker(self.ai_manager, name)
        self.dl_worker.finished_ok.connect(lambda ok, err, n=name: self.on_downloaded(ok, err, n))
        self.dl_worker.start()
        self.update_buttons()

    def download_selected(self):
        q = self.selected_quant()
        if not q or not self.details:
            return
        if self.details.get("pipeline") == "civitai":
            self.download_civitai(q)
            return
        if ms.fit_for_size(q["size"], self.system_info) == "no":
            reply = QMessageBox.question(
                self, "Version trop grosse",
                f"Cette version fait {gb(q['size'])}, c'est probablement trop pour ce PC.\n\n"
                "Télécharger quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        if self.details.get("pipeline") == "github":
            self.download_github(q)
            return
        self.start_download(ms.ollama_name(self.details["id"], q["quant"]), f"({gb(q['size'])})")

    def download_github(self, asset: Dict):
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(self, "Ollama absent", "Ollama doit être installé et lancé pour installer ce GGUF.")
            return
        name = re.sub(r"[^a-z0-9._/-]+", "-", asset.get("asset", "modele").lower()).replace(".gguf", "")[:60].strip("-.")
        if not pv.valid_model_name(name):
            name = "github-modele"
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.cancel_btn.setVisible(True)
        self.dl_status.setText(f"⏳ Téléchargement puis installation de {asset.get('asset','')}…")
        self.github_file_worker = FileDownloadWorker(ms.download_github_gguf, self.details["id"], asset)
        self.github_file_worker.progress.connect(self.on_file_progress)
        self.github_file_worker.finished_ok.connect(lambda ok, result, n=name, a=asset:
                                                    self.on_github_file(ok, result, n, a))
        self.github_file_worker.start()

    def download_civitai(self, asset: Dict):
        self.progress.setVisible(True); self.cancel_btn.setVisible(True); self.progress.setValue(0)
        self.dl_status.setText(f"⏳ Téléchargement image de {asset.get('asset', '')}…")
        self.civitai_worker = FileDownloadWorker(ms.download_civitai_file, asset)
        self.civitai_worker.progress.connect(self.on_file_progress)
        self.civitai_worker.finished_ok.connect(self.on_civitai_downloaded)
        self.civitai_worker.start()

    def on_civitai_downloaded(self, ok: bool, result: str):
        self.civitai_worker = None
        self.progress.setVisible(False); self.cancel_btn.setVisible(False)
        if ok:
            size = Path(result).stat().st_size if Path(result).exists() else 0
            download_history.record(Path(result).name, "Civitai", result, size)
            self.dl_status.setText(f"✅ Fichier image téléchargé : {result}")
            self.refresh_history()
        else:
            self.dl_status.setText(f"❌ {result}")
        self.update_buttons()

    def on_file_progress(self, done: int, total: int):
        if total:
            self.progress.setValue(min(100, int(done * 100 / total)))
            self.dl_status.setText(f"⏳ Téléchargement : {gb(done)} / {gb(total)}")

    def on_github_file(self, ok: bool, result: str, name: str, _asset: Dict):
        self.github_file_worker = None
        if not ok:
            self.progress.setVisible(False); self.cancel_btn.setVisible(False)
            self.dl_status.setText(f"❌ {result}")
            self.update_buttons()
            return
        self.dl_status.setText("⏳ Import du fichier dans Ollama…")
        download_history.record(name, "GitHub", result, Path(result).stat().st_size if Path(result).exists() else 0)
        self.github_worker = FunctionWorker(pv.create_from_gguf, name, result)
        self.github_worker.done.connect(lambda done, message, n=name: self.on_downloaded(
            done, str(message) if not done else "", n))
        self.github_worker.start()

    def refresh_history(self):
        entries = download_history.list_entries()
        stats = download_history.cache_stats()
        if not entries and not stats["files"]:
            self.history_label.setText("Historique : aucun fichier téléchargé")
            return
        self.history_label.setText(f"Cache : {stats['files']} fichier(s) · {gb(stats['bytes'])}" +
                                   (f" · {stats['partial']} interrompu(s)" if stats['partial'] else "") +
                                   f" · {len(entries)} entrée(s) historique")

    def clean_download_cache(self):
        removed = download_history.cleanup_cache()
        self.refresh_history()
        self.dl_status.setText(f"✅ Cache nettoyé : {removed} fichier(s) supprimé(s).")

    def cancel_download(self):
        if self.github_file_worker:
            self.github_file_worker.stop()
            self.dl_status.setText("⏹ Annulation demandée… le fichier partiel sera conservé pour reprendre.")
        elif self.civitai_worker:
            self.civitai_worker.stop()
            self.dl_status.setText("⏹ Annulation demandée… le fichier partiel sera conservé pour reprendre.")

    def download_ollama_name(self):
        name = self.ollama_name.text().strip()
        if not name:
            self.dl_status.setText("Écrivez le nom exact du modèle (ex. qwen3.5:9b).")
            return
        self.start_download(name)

    def open_ollama_site(self):
        q = self.ollama_name.text().strip() or self.query.text().strip()
        QDesktopServices.openUrl(QUrl(f"https://ollama.com/search?q={quote_plus(q)}" if q
                                      else "https://ollama.com/search"))

    def on_downloaded(self, ok: bool, error: str, name: str):
        self.progress.setVisible(False)
        self.cancel_btn.setVisible(False)
        if ok:
            self.dl_status.setText(f"✅ {name} est installé : il est disponible dans le Chat.")
            self.models_changed.emit()
            self.refresh_history()
            if self.details:
                self.show_details(self.details)
        else:
            self.dl_status.setText(f"❌ Échec : {error}")
        self.update_buttons()
