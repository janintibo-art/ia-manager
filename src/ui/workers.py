"""Tâches en arrière-plan (pour ne pas figer la fenêtre)"""

from typing import Dict, List

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
    """Interroge l'IA avec l'historique et les consignes du projet"""
    answered = pyqtSignal(str)

    def __init__(self, ai_manager, model: str, messages: List[Dict], system: str = ""):
        super().__init__()
        self.ai_manager = ai_manager
        self.model = model
        self.messages = [dict(m) for m in messages]
        self.system = system

    def run(self):
        self.answered.emit(self.ai_manager.chat_messages(self.model, self.messages, self.system))
