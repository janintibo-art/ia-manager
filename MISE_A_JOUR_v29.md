# IA Manager v29 — performance et mémoire

Cette version améliore les accès répétés sans changer le comportement des conversations.

## Caches partagés

La liste des modèles Ollama est désormais partagée entre les onglets pendant 10 secondes. Avant, Chat, Comparateur, Modèles et Tableau de bord pouvaient lancer chacun une requête `/api/tags` lors d'un rafraîchissement rapproché. Les modèles en cours d'utilisation sont conservés 2 secondes pour éviter des appels `/api/ps` répétés. Télécharger ou supprimer un modèle invalide immédiatement le cache concerné.

Les métadonnées Ollama déjà mises en cache gardent leur comportement. Dans **Espace de travail → Mémoire GPU / file**, **Rafraîchir les caches IA** vide la liste des modèles et les métadonnées ; le prochain rafraîchissement relit le serveur.

## Réglages plus rapides et sûrs

`settings.json` est relu seulement lorsque sa date de modification change. Les écritures atomiques et le verrou introduits précédemment restent actifs. Cela réduit le nombre de lectures disque pendant l'ouverture des onglets, sans empêcher une modification externe d'être détectée.

## Index documentaire

La base `memoire.sqlite3` utilise WAL, une synchronisation normale et un cache mémoire SQLite borné. Les recherches et l'indexation peuvent ainsi mieux cohabiter, avec moins d'attente d'écriture. Les documents et textes gardent leurs limites précédentes ; le fichier WAL peut rester à côté de la base pendant une utilisation normale.

## Limites

Les caches sont propres au processus IA Manager et ne synchronisent pas deux instances ouvertes. Le délai de dix secondes peut afficher une liste de modèles légèrement ancienne ; le bouton de rafraîchissement forcé vide ces caches. La mémoire système et les modèles réellement chargés restent mesurés par le tableau de bord.

## Vérification

Les 19 tests ciblés passent, avec compilation syntaxique de tous les modules. La compilation Windows doit être vérifiée par GitHub Actions après l'installation.
