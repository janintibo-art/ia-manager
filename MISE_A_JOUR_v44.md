# IA Manager v44 — cache des fiches modèles

Les fiches détaillées des modèles sont maintenant mises en cache temporairement.

## Performance

Quand vous revenez sur un dépôt Hugging Face, GitHub, ModelScope ou Civitai déjà consulté, IA Manager réutilise sa fiche pendant 60 secondes au lieu de refaire les appels réseau. Cela accélère la navigation et réduit les limites API.

## Actualisation forcée

**Espace de travail → Mémoire GPU / file → Rafraîchir les caches IA** vide aussi le cache des fiches. Le prochain affichage relira les sources.

## Vérification

La compilation syntaxique et les 39 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
