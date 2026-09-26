# IA Manager v40 — cache unifié

Le cache des téléchargements est maintenant géré au même endroit pour les modèles de discussion et les modèles image.

## Suivi de l'espace

La ligne d'état de l'onglet Recherche indique le nombre de fichiers, l'espace total occupé et les téléchargements interrompus. Elle inclut `downloads` (GGUF GitHub) et `image_downloads` (Civitai).

## Nettoyage sûr

Le bouton de nettoyage examine les deux dossiers. Il supprime les fichiers `.part` abandonnés et les fichiers non référencés par l'historique, sans supprimer les modèles déjà créés dans Ollama.

## Vérification

La compilation syntaxique et les 35 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
