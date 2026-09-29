# IA Manager v135 — assistant intelligent MergeKit

Ajoute un assistant avant fusion :

- analyse CPU / RAM / GPU / VRAM ;
- espace disque libre exact ;
- taille exacte des checkpoints locaux ;
- estimation de taille pour les modèles distants quand le nombre de paramètres est identifiable ;
- lecture des `config.json` locaux ;
- détection d’incompatibilités de famille, hidden size ou nombre de couches ;
- recommandation Linear ou SLERP selon les informations disponibles ;
- poids et densité proposés ;
- activation CUDA seulement quand le matériel détecté le justifie ;
- estimation de l’espace de travail nécessaire ;
- blocage de l’application automatique des réglages en cas d’incompatibilité locale claire.

Les estimations sont explicitement distinguées des mesures exactes.
