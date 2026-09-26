# IA Manager v34 — historique et cache

La recherche conserve maintenant une trace locale des modèles GitHub importés dans Ollama.

## Historique

Après l'import d'un GGUF, le nom, la source, la date et la taille du fichier sont enregistrés dans `~/.ia_manager/models/download_history.json`. L'historique est limité aux 100 dernières entrées et ne contient aucune clé API.

## Nettoyage

Le bouton **Nettoyer le cache** supprime les fichiers `.part` abandonnés et les GGUF téléchargés qui ne sont plus référencés par l'historique. Les fichiers conservés pour une reprise restent intacts, et les modèles déjà créés dans Ollama ne sont pas supprimés.

## Vérification

La compilation syntaxique et les 27 tests ciblés passent localement. GitHub Actions reste nécessaire pour confirmer la compilation Windows et l'interface complète.
