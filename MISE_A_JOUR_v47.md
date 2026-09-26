# IA Manager v47 — cache de recherche persistant

Le cache des recherches multi-sources survit maintenant au redémarrage de l'application.

## Fonctionnement

Les métadonnées des 100 dernières requêtes sont enregistrées dans `~/.ia_manager/cache/search_results.json`. En mode hors ligne, IA Manager peut donc réafficher une recherche déjà effectuée lors d'une session précédente.

Le cache ne contient ni conversation, ni clé API, ni jeton, ni contenu de document. Les résultats gardent leur durée de fraîcheur courte et peuvent être supprimés avec **Rafraîchir les caches IA**.

## Vérification

La compilation syntaxique et les 42 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
