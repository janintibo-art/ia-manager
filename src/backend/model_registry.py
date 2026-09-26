"""Catalogue des modèles IA locaux (via Ollama), classés par catégorie,
avec l'évaluation de compatibilité et les recommandations selon le PC."""

from typing import Dict, List, Optional

CATEGORIES: Dict[str, Dict[str, str]] = {
    "chat": {
        "label": "💬 Discussion",
        "desc": "Assistants généralistes : répondre aux questions, rédiger, résumer, traduire.",
    },
    "code": {
        "label": "💻 Code",
        "desc": "Spécialisés en programmation : écrire, expliquer, corriger et compléter du code.",
    },
    "reasoning": {
        "label": "🧠 Raisonnement",
        "desc": "Modèles qui « réfléchissent » étape par étape avant de répondre : maths, logique, "
                "problèmes complexes. Plus lents mais plus fiables sur les questions difficiles.",
    },
    "vision": {
        "label": "🖼️ Images",
        "desc": "Comprennent les images : décrire une photo, lire un document scanné, analyser un "
                "graphique. Ils ne créent pas d'images (la génération d'images n'est pas gérée par Ollama).",
    },
    "light": {
        "label": "🪶 Légers",
        "desc": "Très petits modèles pour PC modestes, portables ou sans carte graphique. "
                "Rapides mais moins précis.",
    },
}

