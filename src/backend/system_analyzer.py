"""Analyseur de système - CPU, GPU, RAM"""

import psutil
import platform
from typing import Dict, List


class SystemAnalyzer:
    """Analyser les capacités du système"""

    @staticmethod
    def get_system_info() -> Dict:
        """Obtenir les informations système"""
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            gpu_type = "NVIDIA (CUDA)" if has_cuda else "CPU Only"
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3) if has_cuda else 0
        except:
            has_cuda = False
            gpu_type = "Pas de GPU détecté"
            vram_gb = 0

        ram_gb = psutil.virtual_memory().total / (1024**3)
        ram_available_gb = psutil.virtual_memory().available / (1024**3)

        return {
            "cpu": platform.processor(),
            "ram_gb": ram_gb,
            "ram_available_gb": ram_available_gb,
            "gpu_type": gpu_type,
            "vram_gb": vram_gb,
            "gpu_vendor": "NVIDIA" if has_cuda else "Intégré/AMD",
            "cpu_count": psutil.cpu_count(),
        }

    @staticmethod
    def get_recommendations(info: Dict) -> List[str]:
        """Recommander les IA en fonction du système"""
        recommendations = []
        ram_gb = info["ram_gb"]
        vram_gb = info["vram_gb"]

        # Recommandations par RAM
        if ram_gb >= 32:
            recommendations.append("Modèles gros (70B) : Llama 2 70B, Falcon 180B")
        elif ram_gb >= 16:
            recommendations.append("Modèles moyens (7-20B) : Mistral 7B, CodeLlama 13B")
        elif ram_gb >= 8:
            recommendations.append("Modèles petits (7B) : Llama 2 7B, Mistral 7B")
        else:
            recommendations.append("Modèles très légers (3B) : Orca Mini, Phi")

        # Recommandations GPU
        if vram_gb >= 24:
            recommendations.append("GPU excellent : Peut charger les gros modèles en VRAM")
        elif vram_gb >= 8:
            recommendations.append("GPU bon : Peut charger 7-13B en VRAM, swap pour plus")
        elif vram_gb > 0:
            recommendations.append("GPU limité : Utiliser plus de RAM qu'OFFLOADING")
        else:
            recommendations.append("Pas de GPU : Utiliser CPU (plus lent, mais fonctionne)")

        # Recommandation de speed
        cpu_count = info["cpu_count"]
        if cpu_count >= 8:
            recommendations.append("Processeur puissant : Peut gérer la parallélisation")
        elif cpu_count >= 4:
            recommendations.append("Processeur standard : Multi-threading possible")
        else:
            recommendations.append("Processeur limité : Single-thread recommandé")

        return recommendations
