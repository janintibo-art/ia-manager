# IA Manager v30 — mode hors ligne et diagnostic

Cette version ajoute deux outils pratiques pour garder le contrôle des données et faciliter le dépannage.

## Mode hors ligne

Dans **Connexions**, la case **Mode hors ligne** bloque les recherches web et les fournisseurs distants (API ou serveur distant). Les services locaux comme Ollama sur `localhost` restent utilisables. Le blocage est appliqué avant toute requête réseau ; il s'applique aussi aux téléchargements de modèles distants.

Le réglage est mémorisé dans `settings.json`. Désactivez-le pour retrouver les connexions web et API.

## Diagnostic sans secrets

Le bouton **Exporter un diagnostic sans secrets** crée un fichier JSON dans le dossier de configuration. Il contient la version, le système, les fournisseurs configurés sous forme résumée et quelques réglages sûrs. Les clés API, les URL, les prompts, les conversations et le contenu des documents ne sont pas exportés. Ce fichier peut être joint à un rapport GitHub sans exposer les identifiants.

## Performance et mémoire

Les caches Ollama, le cache de réglages et l'index documentaire SQLite optimisé de v29 restent actifs. Le bouton de vidage des caches IA permet de forcer une lecture fraîche après un changement externe.

## Vérification

La compilation syntaxique et les 21 tests ciblés passent localement. La construction Windows complète doit être confirmée par GitHub Actions après l'envoi du ZIP.