# size_gb : taille du téléchargement ≈ mémoire occupée par le modèle.
# quality : 1 à 5, niveau des réponses dans sa catégorie.
# french : 1 à 3, qualité en français.
MODELS: List[Dict] = [
    # ---------------- Discussion ----------------
    {"id": "llama3.2:3b", "name": "Llama 3.2 3B", "category": "chat", "editor": "Meta",
     "params": "3 milliards", "size_gb": 2.0, "quality": 2, "french": 2, "context": "128k",
     "desc": "Petit assistant généraliste de Meta, rapide même sans carte graphique.",
     "strengths": ["Très rapide", "Tourne sur presque tous les PC", "Bon pour les questions simples"],
     "weaknesses": ["Se trompe plus souvent sur les sujets pointus"],
     "ideal": "Questions rapides, reformulation, petits résumés."},
    {"id": "gemma3:4b", "name": "Gemma 3 4B", "category": "chat", "editor": "Google",
     "params": "4 milliards", "size_gb": 3.3, "quality": 3, "french": 3, "context": "128k",
     "desc": "Petit modèle de Google, étonnamment bon pour sa taille et très correct en français. "
             "Il sait aussi lire les images.",
     "strengths": ["Excellent rapport qualité/taille", "Bon français", "Comprend les images"],
     "weaknesses": ["Moins solide en raisonnement long"],
     "ideal": "Assistant du quotidien sur un PC moyen."},
    {"id": "llama3.1:8b", "name": "Llama 3.1 8B", "category": "chat", "editor": "Meta",
     "params": "8 milliards", "size_gb": 4.9, "quality": 3, "french": 2, "context": "128k",
     "desc": "Le généraliste de référence de Meta, très utilisé et bien équilibré.",
     "strengths": ["Polyvalent", "Stable et fiable", "Très bien supporté"],
     "weaknesses": ["Français correct mais pas le meilleur"],
     "ideal": "Usage général avec une carte graphique de 6-8 Go."},
    {"id": "qwen3:8b", "name": "Qwen 3 8B", "category": "chat", "editor": "Alibaba",
     "params": "8 milliards", "size_gb": 5.2, "quality": 4, "french": 3, "context": "128k",
     "desc": "Modèle récent d'Alibaba, parmi les meilleurs de sa taille. Peut activer un mode réflexion.",
     "strengths": ["Très bon niveau général", "Multilingue", "Mode réflexion intégré"],
     "weaknesses": ["Un peu bavard"],
     "ideal": "Meilleur choix général pour une carte graphique de 8 Go."},
    {"id": "mistral-nemo:12b", "name": "Mistral Nemo 12B", "category": "chat", "editor": "Mistral AI / NVIDIA",
     "params": "12 milliards", "size_gb": 7.1, "quality": 3, "french": 3, "context": "128k",
     "desc": "Modèle de l'entreprise française Mistral AI, excellent en français.",
     "strengths": ["Très bon français", "Style naturel", "Long contexte"],
     "weaknesses": ["Moins fort en maths que Qwen"],
     "ideal": "Rédaction et échanges en français."},
    {"id": "gemma3:12b", "name": "Gemma 3 12B", "category": "chat", "editor": "Google",
     "params": "12 milliards", "size_gb": 8.1, "quality": 4, "french": 3, "context": "128k",
     "desc": "Version intermédiaire de Gemma 3 : belle qualité d'écriture et vision intégrée.",
     "strengths": ["Écriture soignée", "Bon français", "Comprend les images"],
     "weaknesses": ["Demande 10 Go de VRAM pour être rapide"],
     "ideal": "Rédaction de qualité avec une carte de 10-12 Go."},
    {"id": "qwen3:14b", "name": "Qwen 3 14B", "category": "chat", "editor": "Alibaba",
     "params": "14 milliards", "size_gb": 9.3, "quality": 4, "french": 3, "context": "128k",
     "desc": "Très haut niveau pour un modèle local, bon compromis pour les cartes de 12 Go.",
     "strengths": ["Excellent niveau général", "Bon raisonnement", "Multilingue"],
     "weaknesses": ["Lent sans bonne carte graphique"],
     "ideal": "Assistant exigeant sur un PC de joueur."},
    {"id": "mistral-small:24b", "name": "Mistral Small 24B", "category": "chat", "editor": "Mistral AI",
     "params": "24 milliards", "size_gb": 14.0, "quality": 5, "french": 3, "context": "128k",
     "desc": "Le modèle « moyen » de Mistral AI, très bon en français et en suivi d'instructions.",
     "strengths": ["Excellent français", "Réponses précises", "Suit bien les consignes"],
     "weaknesses": ["16 Go de VRAM conseillés"],
     "ideal": "Travail sérieux en français sur un gros PC."},
    {"id": "gemma3:27b", "name": "Gemma 3 27B", "category": "chat", "editor": "Google",
     "params": "27 milliards", "size_gb": 17.0, "quality": 5, "french": 3, "context": "128k",
     "desc": "Le plus grand Gemma 3 : qualité proche des assistants en ligne.",
     "strengths": ["Très haute qualité", "Comprend les images", "Très bon français"],
     "weaknesses": ["Carte 24 Go ou beaucoup de RAM"],
     "ideal": "Meilleure qualité possible sur une carte 24 Go."},
    {"id": "qwen3:32b", "name": "Qwen 3 32B", "category": "chat", "editor": "Alibaba",
     "params": "32 milliards", "size_gb": 20.0, "quality": 5, "french": 3, "context": "128k",
     "desc": "Un des meilleurs modèles ouverts de taille moyenne.",
     "strengths": ["Niveau très élevé", "Fort en raisonnement et en code"],
     "weaknesses": ["Très gourmand en mémoire"],
     "ideal": "PC haut de gamme (24 Go de VRAM)."},
    {"id": "llama3.3:70b", "name": "Llama 3.3 70B", "category": "chat", "editor": "Meta",
     "params": "70 milliards", "size_gb": 43.0, "quality": 5, "french": 3, "context": "128k",
     "desc": "Le très grand modèle de Meta. Qualité maximale, mais il faut énormément de mémoire.",
     "strengths": ["Qualité maximale du catalogue"],
     "weaknesses": ["48 Go de mémoire minimum", "Très lent sans plusieurs GPU"],
     "ideal": "Stations de travail avec 64 Go de RAM ou plus."},

    # ---------------- Code ----------------
    {"id": "qwen2.5-coder:1.5b", "name": "Qwen 2.5 Coder 1.5B", "category": "code", "editor": "Alibaba",
     "params": "1,5 milliard", "size_gb": 1.0, "quality": 2, "french": 2, "context": "32k",
     "desc": "Minuscule modèle de code, idéal pour l'autocomplétion rapide.",
     "strengths": ["Ultra rapide", "Tourne partout"],
     "weaknesses": ["Limité pour les tâches complexes"],
     "ideal": "Autocomplétion dans un éditeur de code."},
    {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B", "category": "code", "editor": "Alibaba",
     "params": "7 milliards", "size_gb": 4.7, "quality": 4, "french": 2, "context": "128k",
     "desc": "Excellent modèle de programmation, très populaire pour son rapport qualité/taille.",
     "strengths": ["Très bon en Python, JS, C#…", "Explique bien le code"],
     "weaknesses": ["Moins bon hors programmation"],
     "ideal": "Aide à la programmation avec une carte de 6-8 Go."},
    {"id": "deepseek-coder-v2:16b", "name": "DeepSeek Coder V2 16B", "category": "code", "editor": "DeepSeek",
     "params": "16 milliards (MoE)", "size_gb": 8.9, "quality": 4, "french": 2, "context": "128k",
     "desc": "Modèle de code rapide grâce à son architecture « mixture of experts ».",
     "strengths": ["Rapide pour sa taille", "Nombreux langages supportés"],
     "weaknesses": ["Français moyen"],
     "ideal": "Projets de code variés sur une carte de 10-12 Go."},
    {"id": "qwen2.5-coder:14b", "name": "Qwen 2.5 Coder 14B", "category": "code", "editor": "Alibaba",
     "params": "14 milliards", "size_gb": 9.0, "quality": 4, "french": 2, "context": "128k",
     "desc": "Version plus puissante de Qwen Coder, pour du code plus long et plus complexe.",
     "strengths": ["Très fiable", "Bonne compréhension de gros fichiers"],
     "weaknesses": ["Demande 12 Go de VRAM pour être rapide"],
     "ideal": "Développement sérieux sur un PC de joueur."},
    {"id": "devstral:24b", "name": "Devstral 24B", "category": "code", "editor": "Mistral AI",
     "params": "24 milliards", "size_gb": 14.0, "quality": 5, "french": 3, "context": "128k",
     "desc": "Modèle de Mistral AI conçu pour travailler sur des projets de code entiers.",
     "strengths": ["Comprend des projets complets", "Bon français"],
     "weaknesses": ["16 Go de VRAM conseillés"],
     "ideal": "Agents de code et gros projets."},
    {"id": "qwen2.5-coder:32b", "name": "Qwen 2.5 Coder 32B", "category": "code", "editor": "Alibaba",
     "params": "32 milliards", "size_gb": 20.0, "quality": 5, "french": 2, "context": "128k",
     "desc": "Le meilleur modèle de code local de la gamme Qwen.",
     "strengths": ["Niveau proche des services en ligne"],
     "weaknesses": ["Carte 24 Go conseillée"],
     "ideal": "Programmation intensive sur PC haut de gamme."},

    # ---------------- Raisonnement ----------------
    {"id": "deepseek-r1:1.5b", "name": "DeepSeek R1 1.5B", "category": "reasoning", "editor": "DeepSeek",
     "params": "1,5 milliard", "size_gb": 1.1, "quality": 1, "french": 1, "context": "128k",
     "desc": "Toute petite version de DeepSeek R1, pour découvrir les modèles qui réfléchissent.",
     "strengths": ["Tourne partout"],
     "weaknesses": ["Peu fiable", "Français faible"],
     "ideal": "Tests sur petit PC."},
    {"id": "deepseek-r1:8b", "name": "DeepSeek R1 8B", "category": "reasoning", "editor": "DeepSeek",
     "params": "8 milliards", "size_gb": 5.2, "quality": 3, "french": 2, "context": "128k",
     "desc": "Réfléchit longuement avant de répondre : bon en maths et en logique.",
     "strengths": ["Bon raisonnement", "Montre sa réflexion"],
     "weaknesses": ["Lent (beaucoup de texte de réflexion)"],
     "ideal": "Exercices de maths et problèmes logiques."},
    {"id": "deepseek-r1:14b", "name": "DeepSeek R1 14B", "category": "reasoning", "editor": "DeepSeek",
     "params": "14 milliards", "size_gb": 9.0, "quality": 4, "french": 2, "context": "128k",
     "desc": "Version plus précise de DeepSeek R1, nettement plus fiable que la 8B.",
     "strengths": ["Raisonnement solide"],
     "weaknesses": ["Lent sans bonne carte graphique"],
     "ideal": "Problèmes complexes sur un PC de joueur."},
    {"id": "phi4:14b", "name": "Phi-4 14B", "category": "reasoning", "editor": "Microsoft",
     "params": "14 milliards", "size_gb": 9.1, "quality": 4, "french": 2, "context": "16k",
     "desc": "Modèle de Microsoft entraîné pour le raisonnement et les sciences.",
     "strengths": ["Excellent en maths et sciences", "Réponses directes"],
     "weaknesses": ["Contexte court (16k)"],
     "ideal": "Maths, physique, logique."},
    {"id": "deepseek-r1:32b", "name": "DeepSeek R1 32B", "category": "reasoning", "editor": "DeepSeek",
     "params": "32 milliards", "size_gb": 20.0, "quality": 5, "french": 2, "context": "128k",
     "desc": "Grande version de DeepSeek R1, raisonnement de très haut niveau.",
     "strengths": ["Très fort sur les problèmes difficiles"],
     "weaknesses": ["Carte 24 Go conseillée", "Lent"],
     "ideal": "Problèmes difficiles sur PC haut de gamme."},
    {"id": "qwq:32b", "name": "QwQ 32B", "category": "reasoning", "editor": "Alibaba",
     "params": "32 milliards", "size_gb": 20.0, "quality": 5, "french": 2, "context": "128k",
     "desc": "Modèle de raisonnement d'Alibaba, concurrent direct de DeepSeek R1.",
     "strengths": ["Excellent en maths et code"],
     "weaknesses": ["Très long à répondre"],
     "ideal": "Raisonnement poussé sur PC haut de gamme."},

    # ---------------- Images ----------------
    {"id": "moondream:1.8b", "name": "Moondream 2", "category": "vision", "editor": "Vikhyat",
     "params": "1,8 milliard", "size_gb": 1.7, "quality": 2, "french": 1, "context": "2k",
     "desc": "Minuscule modèle de vision : décrit rapidement une image.",
     "strengths": ["Très léger et rapide"],
     "weaknesses": ["Répond surtout en anglais", "Descriptions simples"],
     "ideal": "Décrire des images sur petit PC."},
    {"id": "llava:7b", "name": "LLaVA 7B", "category": "vision", "editor": "LLaVA",
     "params": "7 milliards", "size_gb": 4.7, "quality": 2, "french": 2, "context": "4k",
     "desc": "Le modèle de vision historique : décrit et analyse des images.",
     "strengths": ["Très répandu", "Fiable pour les descriptions"],
     "weaknesses": ["Dépassé par les modèles récents"],
     "ideal": "Description d'images simple."},
    {"id": "minicpm-v:8b", "name": "MiniCPM-V 8B", "category": "vision", "editor": "OpenBMB",
     "params": "8 milliards", "size_gb": 5.5, "quality": 4, "french": 2, "context": "32k",
     "desc": "Très bon pour lire du texte dans les images (OCR) et analyser des documents.",
     "strengths": ["Excellent OCR", "Documents et captures d'écran"],
     "weaknesses": ["Moins bon en conversation"],
     "ideal": "Lire des factures, documents scannés, captures."},
    {"id": "qwen2.5vl:7b", "name": "Qwen 2.5 VL 7B", "category": "vision", "editor": "Alibaba",
     "params": "7 milliards", "size_gb": 6.0, "quality": 4, "french": 3, "context": "128k",
     "desc": "Modèle de vision récent et polyvalent : photos, graphiques, documents.",
     "strengths": ["Très bonne compréhension d'image", "Bon français"],
     "weaknesses": ["8 Go de VRAM conseillés"],
     "ideal": "Meilleur choix vision pour une carte de 8 Go."},
    {"id": "llama3.2-vision:11b", "name": "Llama 3.2 Vision 11B", "category": "vision", "editor": "Meta",
     "params": "11 milliards", "size_gb": 7.8, "quality": 4, "french": 2, "context": "128k",
     "desc": "Version vision de Llama : analyse détaillée des images.",
     "strengths": ["Analyse détaillée", "Raisonne sur les graphiques"],
     "weaknesses": ["Français moyen"],
     "ideal": "Analyse d'images poussée avec une carte de 10-12 Go."},

    # ---------------- Légers ----------------
    {"id": "gemma3:1b", "name": "Gemma 3 1B", "category": "light", "editor": "Google",
     "params": "1 milliard", "size_gb": 0.8, "quality": 1, "french": 2, "context": "32k",
     "desc": "Le plus petit modèle du catalogue. Fonctionne même sur un vieux portable.",
     "strengths": ["Extrêmement léger", "Instantané"],
     "weaknesses": ["Réponses limitées"],
     "ideal": "Vieux PC, tests, tâches très simples."},
    {"id": "llama3.2:1b", "name": "Llama 3.2 1B", "category": "light", "editor": "Meta",
     "params": "1 milliard", "size_gb": 1.3, "quality": 1, "french": 1, "context": "128k",
     "desc": "Mini version de Llama, rapide sur processeur seul.",
     "strengths": ["Très rapide sans GPU"],
     "weaknesses": ["Français faible", "Se trompe souvent"],
     "ideal": "Résumés courts sur PC sans carte graphique."},
    {"id": "qwen3:1.7b", "name": "Qwen 3 1.7B", "category": "light", "editor": "Alibaba",
     "params": "1,7 milliard", "size_gb": 1.4, "quality": 2, "french": 2, "context": "32k",
     "desc": "Petit modèle récent, meilleur que la moyenne des modèles de cette taille.",
     "strengths": ["Bon niveau pour sa taille", "Multilingue"],
     "weaknesses": ["Limité sur les sujets complexes"],
     "ideal": "Meilleur petit modèle pour PC sans GPU."},
    {"id": "phi3:mini", "name": "Phi-3 Mini 3.8B", "category": "light", "editor": "Microsoft",
     "params": "3,8 milliards", "size_gb": 2.2, "quality": 2, "french": 1, "context": "128k",
     "desc": "Petit modèle de Microsoft, bon en raisonnement simple.",
     "strengths": ["Bon en logique pour sa taille"],
     "weaknesses": ["Surtout en anglais"],
     "ideal": "Petits calculs et logique sur PC modeste."},
]

