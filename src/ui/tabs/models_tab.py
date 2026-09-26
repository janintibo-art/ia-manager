"""Onglet Modèles - Télécharger et gérer les IA"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.backend.ai_manager import AIManager


class DownloadWorker(QThread):
    """Thread pour télécharger un modèle sans bloquer l'UI"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, ai_manager, model_name):
        super().__init__()
        self.ai_manager = ai_manager
        self.model_name = model_name

    def run(self):
        try:
            self.ai_manager.download_model(self.model_name)
            self.finished.emit(True)
        except Exception as e:
            self.progress.emit(f"Erreur : {str(e)}")
            self.finished.emit(False)


class ModelsTab(QWidget):
    """Interface de gestion des modèles"""

    def __init__(self):
        super().__init__()
        self.ai_manager = AIManager()
        self.download_worker = None
        self.init_ui()

    def init_ui(self):
        """Initialiser l'interface de gestion des modèles"""
        layout = QVBoxLayout()

        # Section téléchargement
        layout.addWidget(QLabel("📥 Télécharger un modèle :"))

        download_layout = QHBoxLayout()

        self.model_list = QComboBox()
        self.populate_model_list()
        download_layout.addWidget(self.model_list)

        download_btn = QPushButton("Télécharger")
        download_btn.clicked.connect(self.download_model)
        download_layout.addWidget(download_btn)

        layout.addLayout(download_layout)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Section modèles installés
        layout.addWidget(QLabel("\n📦 Modèles installés :"))

        self.installed_list = QListWidget()
        self.refresh_installed_models()
        layout.addWidget(self.installed_list)

        # Boutons d'action
        action_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_installed_models)
        action_layout.addWidget(refresh_btn)

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self.delete_model)
        action_layout.addWidget(delete_btn)

        layout.addLayout(action_layout)
        layout.addStretch()

        self.setLayout(layout)

    def populate_model_list(self):
        """Remplir la liste des modèles disponibles"""
        models = {
            "Ollama - Llama 2 (7B)": "ollama:llama2",
            "Ollama - Mistral (7B)": "ollama:mistral",
            "Ollama - Neural Chat": "ollama:neural-chat",
            "Ollama - CodeLlama": "ollama:codellama",
            "HuggingFace - Orca Mini": "huggingface:microsoft/orca-mini-3b",
            "HuggingFace - Falcon 7B": "huggingface:tiiuae/falcon-7b",
        }

        for label, model_id in models.items():
            self.model_list.addItem(label, model_id)

    def download_model(self):
        """Télécharger un modèle"""
        model_id = self.model_list.currentData()

        if not model_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un modèle.")
            return

        self.progress_bar.setVisible(True)
        self.status_label.setText(f"Téléchargement de {self.model_list.currentText()}...")

        self.download_worker = DownloadWorker(self.ai_manager, model_id)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.progress.connect(self.update_status)
        self.download_worker.start()

    def on_download_finished(self, success):
        """Appelé quand le téléchargement est terminé"""
        self.progress_bar.setVisible(False)

        if success:
            self.status_label.setText("✅ Téléchargement terminé !")
            self.refresh_installed_models()
        else:
            self.status_label.setText("❌ Échec du téléchargement")

    def update_status(self, message):
        """Mettre à jour le statut"""
        self.status_label.setText(message)

    def refresh_installed_models(self):
        """Actualiser la liste des modèles installés"""
        self.installed_list.clear()
        models = self.ai_manager.get_available_models()

        if models:
            for model in models:
                item = QListWidgetItem(f"✓ {model}")
                self.installed_list.addItem(item)
        else:
            self.installed_list.addItem("Aucun modèle installé")

    def delete_model(self):
        """Supprimer le modèle sélectionné"""
        item = self.installed_list.currentItem()

        if not item:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un modèle à supprimer.")
            return

        model_name = item.text().replace("✓ ", "")

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Êtes-vous sûr de vouloir supprimer '{model_name}' ?"
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.ai_manager.delete_model(model_name)
            self.refresh_installed_models()
