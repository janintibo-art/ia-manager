
from pathlib import Path
from src.backend import creative_tools, settings

MODEL_TO_TOOL = {
    "hunyuan3d": "hunyuan3d",
    "hunyuan3d2": "hunyuan3d",
    "triposr": "triposr",
    "musicgen-small": "audiocraft",
    "musicgen-melody": "audiocraft",
    "audiogen": "audiocraft",
    "wan21": "comfyui",
    "wan21-t2v": "comfyui",
    "ltx-video": "comfyui",
    "cogvideox-2b": "comfyui",
}

def tool_for_model(model):
    if not model:
        return ""
    mid = str(model.get("id") or "")
    if mid in MODEL_TO_TOOL:
        return MODEL_TO_TOOL[mid]
    engine = str(model.get("engine") or "").lower()
    if "hunyuan" in engine:
        return "hunyuan3d"
    if "triposr" in engine:
        return "triposr"
    if "audiocraft" in engine:
        return "audiocraft"
    if "comfyui" in engine:
        return "comfyui"
    return ""

def tool_state(tool_key):
    if not tool_key:
        return {"state": "non géré automatiquement", "installed": False, "ready": False}
    root = settings.get("creative_tools_root") or str(Path.home()/"IA Manager"/"Outils")
    record = creative_tools.read_manifest(root, tool_key)
    state = str(record.get("state") or "non installé")
    installed = state.startswith("installé")
    return {"state": state, "installed": installed, "ready": installed, "root": str(root)}

def quick_guide(model):
    key = tool_for_model(model)
    if not key:
        return {
            "tool": "",
            "title": "Installation manuelle",
            "steps": [
                "Ouvrir la page officielle du modèle.",
                "Installer le moteur recommandé indiqué dans la fiche.",
                "Télécharger les poids du modèle.",
                "Lancer l'interface locale puis revenir ici."
            ],
        }
    name = creative_tools.TOOLS[key]["name"]
    steps = [
        f"Installer {name} dans Outils locaux.",
        "Premier démarrage avec Internet pour récupérer les poids nécessaires.",
        "Attendre que l'interface locale soit prête.",
        "Revenir ici et ouvrir l'interface du moteur."
    ]
    return {"tool": key, "title": name, "steps": steps}
