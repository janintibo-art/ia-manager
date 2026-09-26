# IA Manager v35 — recherche GitHub renforcée

La recherche GitHub peut maintenant utiliser un jeton personnel facultatif.

## Pourquoi l'utiliser

Sans authentification, GitHub limite le nombre de recherches par heure. Dans **Connexions → Recherche internet**, le champ **Jeton GitHub** permet d'utiliser la limite associée au compte et d'éviter les erreurs lors de recherches répétées.

Le jeton est enregistré localement, masqué dans l'interface, absent des diagnostics et exclu des sauvegardes de configuration. Il n'est jamais affiché dans les résultats.

## Message de limite

Lorsque GitHub répond avec une limite de requêtes, IA Manager explique la cause et indique où ajouter le jeton, au lieu d'afficher une erreur réseau vague.

## Vérification

La compilation syntaxique et les 28 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
