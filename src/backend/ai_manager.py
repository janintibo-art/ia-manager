"""Gestionnaire principal des IA"""

import requests
from pathlib import Path
from typing import List, Optional


class AIManager:
    """Orchestration des IA (Ollama, HuggingFace, etc)"""

    def __init__(self):
        self.models_dir = Path.home() / ".ia_manager" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.ollama_url = "http://localhost:11434"
        self.hf_cache = Path.home() / ".cache" / "huggingface" / "hub"

    def get_available_models(self) -> List[str]:
        """Obtenir la liste des modèles disponibles"""
        models = []

        # Vérifier Ollama
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                for model in response.json().get("models", []):
                    models.append(model["name"])
        except:
            pass

        return models

    def chat(self, model: str, message: str) -> str:
        """Discuter avec un modèle"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": message, "stream": False},
                timeout=300
            )

            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Erreur : {response.status_code}"
        except Exception as e:
            return f"Erreur de connexion : {str(e)}"

    def download_model(self, model_id: str) -> bool:
        """Télécharger un modèle"""
        try:
            if model_id.startswith("ollama:"):
                model_name = model_id.replace("ollama:", "")
                response = requests.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_name, "stream": False},
                    timeout=3600
                )
                return response.status_code == 200

            elif model_id.startswith("huggingface:"):
                from huggingface_hub import hf_hub_download
                model_name = model_id.replace("huggingface:", "")
                hf_hub_download(model_name)
                return True
        except Exception as e:
            print(f"Erreur téléchargement : {str(e)}")
            return False

    def delete_model(self, model_name: str) -> bool:
        """Supprimer un modèle"""
        try:
            response = requests.delete(
                f"{self.ollama_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
