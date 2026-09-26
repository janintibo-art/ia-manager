"""Calcul de l'allocation RAM/VRAM"""

from typing import Dict

import psutil

from src.backend.system_analyzer import detect_gpu


class AllocationCalculator:
    """Calculer l'allocation optimale RAM/VRAM"""

    def __init__(self):
        self._gpu = None

    def _gpu_info(self) -> Dict:
        if self._gpu is None:
            self._gpu = detect_gpu()
        return self._gpu

    def calculate_allocation(self, vram_percent: int = 50, priority: str = "Équilibré") -> Dict:
        """
        Calculer l'allocation recommandée

        Args:
            vram_percent: Pourcentage de VRAM à utiliser (0-100)
            priority: "Rapidité maximale", "Équilibré", "Qualité maximale"
        """
        gpu = self._gpu_info()
        total_vram_mb = gpu["vram_gb"] * 1024
        has_gpu = total_vram_mb > 0

        available_ram_mb = psutil.virtual_memory().available / (1024 ** 2)

        if has_gpu:
            vram_mb = int(total_vram_mb * (vram_percent / 100)) - 500  # 500 Mo réservés à Windows
            vram_mb = max(0, vram_mb)
        else:
            vram_mb = 0

        if priority == "Rapidité maximale":
            ram_mb = int(available_ram_mb * 0.5)
            advice = ("VITESSE : choisir un modèle qui tient entièrement dans la VRAM ci-dessus. "
                      "Réponses rapides, modèle plus petit.")
        elif priority == "Qualité maximale":
            ram_mb = int(available_ram_mb * 0.85)
            advice = ("QUALITÉ : un modèle plus gros peut déborder de la VRAM vers la RAM. "
                      "Meilleures réponses, mais nettement plus lent.")
        else:
            ram_mb = int(available_ram_mb * 0.7)
            advice = "ÉQUILIBRÉ : modèle qui remplit la VRAM avec un léger débordement en RAM."

        if not has_gpu:
            advice += " Aucun GPU détecté : tout le modèle sera en RAM."

        max_model_gb = (vram_mb + ram_mb) / 1024

        return {
            "vram_mb": vram_mb,
            "ram_mb": ram_mb,
            "max_model_gb": max_model_gb,
            "advice": advice,
            "gpu_available": has_gpu,
        }
