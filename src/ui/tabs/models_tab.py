"""Onglet Modèles - Télécharger et gérer les IA"""

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from src.backend.ai_manager import AIManager


class DownloadWorker(QThread):
    """Télécharge un modèle sans figer la fenêtre"""
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, ai_manager, model_id):
        super().__init__()
        self.ai_manager = ai_manager
        self.model_id = model_id

    def run(self):
        try:
            self.ai_manager.download_model(self.model_id)
            self.finished_ok.emit(True, "")
        except Exception as e:
            self.finished_ok.emit(False, str(e))


class ModelsTab(QWidget):
    """Interface de gestion des modèles"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.download_worker = None
        self.init_ui()
        self.refresh_installed_models()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("📥 Télécharger un modèle :"))

        download_layout = QHBoxLayout()
        self.model_list = QComboBox()
        for m in self.ai_manager.get_catalog():
            self.model_list.addItem(f"{m['label']}  (~{m['size_gb']:.1f} Go)", m["id"])
        self.model_list.currentIndexChanged.connect(self.show_description)
        download_layout.addWidget(self.model_list, 1)

        self.download_btn = QPushButton("Télécharger")
        self.download_btn.clicked.connect(self.download_model)
        download_layout.addWidget(self.download_btn)
        layout.addLayout(download_layout)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # animation continue
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel("📦 Modèles installés :"))
        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list)

        action_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_installed_models)
        action_layout.addWidget(refresh_btn)
        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self.delete_model)
        action_layout.addWidget(delete_btn)
        layout.addLayout(action_layout)

        self.setLayout(layout)
        self.show_description()

    def show_description(self):
        index = self.model_list.currentIndex()
        catalog = self.ai_manager.get_catalog()
        if 0 <= index < len(catalog):
            m = catalog[index]
            self.desc_label.setText(
                f"ℹ️ {m['desc']}\nMémoire nécessaire : environ {m['size_gb']:.1f} Go (VRAM + RAM)."
            )

    def download_model(self):
        model_id = self.model_list.currentData()
        if not model_id:
            return
        if not self.ai_manager.is_ollama_running():
            QMessageBox.warning(
                self, "Ollama absent",
                "Ollama doit être installé et lancé pour télécharger des modèles.\n"
                "Téléchargement : https://ollama.com",
            )
            return

        self.progress_bar.setVisible(True)
        self.download_btn.setEnabled(False)
        self.status_label.setText(
            f"Téléchargement de {self.model_list.currentText()}… (peut prendre plusieurs minutes)"
        )

        self.download_worker = DownloadWorker(self.ai_manager, model_id)
        self.download_worker.finished_ok.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self, success, error):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        if success:
            self.status_label.setText("✅ Téléchargement terminé !")
            self.refresh_installed_models()
        else:
            self.status_label.setText(f"❌ Échec du téléchargement : {error}")

    def refresh_installed_models(self):
        self.installed_list.clear()
        models = self.ai_manager.get_available_models()
        if models:
            self.installed_list.addItems(models)
        else:
            self.installed_list.addItem("Aucun modèle installé")

    def delete_model(self):
        item = self.installed_list.currentItem()
        if not item or item.text() == "Aucun modèle installé":
            QMessageBox.warning(self, "Erreur", "Sélectionnez un modèle à supprimer.")
            return

        model_name = item.text()
        reply = QMessageBox.question(
            self, "Confirmation", f"Supprimer « {model_name} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ai_manager.delete_model(model_name)
            self.refresh_installed_models()
