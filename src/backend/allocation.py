"""Calcul de l'allocation RAM/VRAM"""

import psutil
from typing import Dict


class AllocationCalculator:
    """Calculer l'allocation optimale RAM/VRAM"""

    @staticmethod
    def calculate_allocation(vram_percent: int = 50, priority: str = "Équilibré") -> Dict:
        """
        Calculer l'allocation recommandée

        Args:
            vram_percent: Pourcentage de VRAM à utiliser (0-100)
            priority: "Rapidité maximale", "Équilibré", "Qualité maximale"
        """

        try:
            import torch
            has_gpu = torch.cuda.is_available()
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**2) if has_gpu else 0
        except:
            has_gpu = False
            total_vram = 0

        total_ram = psutil.virtual_memory().total / (1024**2)
        available_ram = psutil.virtual_memory().available / (1024**2)

        # Calculer les allocations
        if has_gpu:
            vram_mb = int(total_vram * (vram_percent / 100)) - 500  # Réserver 500MB
            vram_mb = max(2048, vram_mb)  # Min 2GB
        else:
            vram_mb = 0

        # RAM allocation basée sur la priorité
        if priority == "Rapidité maximale":
            ram_mb = int(available_ram * 0.7)  # 70% RAM disponible
            advice = "Configuration optimisée pour la VITESSE. Les réponses seront rapides mais moins nuancées."
        elif priority == "Qualité maximale":
            ram_mb = int(available_ram * 0.9)  # 90% RAM disponible
            advice = "Configuration optimisée pour la QUALITÉ. Les réponses seront meilleures mais plus lentes."
        else:  # Équilibré
            ram_mb = int(available_ram * 0.8)  # 80% RAM disponible
            advice = "Configuration ÉQUILIBRÉE entre vitesse et qualité."

        return {
            "vram_mb": vram_mb,
            "ram_mb": ram_mb,
            "advice": advice,
            "gpu_available": has_gpu
        }
