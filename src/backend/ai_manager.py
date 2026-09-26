"""Gestionnaire principal des IA (via Ollama)"""

from pathlib import Path
from typing import Dict, List

import requests

from src.backend.model_registry import MODELS


class AIManager:
    """Orchestration des IA locales via le serveur Ollama"""

    def __init__(self):
        self.models_dir = Path.home() / ".ia_manager" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.ollama_url = "http://localhost:11434"

    def is_ollama_running(self) -> bool:
        try:
            return requests.get(f"{self.ollama_url}/api/tags", timeout=2).status_code == 200
        except Exception:
            return False

    def get_catalog(self) -> List[Dict]:
        return MODELS

    def get_available_models(self) -> List[str]:
        """Liste des modèles installés dans Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
        except Exception:
            pass
        return []

    def chat(self, model: str, message: str) -> str:
        """Envoyer un message et récupérer la réponse complète"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": message, "stream": False},
                timeout=600,
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            return f"Erreur Ollama : {response.status_code} {response.text[:200]}"
        except requests.exceptions.ConnectionError:
            return "Ollama n'est pas lancé. Installez-le depuis ollama.com puis relancez."
        except Exception as e:
            return f"Erreur : {e}"

    def chat_messages(self, model: str, messages: List[Dict], system: str = "") -> str:
        """Discussion avec historique ; `system` = consignes du projet"""
        payload_messages = []
        if system.strip():
            payload_messages.append({"role": "system", "content": system})
        payload_messages += [{"role": m["role"], "content": m["content"]} for m in messages]
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={"model": model, "messages": payload_messages, "stream": False},
                timeout=900,
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            return f"Erreur Ollama : {response.status_code} {response.text[:200]}"
        except requests.exceptions.ConnectionError:
            return "Ollama n'est pas lancé. Installez-le depuis ollama.com puis relancez."
        except Exception as e:
            return f"Erreur : {e}"

    def download_model(self, model_id: str) -> bool:
        """Télécharger un modèle via Ollama"""
        response = requests.post(
            f"{self.ollama_url}/api/pull",
            json={"name": model_id, "stream": False},
            timeout=7200,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama a répondu {response.status_code} : {response.text[:200]}")
        return True

    def delete_model(self, model_name: str) -> bool:
        """Supprimer un modèle"""
        try:
            response = requests.delete(
                f"{self.ollama_url}/api/delete",
                json={"name": model_name},
                timeout=30,
            )
            return response.status_code == 200
        except Exception:
            return False
