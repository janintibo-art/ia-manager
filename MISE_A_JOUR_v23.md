# IA Manager — v23 : vérifier et restaurer le code

Base : v22, commit GitHub `810e60346436a07a96f37df2042c1d918ec81d48`. Sa compilation Windows n°22 a été vérifiée : réussie.

## Nouveautés

Dans le Chat, le lien **Appliquer au dépôt** ouvre maintenant un aperçu des différences pour chaque fichier. Aucune écriture n'a lieu avant votre choix. Les fichiers déjà identiques sont ignorés.

Vous pouvez **Appliquer localement** ou **Appliquer et envoyer sur GitHub**. Dans le second cas, le message de commit est demandé avant d'écrire ; annuler à cet endroit ne change aucun fichier. L'ajout Git et le commit sont limités aux fichiers présentés dans l'aperçu. Un autre fichier déjà indexé conserve son état mais n'entre pas dans ce commit. Attention : les fichiers sélectionnés sont envoyés entiers ; leurs modifications locales antérieures font donc partie du commit, comme indiqué dans la fenêtre.

Une sauvegarde des octets d'origine est créée avant l'écriture dans `~/.ia_manager/code_backups/`. Le bouton **Restaurer la dernière application de code** rétablit ces fichiers et supprime ceux qui ont été créés par cette application. Les dossiers vides peuvent rester en place. Le raccourci vers la dernière sauvegarde est conservé après redémarrage ; les sauvegardes plus anciennes restent sur disque.

Si un fichier a été modifié depuis l'aperçu ou depuis l'application, l'opération est refusée plutôt que d'écraser le nouveau travail. Les liens symboliques et chemins internes Git sont refusés. En cas d'échec d'écriture, un retour à l'état précédent est tenté et la sauvegarde est conservée. Une panne du disque peut aussi empêcher ce retour : le message donne alors le chemin de la sauvegarde.

La restauration concerne le dossier local : elle ne réécrit pas les commits et ne pousse rien sur GitHub. Pour envoyer un retour arrière déjà validé localement, utiliser ensuite le workflow Git habituel.

## Pièces jointes

- Taille maximale : 25 Mio par fichier, vérifiée avant sa lecture.
- ZIP : les entrées dépassant 200 000 octets décompressés sont ignorées avant décompression ; lecture de chaque entrée bornée et budget global de texte.
- Word : contenu XML limité à 8 Mio après décompression.
- Texte brut : lecture initiale limitée à 512 000 octets puis limite habituelle de 120 000 caractères.
- PDF : arrêt de l'extraction une fois le budget de texte atteint ; plus de copie préalable du PDF entier dans un tableau d'octets.
- Images chargées par le Chat : refus au-delà de 16 millions de pixels lorsque les dimensions sont disponibles avant décodage.

Ces limites réduisent les pics mémoire. Elles ne transforment pas tous les lecteurs en tâches d'arrière-plan : un PDF complexe ou une page très compressée peut encore être lent à analyser. Le traitement asynchrone et l'arrêt actif d'une connexion de chat silencieuse restent des améliorations à venir.

## Limites de l'aperçu

Fichiers texte UTF-8, maximum 2 Mio par fichier, 10 Mio pour le lot (originaux et nouveaux contenus cumulés). Si le diff dépasse 400 000 caractères, l'aperçu l'indique et désactive l'application : demander un lot plus petit. Une sauvegarde peut contenir du code privé ou des secrets déjà présents dans les fichiers ; elle reste locale.

## Fichiers concernés

- `src/backend/change_review.py` : aperçu, sauvegarde, écritures atomiques, restauration et commandes Git limitées.
- `src/ui/change_review_dialog.py` : fenêtre d'aperçu et choix de l'action.
- `src/ui/tabs/chat_tab.py` : branchement de l'aperçu, bouton de restauration et contrôle des images.
- `src/backend/attachments.py` : limites avant lecture et décompression.
- `tests/test_change_review.py` : sept tests ciblés supplémentaires.
- `README.md` et ce document : mode d'emploi et limites.

## Vérification

Douze tests de régression réussis au total : les cinq de v22 et sept nouveaux tests. Ils couvrent notamment la restauration exacte des fins de ligne, les fichiers modifiés entre-temps, l'échec au milieu d'un lot, les chemins interdits, la décompression sélective des ZIP et un vrai commit dans un dépôt Git temporaire avec des modifications tierces déjà indexées.

Le test de démarrage complet de l'application réussit également. La fenêtre d'aperçu a été rendue et inspectée visuellement. Syntaxe Python et diff vérifiés. Aucun push de test effectué : les tests Git sont locaux.

Ces vérifications ont eu lieu sur Linux avec Python 3.12. La compilation Windows de v23 s'exécutera après votre mise à jour ; la compilation v22 réussie ne vaut pas validation de v23.
