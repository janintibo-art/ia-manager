# v54 — Mémoire du chat et archives sur disque

À appliquer après la v53.

## Utilisation
Dans Chat, « Réduire l’historique » sauvegarde d’abord tous les messages actuellement présents, puis garde un mémo local et les six derniers messages (davantage si nécessaire pour ne pas séparer une demande de sa réponse). Le mémo reprend des extraits de l’objectif initial, des échanges récents retirés et du mémo précédent. Ce n’est pas un résumé produit par une IA et il peut omettre des détails.

« Ouvrir les archives » ouvre le dossier dans l’explorateur de fichiers :
- Discussion de projet : `archives_chat` dans le dossier du projet.
- Discussion libre : `.ia_manager/archives_chat` dans le dossier utilisateur.

Chaque sauvegarde possède un dossier daté unique contenant `historique.json` (messages exacts avec leurs champs, dont les images encodées déjà présentes) et `historique.md` (texte lisible). Les fichiers joints externes ne sont pas recopiés : seuls les champs déjà présents dans les messages sont archivés. Les archives précédentes sont conservées lors des réductions suivantes ; il n’y a pas de suppression automatique. Les archives ne sont pas relues automatiquement par le modèle. Le mémo persiste avec les discussions sauvegardées du projet ; une discussion libre n’est pas automatiquement restaurée au redémarrage.

L’écriture doit réussir avant toute réduction. En cas d’échec, le chat reste intact. La réduction est bloquée pendant une génération, une recherche ou un chargement de pièce jointe.

## Fichiers
- `src/backend/chat_history.py` : sauvegarde locale JSON/Markdown et préparation du mémo.
- `src/ui/tabs/chat_tab.py` : archivage avant réduction, accès aux archives, messages d’erreur et blocage pendant les opérations en cours.
- `tests/test_chat_history.py` : sauvegarde exacte, réduction répétée, paires demande/réponse, échec d’écriture sans perte.

## Vérifications
Trois tests automatisés réussis ; syntaxe Python vérifiée. Le démarrage complet et l’EXE restent à valider par le workflow GitHub, car les fichiers de base absents de la v52 ne sont pas disponibles ici.
