"""Assistant local IA Manager : contexte réel + diagnostic direct."""
import shutil
import socket
from pathlib import Path

from src.backend import creative_tools, hardware_profiles, storage, universal_history
from src.backend.ai_manager import AIManager
from src.backend.system_analyzer import SystemAnalyzer


def _port(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            return True
    except Exception:
        return False


def _disk(path):
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        total, used, free = shutil.disk_usage(p)
        return {"free_gb": free / 2**30, "total_gb": total / 2**30}
    except Exception:
        return {"free_gb": 0.0, "total_gb": 0.0}


def collect_state(window=None):
    ai = AIManager()
    ollama = ai.is_ollama_running()
    try:
        models = ai.get_available_models(force=True) if ollama else []
    except Exception:
        models = []

    try:
        system = SystemAnalyzer.get_system_info()
    except Exception:
        system = {}

    profile = hardware_profiles.active_profile()
    recent = universal_history.list_events()[:30]

    comfy = {
        "configured": False,
        "installed": False,
        "python": False,
        "running": _port(8188),
        "path": "",
    }
    creative = getattr(window, "creative_tools_tab", None) if window is not None else None
    if creative is not None:
        try:
            p = creative_tools.paths(creative.directory.text(), "comfyui")
            comfy.update(
                configured=True,
                installed=(p["source"] / "main.py").is_file(),
                python=p["python"].is_file(),
                path=str(p["source"]),
            )
        except Exception:
            pass

    disk_models = _disk(storage.app_models())
    disk_ollama = _disk(storage.ollama_models())

    return {
        "system": system,
        "profile": profile or {},
        "ollama": {
            "running": ollama,
            "port": 11434,
            "models": models,
            "models_dir": str(storage.ollama_models()),
        },
        "comfyui": comfy,
        "storage": {
            "app_models": str(storage.app_models()),
            "ollama_models": str(storage.ollama_models()),
            "conversions": str(storage.conversions()),
            "backups": str(storage.backups()),
            "app_models_free_gb": disk_models["free_gb"],
            "ollama_free_gb": disk_ollama["free_gb"],
        },
        "recent": recent,
        "git": shutil.which("git") or "",
        "python": shutil.which("python") or "",
    }


def context_text(state):
    sys = state.get("system") or {}
    profile = state.get("profile") or {}
    ollama = state.get("ollama") or {}
    comfy = state.get("comfyui") or {}
    storage_state = state.get("storage") or {}
    recent = state.get("recent") or []

    lines = [
        "ÉTAT RÉEL IA MANAGER",
        f"CPU: {sys.get('cpu','inconnu')} · {sys.get('cpu_count','?')} threads",
        f"GPU: {sys.get('gpu_type','inconnu')} · VRAM {float(sys.get('vram_gb') or 0):.1f} Go",
        f"RAM: {float(sys.get('ram_gb') or 0):.1f} Go · libre {float(sys.get('ram_available_gb') or 0):.1f} Go",
        f"Profil recommandations: {profile.get('name','aucun')}",
        f"Ollama: {'démarré' if ollama.get('running') else 'arrêté'} · modèles: {', '.join(ollama.get('models') or []) or 'aucun'}",
        f"Dossier Ollama: {ollama.get('models_dir','')}",
        f"ComfyUI: installé={comfy.get('installed')} · python={comfy.get('python')} · serveur8188={comfy.get('running')}",
        f"Chemin ComfyUI: {comfy.get('path','') or 'inconnu'}",
        f"Stockage modèles IA Manager: {storage_state.get('app_models','')} · libre {float(storage_state.get('app_models_free_gb') or 0):.1f} Go",
        f"Conversions: {storage_state.get('conversions','')}",
        f"Sauvegardes: {storage_state.get('backups','')}",
        f"Git: {state.get('git') or 'introuvable'}",
        f"Python PATH: {state.get('python') or 'introuvable'}",
        "",
        "ÉVÉNEMENTS RÉCENTS",
    ]
    for row in recent[:12]:
        lines.append(
            f"- {row.get('created','')} | {row.get('kind','')} | {row.get('status','')} | "
            f"{row.get('title','')} | {row.get('detail','')}"
        )
    if not recent:
        lines.append("- aucun événement")
    return "\n".join(lines)


def _recent_failures(state):
    return [
        r for r in state.get("recent", [])
        if r.get("status") in ("error", "warning", "failed", "interrupted")
    ][:8]


def direct_answer(question, state):
    q = (question or "").strip().casefold()
    ollama = state["ollama"]
    comfy = state["comfyui"]
    sys = state["system"]
    storage_state = state["storage"]

    if not q:
        return "Écrivez une question ou utilisez un des boutons rapides.", ""

    if "comfy" in q:
        problems = []
        if not comfy.get("installed"):
            problems.append("ComfyUI n’est pas détecté comme installé.")
        if not comfy.get("python"):
            problems.append("Le Python isolé de ComfyUI n’est pas détecté.")
        if not comfy.get("running"):
            problems.append("Le port local 8188 est fermé : le serveur ComfyUI ne semble pas démarré.")
        if not problems:
            text = (
                "ComfyUI semble prêt : installation détectée, Python présent et port 8188 ouvert.\n\n"
                f"Dossier : {comfy.get('path') or 'non déterminé'}\n"
                "Si un workflow reste rouge, le problème est probablement un modèle, un nœud ou une entrée manquante dans le workflow."
            )
        else:
            text = "J’ai trouvé :\n• " + "\n• ".join(problems)
            text += "\n\nOuvrez « Outils locaux » ou « Centre de santé » pour réparer / diagnostiquer."
        return text, "creative_tools_tab"

    if "ollama" in q:
        if not ollama.get("running"):
            return (
                "Ollama ne répond pas actuellement sur le port 11434. "
                "Démarrez Ollama puis relancez le diagnostic. "
                f"Le dossier de modèles configuré est : {ollama.get('models_dir')}",
                "health_tab",
            )
        models = ollama.get("models") or []
        return (
            f"Ollama répond correctement. {len(models)} modèle(s) détecté(s) : "
            + (", ".join(models[:20]) if models else "aucun")
            + f"\n\nDossier : {ollama.get('models_dir')}",
            "smart_library_tab",
        )

    if any(word in q for word in ("modèle", "modele", "model")) and any(
        word in q for word in ("quel", "adapt", "conseil", "choisir", "compatible")
    ):
        vram = float(sys.get("vram_gb") or 0)
        ram = float(sys.get("ram_gb") or 0)
        if vram >= 20:
            advice = "vous pouvez regarder les 20–32B quantifiés, tout en vérifiant la taille réelle."
        elif vram >= 12:
            advice = "les 12–14B sont une bonne zone de départ ; les plus gros peuvent déborder en RAM."
        elif vram >= 8:
            advice = "privilégiez les 7–9B pour garder de bonnes performances."
        elif vram >= 5:
            advice = "privilégiez les 3–4B ; les 7B peuvent être plus lents ou déborder en RAM."
        else:
            advice = "privilégiez les petits modèles 1–3B."
        return (
            f"Matériel détecté : {sys.get('gpu_type','GPU inconnu')} · {vram:.1f} Go VRAM · {ram:.1f} Go RAM.\n\n"
            f"Pour ce matériel, {advice}\n"
            "La Bibliothèque IA peut filtrer les modèles selon la compatibilité estimée.",
            "smart_library_tab",
        )

    if any(word in q for word in ("où", "ou ", "dossier", "chemin", "stock")):
        return (
            "Emplacements connus :\n"
            f"• Modèles Ollama : {storage_state.get('ollama_models')}\n"
            f"• Modèles / téléchargements IA Manager : {storage_state.get('app_models')}\n"
            f"• Conversions : {storage_state.get('conversions')}\n"
            f"• Sauvegardes : {storage_state.get('backups')}\n"
            f"• ComfyUI : {comfy.get('path') or 'non déterminé'}",
            "storage_tab",
        )

    if any(word in q for word in ("échoué", "echoue", "erreur", "problème", "probleme", "raté", "rate")):
        failures = _recent_failures(state)
        if not failures:
            return (
                "Je ne vois pas d’échec récent dans l’Historique universel. "
                "Lancez le Centre de santé si le problème est en cours.",
                "health_tab",
            )
        lines = []
        for row in failures:
            lines.append(
                f"• {row.get('created','')} — {row.get('title','')} : {row.get('detail','') or row.get('status','')}"
            )
        return "Échecs / avertissements récents :\n" + "\n".join(lines), "history_tab"

    if "espace" in q or "disque" in q or "place" in q:
        free = float(storage_state.get("app_models_free_gb") or 0)
        return (
            f"Le disque utilisé pour les modèles IA Manager a environ {free:.1f} Go libres.\n"
            f"Dossier : {storage_state.get('app_models')}\n\n"
            "Ouvrez Stockage pour voir les plus gros fichiers, temporaires et doublons potentiels.",
            "storage_tab",
        )

    if "histor" in q or "récent" in q or "recent" in q:
        recent = state.get("recent") or []
        if not recent:
            return "L’Historique universel est vide pour le moment.", "history_tab"
        lines = [
            f"• {r.get('created','')} — {r.get('title','')} ({r.get('status','')})"
            for r in recent[:8]
        ]
        return "Derniers événements :\n" + "\n".join(lines), "history_tab"

    if "santé" in q or "sante" in q or "diagnostic" in q:
        return (
            "Le diagnostic global vérifie Python, Git, Ollama, GPU, ComfyUI, ports et stockage. "
            "Je peux vous y envoyer directement.",
            "health_tab",
        )

    return (
        "Je peux répondre directement sur l’état d’IA Manager : ComfyUI, Ollama, modèles, chemins, "
        "stockage, erreurs récentes et compatibilité matérielle.\n\n"
        "Pour une question plus libre, choisissez un modèle Ollama dans cet assistant puis utilisez « Réponse enrichie ».",
        "",
    )


def ollama_prompt(question, state):
    return (
        "Tu es l'assistant local intégré à IA Manager. Réponds en français, de façon concise et pratique. "
        "Base-toi uniquement sur l'état fourni pour les faits concernant cette installation. "
        "Si une information n'est pas présente, dis qu'elle n'est pas vérifiée. "
        "Ne prétends jamais avoir exécuté, réparé, déplacé, installé ou supprimé quelque chose. "
        "Tu peux proposer l'écran IA Manager approprié.\n\n"
        + context_text(state)
        + "\n\nQUESTION UTILISATEUR:\n"
        + question
    )
