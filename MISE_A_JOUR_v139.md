# IA Manager v139 — Model Family Tree

Nouvel onglet `🌳 Famille IA`.

Le graphe de filiation est reconstruit automatiquement à partir de :
- l’historique d’entraînement Unsloth ;
- les adaptateurs LoRA ;
- les modèles complets entraînés ;
- les fusions MergeKit ;
- les MoE et fusions multi-étapes ;
- le registre des versions Obliteratus ;
- les dossiers de sortie locaux.

Fonctions :
- arbre parent → enfant ;
- type de transformation affiché sur chaque lien ;
- recherche / filtre ;
- détails et métadonnées ;
- ouverture du dossier local ;
- ouverture dans Chat quand un nom Ollama est connu ;
- envoi direct d’un nœud vers MergeKit comme modèle A ou B ;
- détection simple des cycles ;
- aucun fichier de modèle n’est modifié.
