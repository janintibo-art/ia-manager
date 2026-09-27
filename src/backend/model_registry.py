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
    "lang": {
        "label": "🌍 Langues",
        "desc": "Traduction et usage multilingue : traduire des textes, écrire dans d'autres langues, "
                "échanger avec des personnes qui ne parlent pas français.",
    },
    "special": {
        "label": "🧰 Spécialisés",
        "desc": "Modèles entraînés pour un seul métier : maths, bases de données SQL, médecine, "
                "extraction d'informations, conversion de pages web.",
    },
    "uncensored": {
        "label": "🔓 IA moins filtrées",
        "desc": "Pour commencer : Dolphin Phi sur un petit PC, Dolphin Mistral pour discuter, "
                "DolphinCoder pour programmer. Les modèles plus grands demandent davantage de RAM. "
                "« Moins filtré » décrit l'entraînement annoncé par leurs auteurs ; cela ne garantit "
                "ni l'exactitude ni l'absence de refus. Les longues fenêtres de contexte consomment "
                "davantage de mémoire que la taille du téléchargement affichée.",
    },
    "creative": {
        "label": "✍️ Création et histoires",
        "desc": "Inventez des personnages, dialogues, quêtes et scénarios de jeux. "
                "Pour commencer : Qwen 2.5 3B sur un PC modeste, Qwen 3 4B pour des idées rapides, "
                "Qwen 2.5 14B pour des récits plus détaillés. Dans le Chat, essayez : "
                "« Imagine une quête fantasy avec un choix difficile et trois issues ».",
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

def _m(id, name, category, editor, params, size_gb, quality, french, context, desc,
       strengths, weaknesses, ideal, discovery=True):
    return {"id": id, "name": name, "category": category, "editor": editor, "params": params,
            "size_gb": size_gb, "quality": quality, "french": french, "context": context,
            "desc": desc, "strengths": strengths, "weaknesses": weaknesses, "ideal": ideal,
            "discovery": discovery}


# Modèles moins connus (badge « Découverte »), noms et tailles vérifiés sur ollama.com
MODELS += [
    # ---------------- Discussion ----------------
    _m("granite4:micro", "Granite 4 Micro", "chat", "IBM", "3 milliards", 2.1, 2, 2, "128k",
       "Petit modèle d'IBM pensé pour les entreprises : suit très bien les consignes et sait utiliser des outils.",
       ["Obéit précisément aux consignes", "Léger", "Licence très libre (Apache 2.0)"],
       ["Style un peu sec"], "Assistant qui doit respecter des règles précises."),
    _m("granite3.3:8b", "Granite 3.3 8B", "chat", "IBM", "8 milliards", 4.9, 3, 2, "128k",
       "Modèle professionnel d'IBM, sérieux et fiable, avec un mode réflexion.",
       ["Réponses sobres et fiables", "Bon pour résumer des documents"],
       ["Peu créatif"], "Usage professionnel, résumés, e-mails."),
    _m("falcon3:10b", "Falcon 3 10B", "chat", "TII (Émirats)", "10 milliards", 6.3, 3, 2, "32k",
       "Modèle de l'institut TII d'Abu Dhabi, bon en sciences et en maths pour sa taille.",
       ["Bon en maths et sciences", "Bonne vitesse"],
       ["Français correct sans plus"], "Questions scientifiques avec une carte de 8 Go."),
    _m("olmo2:13b", "OLMo 2 13B", "chat", "Allen Institute (AI2)", "13 milliards", 8.4, 3, 1, "4k",
       "Modèle 100 % ouvert : données d'entraînement, code et poids publiés. Idéal pour la transparence.",
       ["Entièrement ouvert et documenté", "Bonne qualité générale"],
       ["Contexte court (4k)", "Surtout en anglais"], "Recherche, curiosité, usage éthique."),
    _m("tulu3:8b", "Tülu 3 8B", "chat", "Allen Institute (AI2)", "8 milliards", 3, 3, 2, "128k",
       "Version de Llama retravaillée par AI2 pour mieux suivre les instructions.",
       ["Suit bien les consignes", "Recette d'entraînement publique"],
       ["Moins connu, moins de retours d'utilisateurs"], "Assistant général alternatif à Llama."),
    _m("hermes3:8b", "Hermes 3 8B", "chat", "Nous Research", "8 milliards", 4.7, 3, 2, "128k",
       "Modèle communautaire réputé pour le jeu de rôle, l'écriture créative et les longues conversations.",
       ["Très bon en écriture créative", "Garde bien un personnage", "Suit les consignes système"],
       ["Moins rigoureux sur les faits"], "Histoires, jeux de rôle, personnages."),
    _m("dolphin3:8b", "Dolphin 3 8B", "chat", "Cognitive Computations", "8 milliards", 4.9, 3, 2, "128k",
       "Modèle très « obéissant » : il suit les consignes du projet sans ajouter de morale ni de refus inutiles.",
       ["Respecte fidèlement les consignes", "Bon pour le code et les agents"],
       ["C'est à vous de cadrer son comportement"], "Assistant entièrement piloté par vos consignes."),
    _m("exaone3.5:7.8b", "EXAONE 3.5 7.8B", "chat", "LG AI Research", "7,8 milliards", 4.8, 3, 1, "32k",
       "Modèle de LG, bilingue anglais/coréen, bon en suivi d'instructions longues.",
       ["Bon sur les longs documents", "Rigoureux"],
       ["Français faible"], "Documents longs en anglais."),
    _m("cogito:14b", "Cogito 14B", "chat", "Deep Cogito", "14 milliards", 9.0, 4, 2, "128k",
       "Modèle hybride : répond directement ou réfléchit longuement selon la difficulté.",
       ["Deux modes (rapide / réflexion)", "Très bon niveau"],
       ["Demande 12 Go de VRAM pour être rapide"], "Assistant polyvalent qui sait aussi raisonner."),
    _m("lfm2:24b", "LFM2 24B", "chat", "Liquid AI", "24 milliards (2 actifs)", 14.0, 4, 2, "32k",
       "Architecture originale : seulement 2 milliards de paramètres travaillent à chaque mot, "
       "il est donc rapide même en partie en RAM.",
       ["Rapide pour sa taille", "Fonctionne bien sur processeur"],
       ["14 Go de mémoire nécessaire"], "PC avec beaucoup de RAM mais une petite carte graphique."),
    _m("gemma3n:e4b", "Gemma 3n E4B", "chat", "Google", "8 milliards (4 effectifs)", 7.5, 3, 3, "32k",
       "Version de Gemma conçue pour les téléphones et portables, très économe en calcul.",
       ["Économe", "Bon français"],
       ["Fichier plus gros que sa puissance"], "Portables et PC sans grosse carte graphique."),

    # ---------------- Code ----------------
    _m("starcoder2:7b", "StarCoder2 7B", "code", "BigCode (Hugging Face)", "7 milliards", 4.0, 3, 1, "16k",
       "Modèle de complétion de code entraîné sur plus de 600 langages de programmation.",
       ["Énormément de langages", "Complétion rapide"],
       ["Ne discute pas, il complète du code"], "Autocomplétion dans un éditeur."),
    _m("codegemma:7b", "CodeGemma 7B", "code", "Google", "7 milliards", 5.0, 3, 2, "8k",
       "Version de Gemma spécialisée en programmation.",
       ["Bon en Python et JavaScript", "Explications claires"],
       ["Contexte court (8k)"], "Petits scripts et explications de code."),
    _m("yi-coder:9b", "Yi-Coder 9B", "code", "01.AI", "9 milliards", 5.0, 4, 1, "128k",
       "Modèle de code performant avec un très long contexte : il peut lire de gros fichiers.",
       ["Long contexte", "52 langages"],
       ["Répond surtout en anglais"], "Travailler sur de gros fichiers de code."),
    _m("opencoder:8b", "OpenCoder 8B", "code", "INF / M-A-P", "8 milliards", 4.7, 3, 1, "8k",
       "Modèle de code entièrement ouvert, données d'entraînement comprises.",
       ["Transparent", "Bon en Python"],
       ["Contexte court"], "Programmation Python, projets open source."),
    _m("granite-code:8b", "Granite Code 8B", "code", "IBM", "8 milliards", 4.6, 3, 1, "128k",
       "Modèle de code d'IBM, entraîné uniquement sur du code à licence libre.",
       ["Sans risque de licence", "Bon en Java et SQL"],
       ["Moins fort que Qwen Coder"], "Code professionnel, projets d'entreprise."),
    _m("deepcoder:14b", "DeepCoder 14B", "code", "Agentica", "14 milliards", 9.0, 4, 1, "64k",
       "Modèle de code qui réfléchit avant d'écrire : très bon sur les problèmes d'algorithmique.",
       ["Excellent en algorithmique", "Raisonne sur le code"],
       ["Lent (réflexion longue)"], "Exercices de programmation difficiles."),
    _m("codestral:22b", "Codestral 22B", "code", "Mistral AI", "22 milliards", 13.0, 4, 3, "32k",
       "Le modèle de code de Mistral AI, fort en complétion et bon en français.",
       ["80 langages", "Bon français", "Complétion au milieu du code"],
       ["Licence non commerciale"], "Développement avec explications en français."),
    _m("qwen3-coder:30b", "Qwen3 Coder 30B", "code", "Alibaba", "30 milliards (3 actifs)", 19.0, 5, 2, "256k",
       "Le modèle de code récent d'Alibaba, rapide grâce à son architecture « mixture of experts ».",
       ["Niveau très élevé", "Rapide pour sa taille", "Très long contexte"],
       ["20 Go de mémoire nécessaires"], "Agents de code et gros projets.", discovery=False),

    # ---------------- Raisonnement ----------------
    _m("smallthinker:3b", "SmallThinker 3B", "reasoning", "PowerInfer", "3 milliards", 3.6, 2, 1, "32k",
       "Petit modèle qui réfléchit étape par étape, basé sur Qwen 2.5.",
       ["Raisonnement sur petit PC"],
       ["Se perd sur les problèmes longs"], "Découvrir le raisonnement sans GPU."),
    _m("phi4-mini-reasoning:3.8b", "Phi-4 Mini Reasoning", "reasoning", "Microsoft", "3,8 milliards", 3.2, 3, 1, "128k",
       "Petit modèle de Microsoft spécialisé dans les maths étape par étape.",
       ["Très bon en maths pour sa taille", "Léger"],
       ["Limité hors maths"], "Maths sur un PC modeste."),
    _m("openthinker:7b", "OpenThinker 7B", "reasoning", "Open Thoughts", "7 milliards", 4.7, 3, 1, "32k",
       "Modèle de raisonnement communautaire entraîné sur des données ouvertes.",
       ["Données publiques", "Bon en maths et code"],
       ["Surtout en anglais"], "Alternative ouverte à DeepSeek R1."),
    _m("exaone-deep:7.8b", "EXAONE Deep 7.8B", "reasoning", "LG AI Research", "7,8 milliards", 4.8, 3, 1, "32k",
       "Version « réflexion » du modèle de LG, bonne en maths et en sciences.",
       ["Bon en maths", "Rigoureux"],
       ["Français faible"], "Problèmes scientifiques."),
    _m("marco-o1:7b", "Marco-o1 7B", "reasoning", "Alibaba (AIDC)", "7 milliards", 4.7, 3, 2, "32k",
       "Modèle de raisonnement expérimental qui explore plusieurs pistes avant de conclure.",
       ["Explore plusieurs solutions", "Bon en traduction nuancée"],
       ["Expérimental"], "Questions ouvertes à plusieurs réponses possibles."),
    _m("phi4-reasoning:14b", "Phi-4 Reasoning 14B", "reasoning", "Microsoft", "14 milliards", 11.0, 4, 2, "32k",
       "Version « réflexion » de Phi-4, rivalise avec des modèles bien plus gros en maths.",
       ["Excellent en maths et logique"],
       ["Réflexions très longues"], "Problèmes difficiles avec une carte de 12-16 Go."),
    _m("magistral:24b", "Magistral 24B", "reasoning", "Mistral AI", "24 milliards", 14.0, 5, 3, "40k",
       "Le modèle de raisonnement de Mistral AI, qui réfléchit directement en français.",
       ["Raisonne en français", "Très bon niveau"],
       ["16 Go de VRAM conseillés"], "Raisonnement poussé en français."),
    _m("gpt-oss:20b", "GPT-OSS 20B", "reasoning", "OpenAI", "20 milliards (MoE)", 14.0, 5, 3, "128k",
       "Le modèle ouvert d'OpenAI : raisonnement réglable (faible, moyen, fort) et bon en outils.",
       ["Très bon niveau", "Rapide pour sa taille", "Bon français"],
       ["16 Go de mémoire nécessaires"], "Assistant qui raisonne, sur un bon PC.", discovery=False),

    # ---------------- Images ----------------
    _m("qwen3-vl:4b", "Qwen3 VL 4B", "vision", "Alibaba", "4 milliards", 3.3, 3, 3, "256k",
       "Petit modèle de vision récent : photos, captures d'écran, documents.",
       ["Léger", "Bon français", "Lit bien le texte dans les images"],
       ["Moins précis que la 8B"], "Vision sur un PC modeste.", discovery=False),
    _m("qwen3-vl:8b", "Qwen3 VL 8B", "vision", "Alibaba", "8 milliards", 6.1, 5, 3, "256k",
       "Le modèle de vision le plus puissant de la famille Qwen dans cette taille.",
       ["Excellente compréhension d'image", "Bon français", "Très long contexte"],
       ["8 Go de VRAM conseillés"], "Meilleur choix vision pour une carte de 8 Go.", discovery=False),
    _m("granite3.2-vision:2b", "Granite 3.2 Vision 2B", "vision", "IBM", "2 milliards", 2.4, 3, 1, "16k",
       "Petit modèle d'IBM spécialisé dans les documents : tableaux, graphiques, formulaires.",
       ["Très bon sur les documents", "Léger"],
       ["Peu doué pour les photos"], "Lire des tableaux et graphiques."),
    _m("glm-ocr:latest", "GLM-OCR", "vision", "Zhipu AI", "moins d'1 milliard", 2.2, 4, 2, "8k",
       "Modèle dédié à la reconnaissance de texte (OCR) dans des documents complexes.",
       ["Excellent OCR", "Mises en page complexes"],
       ["Ne fait que de l'OCR"], "Numériser factures, courriers, documents scannés."),
    _m("llava-phi3:3.8b", "LLaVA Phi-3", "vision", "LLaVA / Microsoft", "3,8 milliards", 2.9, 2, 1, "4k",
       "Petite version de LLaVA basée sur Phi-3.",
       ["Léger"], ["Surtout en anglais", "Descriptions simples"], "Décrire des images sur petit PC."),
    _m("llava-llama3:8b", "LLaVA Llama 3", "vision", "LLaVA / Meta", "8 milliards", 5.5, 3, 2, "8k",
       "LLaVA reconstruit sur Llama 3, plus précis que l'original.",
       ["Descriptions détaillées"], ["Contexte court"], "Analyse de photos."),

    # ---------------- Légers ----------------
    _m("smollm2:1.7b", "SmolLM2 1.7B", "light", "Hugging Face", "1,7 milliard", 1.8, 2, 1, "8k",
       "Petit modèle de Hugging Face, étonnamment capable pour sa taille.",
       ["Très léger", "Bon en anglais"], ["Français faible"], "Vieux PC, tâches simples."),
    _m("smollm2:360m", "SmolLM2 360M", "light", "Hugging Face", "360 millions", 0.73, 1, 1, "8k",
       "Micro-modèle : tient dans moins d'1 Go.",
       ["Instantané", "Tourne partout"], ["Très limité"], "Tests, reformulations très simples."),
    _m("tinyllama:1.1b", "TinyLlama 1.1B", "light", "TinyLlama", "1,1 milliard", 0.64, 1, 1, "2k",
       "Petit Llama communautaire, pionnier des mini-modèles.",
       ["Minuscule"], ["Dépassé par les récents"], "Curiosité, très vieux PC."),
    _m("granite4:350m", "Granite 4 350M", "light", "IBM", "350 millions", 0.71, 1, 1, "32k",
       "Le plus petit Granite, pour les appareils très limités.",
       ["Ultra léger", "Suit des consignes simples"], ["Très limité"], "Classement ou tri de textes courts."),
    _m("stablelm2:1.6b", "StableLM 2 1.6B", "light", "Stability AI", "1,6 milliard", 0.98, 1, 2, "4k",
       "Petit modèle entraîné en 7 langues européennes, dont le français.",
       ["Français correct pour sa taille", "Très léger"], ["Réponses courtes"], "Petit assistant en français."),
    _m("qwen2.5:0.5b", "Qwen 2.5 0.5B", "light", "Alibaba", "500 millions", 0.4, 1, 1, "32k",
       "Le plus petit Qwen : 400 Mo seulement.",
       ["Le plus léger du catalogue"], ["Très limité"], "Tests et tâches automatiques simples."),
    _m("exaone3.5:2.4b", "EXAONE 3.5 2.4B", "light", "LG AI Research", "2,4 milliards", 1.6, 2, 1, "32k",
       "Petit modèle de LG, bon en suivi d'instructions.",
       ["Léger", "Obéissant"], ["Français faible"], "Tâches guidées sur petit PC."),
    _m("cogito:3b", "Cogito 3B", "light", "Deep Cogito", "3 milliards", 2.2, 2, 2, "128k",
       "Petite version de Cogito qui peut basculer en mode réflexion.",
       ["Mode réflexion sur petit PC"], ["Limité sur les sujets complexes"], "Portable sans carte graphique."),

    # ---------------- Langues ----------------
    _m("translategemma:4b", "TranslateGemma 4B", "lang", "Google", "4 milliards", 3.3, 3, 3, "128k",
       "Modèle de traduction de Google, basé sur Gemma 3, pour 55 langues.",
       ["Spécialisé traduction", "55 langues", "Léger"], ["Ne sert qu'à traduire"], "Traduire des textes au quotidien."),
    _m("translategemma:12b", "TranslateGemma 12B", "lang", "Google", "12 milliards", 8.1, 4, 3, "128k",
       "Version plus précise de TranslateGemma, pour des traductions soignées.",
       ["Traductions de qualité", "55 langues"], ["Demande 10 Go de VRAM"], "Traductions professionnelles."),
    _m("aya-expanse:8b", "Aya Expanse 8B", "lang", "Cohere", "8 milliards", 5.1, 3, 3, "8k",
       "Modèle multilingue de Cohere, entraîné pour 23 langues dont le français.",
       ["Excellent multilingue", "Naturel dans chaque langue"], ["Contexte court"], "Échanges en plusieurs langues."),
    _m("aya-expanse:32b", "Aya Expanse 32B", "lang", "Cohere", "32 milliards", 20.0, 5, 3, "128k",
       "Grande version d'Aya : qualité multilingue de haut niveau.",
       ["Très haute qualité en 23 langues"], ["Carte 24 Go conseillée"], "Traduction et rédaction multilingue exigeantes."),
    _m("command-r7b:7b", "Command R7B", "lang", "Cohere", "7 milliards", 5.1, 3, 3, "128k",
       "Modèle de Cohere taillé pour travailler sur vos documents (RAG), multilingue.",
       ["Cite ses sources", "Multilingue", "Long contexte"], ["Moins créatif"], "Questions sur vos propres documents."),
    _m("sailor2:8b", "Sailor2 8B", "lang", "Sea AI Lab", "8 milliards", 5.2, 3, 1, "32k",
       "Spécialisé dans les langues d'Asie du Sud-Est (vietnamien, thaï, indonésien…).",
       ["Langues d'Asie du Sud-Est"], ["Français faible"], "Communiquer en langues asiatiques."),

    # ---------------- Spécialisés ----------------
    _m("mathstral:7b", "Mathstral 7B", "special", "Mistral AI", "7 milliards", 4.1, 3, 2, "32k",
       "Modèle de Mistral AI dédié aux mathématiques et aux sciences.",
       ["Maths et sciences", "Explique les étapes"], ["Moins bon ailleurs"], "Devoirs de maths, physique."),
    _m("qwen2-math:7b", "Qwen2 Math 7B", "special", "Alibaba", "7 milliards", 4.4, 4, 1, "4k",
       "Spécialiste des problèmes de maths, du collège aux concours.",
       ["Très fort en calcul et algèbre"], ["Contexte court", "Anglais"], "Résoudre des problèmes de maths."),
    _m("sqlcoder:7b", "SQLCoder 7B", "special", "Defog", "7 milliards", 4.1, 3, 1, "16k",
       "Transforme une question en requête SQL pour interroger une base de données.",
       ["Écrit des requêtes SQL"], ["Ne sert qu'au SQL"], "Interroger une base de données."),
    _m("medgemma:4b", "MedGemma 4B", "special", "Google", "4 milliards", 3.3, 3, 2, "128k",
       "Gemma 3 entraîné sur des textes et images médicales. Ne remplace pas un médecin.",
       ["Vocabulaire médical", "Lit des images médicales"], ["Ne remplace pas un avis médical"],
       "Comprendre un compte rendu médical."),
    _m("nuextract:3.8b", "NuExtract 3.8B", "special", "NuMind", "3,8 milliards", 2.2, 3, 1, "4k",
       "Extrait des informations d'un texte vers un format structuré (JSON) : noms, dates, montants…",
       ["Extraction précise", "Léger"], ["Ne discute pas"], "Remplir un tableau à partir de documents."),
    _m("reader-lm:1.5b", "Reader-LM 1.5B", "special", "Jina AI", "1,5 milliard", 0.94, 2, 1, "256k",
       "Convertit une page web (HTML) en texte propre (Markdown).",
       ["Très léger", "Énorme contexte"], ["Ne fait que la conversion"], "Nettoyer des pages web."),
]


# Variantes supplémentaires vérifiées dans le catalogue Ollama ; consultables, sans modifier
# les recommandations automatiques établies pour le matériel de l'utilisateur.
EXTRA_MODELS = [
    _m("gemma4:e2b", "Gemma 4 e2b", "chat", "Google", "e2b", 7.2, 4, 3, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7.2 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("gemma4:12b", "Gemma 4 12b", "chat", "Google", "12b", 7.6, 4, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7.6 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("gemma4:26b", "Gemma 4 26b", "chat", "Google", "26b", 19, 5, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 19 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("gemma4:31b", "Gemma 4 31b", "chat", "Google", "31b", 20, 5, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 20 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2.5:1.5b", "Qwen 2.5 1.5b", "light", "Alibaba", "1.5b", 0.986, 2, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.986 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2.5:3b", "Qwen 2.5 3b", "light", "Alibaba", "3b", 1.9, 2, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.9 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2.5:14b", "Qwen 2.5 14b", "chat", "Alibaba", "14b", 9, 4, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 9 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("qwen2.5:32b", "Qwen 2.5 32b", "chat", "Alibaba", "32b", 20, 5, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 20 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2.5:72b", "Qwen 2.5 72b", "chat", "Alibaba", "72b", 47, 5, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 47 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("codellama:13b", "Code Llama 13b", "code", "Meta", "13b", 7.4, 4, 2, "16k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 7.4 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("codellama:34b", "Code Llama 34b", "code", "Meta", "34b", 19, 5, 2, "16k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 19 Go.", ["Aide à la programmation"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("codellama:70b", "Code Llama 70b", "code", "Meta", "70b", 39, 5, 2, "2k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 39 Go.", ["Aide à la programmation"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("granite4:1b", "granite4 1b", "chat", "IBM", "1b", 3.3, 3, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 3.3 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("granite4:3b", "granite4 3b", "chat", "IBM", "3b", 2.1, 3, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 2.1 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3-vl:2b", "Qwen 3 VL 2b", "vision", "Alibaba", "2b", 1.9, 2, 3, "256k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 1.9 Go.", ["Analyse d'images"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3-vl:30b", "Qwen 3 VL 30b", "vision", "Alibaba", "30b", 20, 5, 3, "256k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 20 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen3-vl:32b", "Qwen 3 VL 32b", "vision", "Alibaba", "32b", 21, 5, 3, "256k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 21 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("llava:13b", "llava 13b", "vision", "LLaVA", "13b", 8, 4, 2, "4k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 8 Go.", ["Analyse d'images"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("llava:34b", "llava 34b", "vision", "LLaVA", "34b", 20, 5, 2, "4k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 20 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("stablelm2:12b", "stablelm2 12b", "chat", "Stability AI", "12b", 7, 4, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("exaone3.5:32b", "exaone3.5 32b", "chat", "LG AI Research", "32b", 19, 5, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 19 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen3.5:0.8b", "Qwen 3.5 0.8b", "light", "Alibaba", "0.8b", 1, 2, 3, "256k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3.5:2b", "Qwen 3.5 2b", "chat", "Alibaba", "2b", 2.7, 3, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 2.7 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3.5:4b", "Qwen 3.5 4b", "chat", "Alibaba", "4b", 3.4, 3, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 3.4 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3.5:27b", "Qwen 3.5 27b", "chat", "Alibaba", "27b", 17, 5, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 17 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen3.5:35b", "Qwen 3.5 35b", "chat", "Alibaba", "35b", 24, 5, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 24 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("gemma2:2b", "Gemma 2 2b", "light", "Google", "2b", 1.6, 2, 3, "8k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.6 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("gemma2:27b", "Gemma 2 27b", "chat", "Google", "27b", 16, 5, 3, "8k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 16 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("starcoder2:15b", "starcoder2 15b", "code", "BigCode", "15b", 9.1, 4, 2, "16k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 9.1 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("deepseek-r1:7b", "DeepSeek R1 7b", "reasoning", "DeepSeek", "7b", 4.7, 3, 2, "128k", "Modèle orienté raisonnement pour les questions complexes et la logique. Fichier Ollama d'environ 4.7 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("deepseek-r1:70b", "DeepSeek R1 70b", "reasoning", "DeepSeek", "70b", 43, 5, 2, "128k", "Modèle orienté raisonnement pour les questions complexes et la logique. Fichier Ollama d'environ 43 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("gemma3:270m", "Gemma 3 270m", "light", "Google", "270m", 0.292, 2, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.292 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("llama3.1:70b", "Llama 3.1 70b", "chat", "Meta", "70b", 43, 5, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 43 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2.5vl:3b", "Qwen 2.5 VL 3b", "vision", "Alibaba", "3b", 3.2, 3, 3, "125k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 3.2 Go.", ["Analyse d'images"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2.5vl:32b", "Qwen 2.5 VL 32b", "vision", "Alibaba", "32b", 21, 5, 3, "125k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 21 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2.5vl:72b", "Qwen 2.5 VL 72b", "vision", "Alibaba", "72b", 49, 5, 3, "125k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 49 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("granite3.3:2b", "granite3.3 2b", "light", "IBM", "2b", 1.5, 2, 2, "128k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.5 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("translategemma:27b", "TranslateGemma 27b", "lang", "Google", "27b", 17, 5, 3, "128k", "Modèle destiné aux tâches de traduction et aux langues. Fichier Ollama d'environ 17 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("llama3:70b", "Llama 3 70b", "chat", "Meta", "70b", 40, 5, 2, "8k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 40 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("llama3.2-vision:90b", "Llama 3.2 Vision 90b", "vision", "Meta", "90b", 55, 5, 2, "128k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 55 Go.", ["Analyse d'images"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("smollm:135m", "SmolLM 135m", "light", "Hugging Face", "135m", 0.092, 1, 2, "2k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.092 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("smollm:360m", "SmolLM 360m", "light", "Hugging Face", "360m", 0.229, 1, 2, "2k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.229 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("llama2:13b", "Llama 2 13b", "chat", "Meta", "13b", 7.4, 3, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7.4 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("llama2:70b", "Llama 2 70b", "chat", "Meta", "70b", 39, 4, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 39 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("openhermes:v2", "OpenHermes v2", "chat", "Nous Research", "v2", 4.1, 2, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 4.1 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("openhermes:7b-mistral-v2-fp16", "OpenHermes 7b-mistral-v2-fp16", "chat", "Nous Research", "7b-mistral-v2-fp16", 14, 4, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 14 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "PC doté de 16 à 32 Go de RAM"),
    _m("openhermes:7b-mistral-v2.5-fp16", "OpenHermes 7b-mistral-v2.5-fp16", "chat", "Nous Research", "7b-mistral-v2.5-fp16", 14, 4, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 14 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "PC doté de 16 à 32 Go de RAM"),
    _m("openhermes:7b-v2", "OpenHermes 7b-v2", "chat", "Nous Research", "7b-v2", 4.1, 2, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 4.1 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("openhermes:7b-v2.5", "OpenHermes 7b-v2.5", "chat", "Nous Research", "7b-v2.5", 4.1, 2, 2, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 4.1 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("medgemma:27b", "MedGemma 27b", "special", "Google", "27b", 17, 5, 3, "128k", "Modèle spécialisé ; vérifiez son domaine d'utilisation avant de le télécharger. Fichier Ollama d'environ 17 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2:0.5b", "Qwen 2 0.5b", "light", "Alibaba", "0.5b", 0.352, 2, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.352 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2:1.5b", "Qwen 2 1.5b", "light", "Alibaba", "1.5b", 0.935, 2, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.935 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2:72b", "Qwen 2 72b", "chat", "Alibaba", "72b", 41, 5, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 41 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("deepseek-coder:6.7b", "DeepSeek Coder 6.7b", "code", "DeepSeek", "6.7b", 3.8, 3, 2, "16k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 3.8 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("deepseek-coder:33b", "DeepSeek Coder 33b", "code", "DeepSeek", "33b", 19, 5, 2, "16k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 19 Go.", ["Aide à la programmation"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("orca-mini:7b", "orca-mini 7b", "chat", "OpenOrca", "7b", 3.8, 3, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 3.8 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("orca-mini:13b", "orca-mini 13b", "chat", "OpenOrca", "13b", 7.4, 4, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7.4 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("orca-mini:70b", "orca-mini 70b", "chat", "OpenOrca", "70b", 39, 5, 2, "4k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 39 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("granite3.1-moe:1b", "granite3.1-moe 1b", "light", "IBM", "1b", 1.4, 2, 2, "128k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.4 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("falcon3:1b", "Falcon 3 1b", "light", "TII", "1b", 1.8, 2, 2, "8k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.8 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("falcon3:3b", "Falcon 3 3b", "light", "TII", "3b", 2, 3, 2, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 2 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("dolphin-llama3:70b", "Dolphin Llama 3 70B", "uncensored", "Eric Hartford", "70b", 40, 4, 2, "8k", "Variante Dolphin de Llama 3 présentée comme moins filtrée. Environ 40 Go.", ["Modèle de grande taille"], ["Mémoire très importante ; contexte 8k"], "Station de travail avec beaucoup de mémoire"),
    _m("cogito:32b", "cogito 32b", "chat", "Deep Cogito", "32b", 20, 5, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 20 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("cogito:70b", "cogito 70b", "chat", "Deep Cogito", "70b", 43, 5, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 43 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("gemma:2b", "gemma 2b", "light", "Communauté", "2b", 1.7, 2, 3, "8k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.7 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen:0.5b", "Qwen 1.5 0.5b", "light", "Alibaba", "0.5b", 0.395, 1, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.395 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen:1.8b", "Qwen 1.5 1.8b", "light", "Alibaba", "1.8b", 1.1, 1, 3, "32k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.1 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen:7b", "Qwen 1.5 7b", "chat", "Alibaba", "7b", 4.5, 2, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 4.5 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen:14b", "Qwen 1.5 14b", "chat", "Alibaba", "14b", 8.2, 3, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 8.2 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("qwen:32b", "Qwen 1.5 32b", "chat", "Alibaba", "32b", 18, 4, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 18 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen:72b", "Qwen 1.5 72b", "chat", "Alibaba", "72b", 41, 4, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 41 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen:110b", "Qwen 1.5 110b", "chat", "Alibaba", "110b", 63, 4, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 63 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("phi3:14b", "phi3 14b", "chat", "Microsoft", "14b", 7.9, 4, 2, "128k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 7.9 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("codegemma:2b", "codegemma 2b", "code", "Google", "2b", 1.6, 2, 3, "8k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 1.6 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("granite3.2:2b", "granite3.2 2b", "light", "IBM", "2b", 1.5, 2, 2, "128k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 1.5 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3.6:27b", "qwen3.6 27b", "reasoning", "Alibaba", "27b", 18, 5, 3, "256k", "Modèle orienté raisonnement pour les questions complexes et la logique. Fichier Ollama d'environ 18 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen3:0.6b", "Qwen 3 0.6b", "light", "Alibaba", "0.6b", 0.523, 2, 3, "40k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.523 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3:4b", "Qwen 3 4b", "reasoning", "Alibaba", "4b", 2.5, 3, 3, "256k", "Modèle orienté raisonnement pour les questions complexes et la logique. Fichier Ollama d'environ 2.5 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3:30b", "Qwen 3 30b", "reasoning", "Alibaba", "30b", 19, 5, 3, "256k", "Modèle orienté raisonnement pour les questions complexes et la logique. Fichier Ollama d'environ 19 Go.", ["Fonctionne en local"], ["Demande beaucoup de mémoire"], "Station de travail avec beaucoup de mémoire"),
    _m("qwen2.5-coder:0.5b", "Qwen 2.5 Coder 0.5b", "code", "Alibaba", "0.5b", 0.398, 2, 3, "32k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 0.398 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen2.5-coder:3b", "Qwen 2.5 Coder 3b", "code", "Alibaba", "3b", 1.9, 2, 3, "32k", "Modèle local pour écrire ou expliquer du code ; à choisir selon la taille du projet. Fichier Ollama d'environ 1.9 Go.", ["Aide à la programmation"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("gemma3n:e2b", "Gemma 3n e2b", "vision", "Google", "e2b", 5.6, 4, 3, "32k", "Modèle multimodal pour analyser les images dans les interfaces compatibles. Fichier Ollama d'environ 5.6 Go.", ["Analyse d'images"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("smollm2:135m", "SmolLM2 135m", "light", "Hugging Face", "135m", 0.271, 2, 2, "8k", "Variante compacte pour les PC modestes ou les réponses rapides. Fichier Ollama d'environ 0.271 Go.", ["Peu gourmand en mémoire"], ["Qualité et vitesse selon le matériel"], "PC courant"),
    _m("qwen3.5:9b", "Qwen 3.5 9b", "chat", "Alibaba", "9b", 6.6, 4, 3, "256k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 6.6 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC doté de 16 à 32 Go de RAM"),
    _m("qwen2.5:7b", "Qwen 2.5 7b", "chat", "Alibaba", "7b", 4.7, 3, 3, "32k", "Assistant de conversation local pour discuter, rédiger et résumer des textes. Fichier Ollama d'environ 4.7 Go.", ["Fonctionne en local"], ["Qualité et vitesse selon le matériel"], "PC courant"),
]
MODELS += EXTRA_MODELS
EXTRA_IDS = {model["id"] for model in EXTRA_MODELS}
UNCENSORED_MODELS = [
    _m("dolphin-phi:2.7b", "Dolphin Phi 2.7B", "uncensored", "Eric Hartford", "2.7b", 1.6, 2, 1, "2k",
       "Petit modèle Dolphin présenté comme non censuré. Contexte court ; environ 1,6 Go à télécharger.",
       ["Léger pour commencer"], ["Ancien modèle ; réponses et français variables"], "PC modeste"),
    _m("wizard-vicuna-uncensored:7b", "Wizard Vicuna Uncensored 7B", "uncensored", "Eric Hartford", "7b", 3.8, 2, 1, "2k",
       "Variante de Wizard Vicuna entraînée avec moins de réponses moralisatrices. Environ 3,8 Go.",
       ["Taille accessible"], ["Contexte limité à 2k ; ancien modèle"], "PC courant"),
    _m("dolphin-mistral:7b", "Dolphin Mistral 7B", "uncensored", "Eric Hartford", "7b", 4.1, 3, 2, "32k",
       "Version Dolphin de Mistral présentée comme non censurée, adaptée à la discussion et au code. Environ 4,1 Go.",
       ["Polyvalent", "Aide au code"], ["Qualité du français variable"], "PC courant"),
    _m("dolphin-llama3:8b", "Dolphin Llama 3 8B", "uncensored", "Eric Hartford", "8b", 4.7, 3, 2, "8k",
       "Variante Dolphin de Llama 3 décrite comme moins filtrée, pour discuter et programmer. Environ 4,7 Go.",
       ["Discussion et code"], ["Contexte 8k ; réponses variables"], "PC courant"),
    _m("wizard-vicuna-uncensored:13b", "Wizard Vicuna Uncensored 13B", "uncensored", "Eric Hartford", "13b", 7.4, 2, 1, "2k",
       "Variante 13B de Wizard Vicuna Uncensored. Environ 7,4 Go ; contexte limité.",
       ["Plus grand que la version 7B"], ["Ancien modèle ; contexte 2k"], "PC doté de 16 Go de RAM"),
    _m("wizard-vicuna-uncensored:30b", "Wizard Vicuna Uncensored 30B", "uncensored", "Eric Hartford", "30b", 18, 3, 1, "2k",
       "Variante 30B de Wizard Vicuna Uncensored. Environ 18 Go ; exige beaucoup de mémoire.",
       ["Variante plus grande"], ["Contexte 2k ; mémoire importante"], "Station de travail"),
    _m("dolphin-mixtral:8x7b", "Dolphin Mixtral 8x7B", "uncensored", "Eric Hartford", "8x7b", 26, 4, 2, "32k",
       "Variante Mixtral Dolphin présentée comme non censurée, intéressante aussi pour le code. Environ 26 Go.",
       ["Discussion et code"], ["Téléchargement et mémoire importants"], "Station de travail"),
    _m("llama2-uncensored:7b", "Llama 2 Uncensored 7B", "uncensored", "George Sung / Jarrad Hope", "7b", 3.8, 2, 1, "2k",
       "Variante de Llama 2 présentée comme non censurée. Environ 3,8 Go.",
       ["Taille accessible"], ["Ancien modèle ; contexte 2k"], "PC courant"),
    _m("dolphincoder:7b", "DolphinCoder 7B", "uncensored", "Eric Hartford", "7b", 4.2, 3, 1, "16k",
       "Dolphin orienté programmation, basé sur StarCoder2 et présenté comme non censuré. Environ 4,2 Go.",
       ["Spécialisé en code"], ["Peu adapté aux discussions généralistes"], "PC courant"),
    _m("dolphin-llama3:8b-256k", "Dolphin Llama 3 8B (contexte long)", "uncensored", "Eric Hartford", "8b", 4.7, 3, 2, "250k",
       "Variante Dolphin Llama 3 dotée d'une grande fenêtre de contexte. Environ 4,7 Go à télécharger.",
       ["Documents et conversations plus longs"], ["Un grand contexte peut épuiser la mémoire du PC"], "PC doté de 16 à 32 Go de RAM"),
    _m("wizardlm-uncensored:13b", "WizardLM Uncensored 13B", "uncensored", "Eric Hartford", "13b", 7.4, 2, 1, "4k",
       "Version de WizardLM basée sur Llama 2 et présentée comme non censurée. Environ 7,4 Go.",
       ["Autre famille de modèles à essayer"], ["Ancien modèle ; contexte 4k"], "PC doté de 16 Go de RAM"),
    _m("everythinglm:13b", "EverythingLM 13B", "uncensored", "EverythingLM", "13b", 7.4, 2, 1, "16k",
       "Modèle non censuré basé sur Llama 2, avec contexte de 16k. Environ 7,4 Go.",
       ["Contexte 16k"], ["Modèle ancien ; prévoir assez de mémoire"], "PC doté de 16 Go de RAM"),
    _m("dolphincoder:15b", "DolphinCoder 15B", "uncensored", "Eric Hartford", "15b", 9.1, 4, 1, "16k",
       "Version 15B de DolphinCoder pour programmer, basée sur StarCoder2. Environ 9,1 Go.",
       ["Code et projets plus complexes"], ["Mémoire supérieure à la version 7B"], "PC doté de 24 Go de RAM"),
    _m("llama2-uncensored:70b", "Llama 2 Uncensored 70B", "uncensored", "George Sung / Jarrad Hope", "70b", 39, 3, 1, "2k",
       "Grande variante de Llama 2 Uncensored. Environ 39 Go à télécharger.",
       ["Grande taille"], ["Contexte limité à 2k ; mémoire très importante"], "Station de travail"),
    _m("dolphin-mixtral:8x22b", "Dolphin Mixtral 8x22B", "uncensored", "Eric Hartford", "8x22b", 80, 4, 2, "64k",
       "Grande variante Dolphin Mixtral, orientée notamment vers le code. Environ 80 Go à télécharger.",
       ["Contexte 64k"], ["Réservé aux machines dotées de beaucoup de mémoire"], "Station de travail haut de gamme"),
]
MODELS += UNCENSORED_MODELS
CREATIVE_MODELS = [
    _m("qwen2.5:1.5b-instruct", "Qwen 2.5 1.5B · idées rapides", "creative", "Alibaba", "1.5b", 0.986, 2, 3, "32k",
       "Petit modèle pour trouver des idées de personnages et de situations. Environ 1 Go à télécharger.",
       ["Très léger", "Idées rapides"], ["Récits longs moins cohérents"], "PC modeste"),
    _m("qwen2.5:3b-instruct", "Qwen 2.5 3B · personnages", "creative", "Alibaba", "3b", 1.9, 3, 3, "32k",
       "Conçoit des personnages, leurs motivations et de courts dialogues. Environ 1,9 Go.",
       ["Bon point de départ", "Français utilisable"], ["Moins de détails qu'un grand modèle"], "PC courant"),
    _m("qwen3:4b-instruct", "Qwen 3 4B · dialogues", "creative", "Alibaba", "4b", 2.5, 3, 3, "256k",
       "Variante instruct pour imaginer des scènes et poursuivre un dialogue. Environ 2,5 Go.",
       ["Création et jeu de rôle", "Grand contexte annoncé"], ["Un contexte long demande plus de RAM"], "PC courant"),
    _m("qwen2.5:7b-instruct", "Qwen 2.5 7B · quêtes", "creative", "Alibaba", "7b", 4.7, 3, 3, "32k",
       "Aide à concevoir des quêtes, rebondissements et descriptions de lieux. Environ 4,7 Go.",
       ["Bon équilibre entre taille et détails"], ["Prévoir de la mémoire pour le contexte"], "PC doté de 16 Go de RAM"),
    _m("llama3.1:8b-instruct-q4_K_M", "Llama 3.1 8B · récits", "creative", "Meta", "8b", 4.9, 3, 2, "128k",
       "Modèle généraliste utile pour bâtir un univers et réécrire des scènes. Environ 4,9 Go.",
       ["Narration et réécriture"], ["Résultats en français à relire"], "PC doté de 16 Go de RAM"),
    _m("qwen2.5:14b-instruct", "Qwen 2.5 14B · scénarios", "creative", "Alibaba", "14b", 9.0, 4, 3, "32k",
       "Pour étoffer les dialogues, la trame d'une quête ou le passé des personnages. Environ 9 Go.",
       ["Davantage de détails", "Bon pour écrire en français"], ["Plus lent et plus gourmand"], "PC doté de 24 Go de RAM"),
    _m("qwen3:30b-a3b-instruct-2507-q4_K_M", "Qwen 3 30B · univers détaillés", "creative", "Alibaba", "30b", 19, 4, 3, "256k",
       "Grand modèle instruct pour développer des intrigues, des factions et des histoires suivies. Environ 19 Go.",
       ["Univers et scénarios complexes"], ["Exige beaucoup de mémoire, surtout avec un long contexte"], "Station de travail"),
]
MODELS += CREATIVE_MODELS
# Modèles à usage unique : visibles dans le catalogue mais jamais « conseillés »
NICHE_IDS = {"glm-ocr:latest", "starcoder2:7b", "nuextract:3.8b", "reader-lm:1.5b",
             "sqlcoder:7b", "sailor2:8b", "medgemma:4b"}
# Catégories présentes dans le tableau de recommandations
RECO_CATEGORIES = [c for c in CATEGORIES if c not in ("special", "uncensored", "creative")]

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

    for cat in RECO_CATEGORIES:
        candidates = []
        for m in models_in(cat):
            if m["id"] in NICHE_IDS or m["id"] in EXTRA_IDS:
                continue
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
