"""Tâches en arrière-plan (pour ne pas figer la fenêtre)"""

from typing import Dict, List

from PyQt6.QtCore import QThread, pyqtSignal


class SafeThread(QThread):
    """QThread qui reste en mémoire jusqu'à sa fin, même si plus personne ne le référence.
    (Qt ferme l'application si un thread encore actif est détruit.)"""
    _alive: set = set()

    def __init__(self):
        super().__init__()
        SafeThread._alive.add(self)
        self.finished.connect(self._release)

    def _release(self):
        SafeThread._alive.discard(self)


class DownloadWorker(SafeThread):
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


class ChatWorker(SafeThread):
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


class FunctionWorker(SafeThread):
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


class StreamWorker(SafeThread):
    """Réponse de l'IA au fil de l'eau : token(morceau) puis done(texte complet, statistiques)"""
    token = pyqtSignal(str)
    done = pyqtSignal(str, dict)

    def __init__(self, model_ref: str, messages: List[Dict], system: str = ""):
        super().__init__()
        self.model_ref = model_ref
        self.messages = [dict(m) for m in messages]
        self.system = system
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        from src.backend.providers import chat_stream
        try:
            text, stats = chat_stream(self.model_ref, self.messages, self.system,
                                      self.token.emit, lambda: self._stop)
        except Exception as e:  # jamais d'exception dans un thread
            text, stats = f"Erreur : {e}", {}
        self.done.emit(text, stats)
