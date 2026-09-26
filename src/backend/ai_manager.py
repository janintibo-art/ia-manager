"""Gestionnaire principal des IA (via Ollama)"""

from pathlib import Path
from typing import Dict, List

import requests


# Catalogue des modèles proposés au téléchargement.
# size_gb = taille approximative du fichier téléchargé (≈ mémoire nécessaire).
MODEL_CATALOG: List[Dict] = [
    {"id": "llama3.2:1b", "label": "Llama 3.2 1B", "size_gb": 1.3,
     "desc": "Meta. Très léger, pour PC modestes ou sans GPU. Réponses simples."},
    {"id": "llama3.2:3b", "label": "Llama 3.2 3B", "size_gb": 2.0,
     "desc": "Meta. Léger et rapide, bon en français courant."},
    {"id": "phi3:mini", "label": "Phi-3 Mini 3.8B", "size_gb": 2.2,
     "desc": "Microsoft. Petit mais bon en raisonnement et en maths."},
    {"id": "llama3.1:8b", "label": "Llama 3.1 8B", "size_gb": 4.9,
     "desc": "Meta. Généraliste de référence, polyvalent."},
    {"id": "mistral:7b", "label": "Mistral 7B", "size_gb": 4.1,
     "desc": "Mistral AI (français). Rapide, bon en français."},
    {"id": "qwen2.5:7b", "label": "Qwen 2.5 7B", "size_gb": 4.7,
     "desc": "Alibaba. Excellent rapport qualité/taille, multilingue."},
    {"id": "gemma2:9b", "label": "Gemma 2 9B", "size_gb": 5.4,
     "desc": "Google. Très bonne qualité d'écriture."},
    {"id": "deepseek-r1:7b", "label": "DeepSeek R1 7B", "size_gb": 4.7,
     "desc": "DeepSeek. Modèle qui « réfléchit » avant de répondre, fort en logique."},
    {"id": "qwen2.5-coder:7b", "label": "Qwen 2.5 Coder 7B", "size_gb": 4.7,
     "desc": "Spécialisé programmation : écrire, expliquer, corriger du code."},
    {"id": "llava:7b", "label": "LLaVA 7B", "size_gb": 4.7,
     "desc": "Comprend les images (vision) en plus du texte."},
    {"id": "mistral-nemo:12b", "label": "Mistral Nemo 12B", "size_gb": 7.1,
     "desc": "Mistral AI + NVIDIA. Très bon en français, long contexte."},
    {"id": "qwen2.5:14b", "label": "Qwen 2.5 14B", "size_gb": 9.0,
     "desc": "Alibaba. Haute qualité, demande un bon GPU."},
    {"id": "phi4:14b", "label": "Phi-4 14B", "size_gb": 9.1,
     "desc": "Microsoft. Excellent en raisonnement pour sa taille."},
    {"id": "deepseek-r1:14b", "label": "DeepSeek R1 14B", "size_gb": 9.0,
     "desc": "Raisonnement poussé, plus précis que la version 7B."},
    {"id": "gemma2:27b", "label": "Gemma 2 27B", "size_gb": 16.0,
     "desc": "Google. Qualité proche des grands modèles en ligne."},
    {"id": "qwen2.5:32b", "label": "Qwen 2.5 32B", "size_gb": 20.0,
     "desc": "Alibaba. Très haute qualité, GPU 24 Go ou beaucoup de RAM."},
    {"id": "llama3.1:70b", "label": "Llama 3.1 70B", "size_gb": 40.0,
     "desc": "Meta. Le plus puissant du catalogue, 48 Go de mémoire minimum."},
]


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
        return MODEL_CATALOG

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
