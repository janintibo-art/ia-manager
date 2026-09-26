# IA Manager v46 — cache des recherches

Les résultats des recherches multi-sources sont maintenant conservés brièvement en mémoire.

## Performance et hors ligne

Une recherche Hugging Face, GitHub, ModelScope ou Civitai déjà effectuée est réutilisée pendant 120 secondes. Si le **mode hors ligne** est activé pendant ce délai, le résultat en cache reste consultable sans réseau. Une requête jamais faite hors ligne affiche un message clair plutôt que de tenter une connexion.

## Actualisation

**Espace de travail → Rafraîchir les caches IA** vide les résultats et les fiches détaillées. La prochaine recherche relira les sources.

## Vérification

La compilation syntaxique et les 41 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
