"""Tâches en arrière-plan (pour ne pas figer la fenêtre)"""

from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    """Télécharge un modèle via Ollama"""
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


class ChatWorker(QThread):
    """Interroge l'IA"""
    answered = pyqtSignal(str)

    def __init__(self, ai_manager, model, message):
        super().__init__()
        self.ai_manager = ai_manager
        self.model = model
        self.message = message

    def run(self):
        self.answered.emit(self.ai_manager.chat(self.model, self.message))
