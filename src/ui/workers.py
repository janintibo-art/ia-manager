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
    """Interroge l'IA (locale ou distante) avec l'historique et les consignes du projet"""
    answered = pyqtSignal(str)

    def __init__(self, model_ref: str, messages: List[Dict], system: str = ""):
        super().__init__()
        self.model_ref = model_ref
        self.messages = [dict(m) for m in messages]
        self.system = system

    def run(self):
        from src.backend.providers import chat
        try:
            text = chat(self.model_ref, self.messages, self.system)
        except Exception as e:  # jamais d'exception dans un thread
            text = f"Erreur : {e}"
        self.answered.emit(text)


class FunctionWorker(QThread):
    """Lance une fonction quelconque en arrière-plan : done(ok, résultat ou message d'erreur)"""
    done = pyqtSignal(bool, object)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.done.emit(True, self.func(*self.args))
        except Exception as e:
            self.done.emit(False, str(e))