FIT_LABELS = {
    "gpu": ("✅", "Rapide", "Tient entièrement dans la carte graphique"),
    "mixed": ("⚠️", "Moyen", "Réparti entre carte graphique et RAM : plus lent"),
    "cpu": ("🐢", "Lent", "Tourne sur le processeur et la RAM"),
    "no": ("❌", "Trop gros", "Pas assez de mémoire sur ce PC"),
}


def get_model(model_id: str) -> Optional[Dict]:
    for m in MODELS:
        if m["id"] == model_id:
            return m
    return None


def models_in(category: Optional[str]) -> List[Dict]:
    if not category:
        return list(MODELS)
    return [m for m in MODELS if m["category"] == category]


def memory_needed_gb(model: Dict) -> float:
    """Mémoire réellement utilisée : poids du modèle + ~20 % pour le contexte"""
    return model["size_gb"] * 1.2


def evaluate_fit(model: Dict, info: Optional[Dict]) -> str:
    """Renvoie 'gpu', 'mixed', 'cpu' ou 'no' selon la machine"""
    if not info:
        return "mixed"
    need = memory_needed_gb(model)
    vram = max(0.0, info.get("vram_gb", 0.0) - 0.5)
    ram = info.get("ram_gb", 0.0) * 0.6  # on laisse 40 % de la RAM à Windows
    if vram > 0 and need <= vram:
        return "gpu"
    if need <= vram + ram:
        return "mixed" if vram > 0 else "cpu"
    return "no"


