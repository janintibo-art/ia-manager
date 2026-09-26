"""Analyseur de système - CPU, GPU, RAM"""

import platform
import subprocess
from typing import Dict, List

import psutil


def _run(cmd: List[str]) -> str:
    """Lancer une commande sans ouvrir de fenêtre console, renvoie '' en cas d'échec"""
    try:
        flags = 0x08000000 if platform.system() == "Windows" else 0  # CREATE_NO_WINDOW
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, creationflags=flags
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def detect_gpu() -> Dict:
    """Détecter la carte graphique et sa VRAM (NVIDIA via nvidia-smi, sinon Windows)"""
    out = _run([
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ])
    if out:
        first = out.splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        if len(parts) >= 2:
            try:
                return {
                    "name": parts[0],
                    "vendor": "NVIDIA",
                    "vram_gb": float(parts[1]) / 1024,
                    "vram_exact": True,
                }
            except ValueError:
                pass

    if platform.system() == "Windows":
        out = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_VideoController | "
            "ForEach-Object { $_.Name + '|' + $_.AdapterRAM }",
        ])
        best = None
        for line in out.splitlines():
            if "|" not in line:
                continue
            name, ram = line.split("|", 1)
            try:
                vram = int(ram) / (1024 ** 3)
            except ValueError:
                vram = 0.0
            if best is None or vram > best["vram_gb"]:
                lower = name.lower()
                if "amd" in lower or "radeon" in lower:
                    vendor = "AMD"
                elif "intel" in lower:
                    vendor = "Intel"
                elif "nvidia" in lower:
                    vendor = "NVIDIA"
                else:
                    vendor = "Autre"
                best = {
                    "name": name.strip(),
                    "vendor": vendor,
                    "vram_gb": vram,
                    "vram_exact": False,
                }
        if best:
            return best

    return {"name": "Aucun GPU détecté", "vendor": "Aucun", "vram_gb": 0.0, "vram_exact": True}


class SystemAnalyzer:
    """Analyser les capacités du système"""

    @staticmethod
    def get_system_info() -> Dict:
        """Obtenir les informations système"""
        gpu = detect_gpu()
        mem = psutil.virtual_memory()

        return {
            "cpu": platform.processor() or platform.machine(),
            "cpu_count": psutil.cpu_count() or 1,
            "ram_gb": mem.total / (1024 ** 3),
            "ram_available_gb": mem.available / (1024 ** 3),
            "gpu_type": gpu["name"],
            "gpu_vendor": gpu["vendor"],
            "vram_gb": gpu["vram_gb"],
            "vram_exact": gpu["vram_exact"],
        }

    @staticmethod
    def get_recommendations(info: Dict) -> List[str]:
        """Recommander les IA en fonction du système"""
        recommendations = []
        ram_gb = info["ram_gb"]
        vram_gb = info["vram_gb"]
        total = ram_gb + vram_gb

        if vram_gb >= 20:
            recommendations.append("GPU très puissant : modèles 27-32B entièrement en VRAM (qwen2.5:32b, gemma2:27b)")
        elif vram_gb >= 10:
            recommendations.append("GPU puissant : modèles 12-14B en VRAM (qwen2.5:14b, phi4, mistral-nemo)")
        elif vram_gb >= 6:
            recommendations.append("GPU moyen : modèles 7-9B en VRAM (llama3.1:8b, qwen2.5:7b, gemma2:9b)")
        elif vram_gb > 0:
            recommendations.append("GPU limité : modèles 3-4B en VRAM (llama3.2:3b, phi3:mini), le reste en RAM")
        else:
            recommendations.append("Pas de GPU dédié : tout tourne sur le processeur, préférer les modèles 1-4B")

        if total >= 48:
            recommendations.append("Mémoire totale large : un 70B est possible en répartissant VRAM + RAM (lent)")
        elif total >= 24:
            recommendations.append("Mémoire totale suffisante pour un 14B en répartition VRAM + RAM")
        elif total >= 12:
            recommendations.append("Mémoire totale adaptée aux modèles 7-8B")
        else:
            recommendations.append("Mémoire totale faible : rester sur les modèles 1-3B")

        if info["cpu_count"] >= 8:
            recommendations.append("Processeur multi-cœurs : bonnes performances pour la partie en RAM")
        else:
            recommendations.append("Processeur modeste : la partie en RAM sera lente, charger au maximum en VRAM")

        if not info.get("vram_exact", True):
            recommendations.append("Note : VRAM lue par Windows, la valeur peut être plafonnée à 4 Go")

        return recommendations
