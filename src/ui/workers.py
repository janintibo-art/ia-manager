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

    def stop(self):
        self.requestInterruption()

    def run(self):
        from src.backend.providers import chat_stream
        from src.backend import local_jobs
        token = None
        try:
            if local_jobs.enabled() and local_jobs.is_local(self.model_ref):
                token = local_jobs.acquire(self.model_ref, self.isInterruptionRequested)
                if token is None:
                    self.answered.emit("Erreur : tâche interrompue")
                    return
            text, stats = chat_stream(self.model_ref, self.messages, self.system,
                                      should_stop=self.isInterruptionRequested)
            if stats.get("stopped"):
                text = "Erreur : tâche interrompue"
        except Exception as e:
            text = f"Erreur : {e}"
        finally:
            if token:
                local_jobs.release(token)
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
    phase = pyqtSignal(str)
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
        from src.backend import local_jobs
        token = None
        try:
            if local_jobs.enabled() and local_jobs.is_local(self.model_ref):
                self.phase.emit("En attente d’un créneau local…")
                token = local_jobs.acquire(self.model_ref, lambda: self._stop)
                if token is None:
                    self.done.emit("", {"stopped": True})
                    return
            self.phase.emit("L’IA réfléchit…")
            text, stats = chat_stream(self.model_ref, self.messages, self.system,
                                      self.token.emit, lambda: self._stop)
        except Exception as e:
            text, stats = f"Erreur : {e}", {}
        finally:
            if token:
                local_jobs.release(token)
        self.done.emit(text, stats)


class AttachmentWorker(SafeThread):
    progress = pyqtSignal(int, int, str)
    loaded = pyqtSignal(list, list)

    def __init__(self, paths, loader):
        super().__init__()
        from threading import Event
        self.paths, self.loader = list(paths), loader
        self.cancelled = Event()

    def stop(self):
        self.cancelled.set()

    def run(self):
        from pathlib import Path
        results, errors = [], []
        for index, path in enumerate(self.paths, 1):
            if self.cancelled.is_set():
                break
            self.progress.emit(index, len(self.paths), Path(path).name)
            try:
                results.append(self.loader(path))
            except Exception as error:
                errors.append(f"{Path(path).name} : {error}")
        if not self.cancelled.is_set():
            self.loaded.emit(results, errors)