def recommend(info: Dict, priority: str = "Équilibré") -> Dict[str, Optional[Dict]]:
    """Meilleur modèle par catégorie selon le PC et la priorité.

    Rapidité : le meilleur qui tient entièrement en VRAM (ou le plus léger sans GPU).
    Équilibré : le meilleur en VRAM, sinon un léger débordement en RAM.
    Qualité : le meilleur qui tient dans VRAM + RAM.
    """
    vram = info.get("vram_gb", 0.0)
    result: Dict[str, Optional[Dict]] = {}

    for cat in CATEGORIES:
        candidates = []
        for m in models_in(cat):
            fit = evaluate_fit(m, info)
            if fit == "no":
                continue
            need = memory_needed_gb(m)
            if priority == "Rapidité maximale":
                if vram > 0 and fit != "gpu":
                    continue
                if vram == 0 and need > 4:
                    continue
            elif priority == "Équilibré":
                if vram > 0 and fit != "gpu" and need > vram * 1.3:
                    continue
                if vram == 0 and need > 7:
                    continue
            candidates.append(m)

        if not candidates:
            result[cat] = None
            continue

        candidates.sort(key=lambda m: (m["quality"], m["french"], -m["size_gb"]), reverse=True)
        if priority == "Rapidité maximale":
            # à qualité égale on préfère le plus petit (déjà trié par -size)
            result[cat] = candidates[0]
        else:
            best_q = candidates[0]["quality"]
            same = [m for m in candidates if m["quality"] == best_q]
            same.sort(key=lambda m: (m["french"], m["size_gb"]), reverse=True)
            result[cat] = same[0]

    return result
