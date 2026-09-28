# IA Manager v101 — Pipelines visuels, favoris et profils projet

Mise à jour différentielle après la v100. Aucun modèle lourd n'est inclus dans l'archive.

## Nouveautés

- Éditeur de pipelines visuel dans le Studio IA : bibliothèque de briques, ajout/retrait, réorganisation par boutons ou glisser-déposer et guide de lancement.
- Sauvegarde de pipelines personnalisés dans les réglages d'IA Manager, avec validation avant rechargement.
- Les 12 pipelines v100 peuvent être chargés comme modèles puis personnalisés sans modifier les originaux.
- Favoris de modèles persistants et filtre « ★ Favoris ».
- 7 profils projet : Jeu 2D, Jeu 3D, Musique, Vidéo, Voix/doublage, Documents/RAG et Développement.
- Un profil peut ajouter ses modèles conseillés aux favoris et préparer automatiquement son pipeline associé.
- L'écran reste non-exécutant : il n'installe, ne télécharge et ne lance rien automatiquement. Le bouton Outils locaux mène au gestionnaire v99 pour les moteurs réellement pilotés.

## Sécurité / stabilité

Les données personnalisées passent par `settings.json` avec les écritures atomiques déjà utilisées par IA Manager. Les pipelines chargés sont filtrés : nom obligatoire, étapes connues uniquement, limite de longueur et doublons de noms supprimés. Les 19 onglets historiques restent à leur indice actuel ; le Studio IA continue d'être branché comme extension séparée.

## Validation

- 5 tests unitaires v101 pour la bibliothèque, la conversion des pipelines v100, la validation des sauvegardes, les profils et les guides.
- Analyse syntaxique Python des fichiers v101.
- Aucun téléchargement de poids ni test GPU n'est nécessaire pour cette mise à jour d'interface.
