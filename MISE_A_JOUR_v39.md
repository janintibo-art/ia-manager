# IA Manager v39 — authentification Civitai

La source Civitai accepte maintenant un jeton personnel facultatif.

## Utilité

Le jeton peut augmenter la limite de l'API et autoriser l'accès à certains fichiers nécessitant une authentification. Il est utilisé pour la recherche, les fiches et les téléchargements Civitai.

## Protection

Le champ est masqué dans **Connexions**. Le jeton est conservé localement et n'apparaît ni dans les sauvegardes de configuration, ni dans les diagnostics exportés.

## Vérification

La compilation syntaxique et les 34 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
