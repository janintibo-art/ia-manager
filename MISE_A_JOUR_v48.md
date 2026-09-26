# IA Manager v48 — authentification ModelScope

La source ModelScope accepte maintenant un jeton personnel facultatif.

## Accès étendu

Le jeton peut autoriser la consultation de dépôts privés et augmenter les limites de l'API ModelScope. Il est utilisé pour la recherche et les fiches détaillées.

## Protection

Le champ est masqué dans **Connexions**. Le jeton reste local et n'est jamais inclus dans les sauvegardes ou les diagnostics ; ceux-ci indiquent uniquement si un jeton est configuré.

## Vérification

La compilation syntaxique et les 43 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
