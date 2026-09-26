# IA Manager — analyse et livraison v22

Analyse du 26 septembre 2026. Base : commit `e075c5ed46f36366ce870a61d9ba9d0a401e8612`, branche `main`, dernière release observée `v1.0.21`. La compilation GitHub n°21, démarrée à 14:37 UTC, est réussie. Le nom de cette archive suit la numérotation suivante : `ia_manager_v22.zip`. La prochaine release GitHub conserve sa numérotation automatique par numéro d'exécution.

## Bilan

Le projet est une application de bureau Python/PyQt6, principalement destinée à Windows. Termux sert ici à envoyer les mises à jour et suivre la compilation, pas à exécuter l'application. Le code possède déjà une base utile : moteurs Ollama et compatibles OpenAI, fournisseur Anthropic, projets, historiques, pièces jointes, export, comparateur, tâches planifiées, recherche web et mesures de vitesse.

La séparation entre interface et backend est un bon point. Les travailleurs Qt évitent une partie des blocages et le test de démarrage couvre déjà beaucoup de parcours. Une compilation verte ne garantit cependant ni la fiabilité des sauvegardes ni le comportement face à un serveur lent ou à de gros fichiers.

Cette livraison ajoute Obliteratus et corrige plusieurs défauts ciblés. Elle ne prétend pas éliminer tous les problèmes de l'application.

## Défauts corrigés

### 1. Discussions susceptibles de s'écraser — priorité élevée

**Fichier :** `src/backend/project_manager.py`, `save_conversation`.

Avant : l'identifiant d'une nouvelle discussion était constitué de la date et de l'heure à la seconde. Deux créations rapides dans un même projet produisaient le même nom JSON ; la seconde remplaçait la première.

Correction : ajout d'un suffixe UUID aux nouvelles discussions. Une discussion existante conserve son identifiant lors d'une mise à jour. Les anciennes sauvegardes restent lisibles.

Vérification : création de 25 discussions, unicité et nombre des fichiers, puis modification d'une discussion sans en créer une nouvelle.

### 2. File des tâches pouvant rester bloquée — priorité élevée

**Fichier :** `src/ui/main_window.py`, `start_next_task`, `on_task_answer`, `on_task_finished`.

Avant : le signal de réponse pouvait être reçu alors que le QThread était encore actif. Le lancement de la tâche suivante était alors refusé par `isRunning()` ; aucun rappel à la fin effective du thread ne relançait immédiatement la file. Un passage ultérieur pouvait la débloquer, mais pas de manière fiable.

Correction : le passage à la tâche suivante est déclenché par `finished`, après traitement de la réponse. Le travailleur reste réservé jusqu'à sa fin.

Vérification : un faux travailleur envoie sa réponse puis reste actif pendant 120 ms. Deux tâches s'exécutent dans le bon ordre et la file se vide.

### 3. Configuration écrite directement sur le fichier final — priorité élevée

**Fichier :** `src/backend/settings.py`, `set`.

Avant : une interruption pendant l'écriture pouvait laisser un JSON incomplet ; une lecture ultérieure revenait silencieusement aux valeurs par défaut. Deux appels concurrents pouvaient aussi perdre des modifications.

Correction : écriture d'un fichier temporaire dans le même dossier, synchronisation, puis remplacement atomique ; verrou interne autour de la lecture/modification/écriture.

Vérification : 30 mises à jour concurrentes et simulation d'un échec du remplacement. L'ancien fichier reste intact et le temporaire est supprimé.

Limites : ce verrou concerne un seul processus. Deux instances simultanées de l'application restent à traiter. Les opérations qui relisent et reconstruisent une liste complète avant d'appeler `set` ne deviennent pas des transactions par cette seule correction. Les autres JSON du projet n'ont pas tous été convertis à l'écriture atomique.

### 4. Écriture hors du dépôt à travers un lien symbolique — priorité élevée

**Fichier :** `src/backend/code_tools.py`, `write_to_folder`.

Avant : supprimer les segments `..` ne suffisait pas. Un sous-dossier du dépôt pouvait être un lien vers un autre emplacement ; écrire à travers ce lien modifiait alors un fichier extérieur. Les fichiers internes `.git` pouvaient également être ciblés.

Correction : résolution des destinations et contrôle de leur appartenance au dossier choisi ; refus des destinations absolues, des traversées reçues par cette fonction et des composants `.git`. Validation de tout le lot avant de commencer à écrire.

Vérification : chemins interdits, lien symbolique extérieur, absence d'écriture du premier fichier si le second est invalide et écriture normale. Le test des liens est ignoré sur Windows si la création de liens n'est pas autorisée.

Limites : cela n'ajoute pas encore de sauvegarde automatique avant écrasement, ni de transaction pour l'ensemble des fichiers. Un défaut matériel au milieu des écritures peut laisser un lot partiellement appliqué. L'extracteur de blocs conserve son ancien comportement de normalisation des noms.

### 5. Test de démarrage modifiant le profil réel — priorité moyenne

**Fichier :** `tests/smoke_test.py`.

Avant : le test enregistrait des fournisseurs fictifs, changeait les réglages et utilisait le dossier de configuration habituel. Ce défaut touchait surtout son lancement sur une machine personnelle ; le runner GitHub est éphémère.

Correction : profil utilisateur temporaire configuré avant les imports applicatifs. Aucun test demandé sur votre téléphone.

## Ajout d'Obliteratus

**Fichiers :** `src/backend/obliteratus.py`, `src/ui/tabs/obliteratus_tab.py`, branchement dans `src/ui/main_window.py`.

Un nouvel onglet propose :

- accès à la version web officielle et à sa documentation ;
- choix d'un Python installé sur le PC ;
- installation/réparation dans un environnement virtuel séparé ;
- lancement de l'interface officielle locale dans le navigateur ;
- choix du port, journal limité à 2 000 blocs et arrêt du processus lancé ;
- arrêt du processus local à la fermeture effective d'IA Manager.

L'exécutable IA Manager n'embarque ni PyTorch ni les modèles. Le bouton Installer télécharge les dépendances au moment de son utilisation. Le Python choisi sert à créer l'environnement dédié : ses paquets habituels ne sont pas la cible de l'installation.

La source d'Obliteratus est fixée au commit `b847511776a2afa7ed076f676184a4abfef2b162` (métadonnées 0.1.3). Ses dépendances transitives restent soumises aux contraintes définies par ce projet, elles ne constituent pas un environnement totalement verrouillé.

Le lancement local utilise `python -m obliteratus ui`, l'adresse `127.0.0.1` et aucun lien de partage public. `OBLITERATUS_TELEMETRY=0` et `GRADIO_ANALYTICS_ENABLED=False` sont transmis au processus local. Ces réglages ne contrôlent pas le service web externe.

### Utilisation

1. Après compilation, ouvrir l'onglet **Obliteratus**.
2. Pour essayer depuis un navigateur, choisir **Ouvrir la version web**. Les conditions d'accès et ressources dépendent du service externe.
3. Pour un usage local sur le PC, sélectionner Python 3.10 ou plus récent, puis **Installer / réparer**. Le téléchargement peut être volumineux.
4. Cliquer sur **Lancer en local**, attendre que le journal annonce le serveur, puis **Ouvrir l'interface locale**.
5. Si le port est occupé, arrêter, choisir un autre port et relancer. Consulter le journal en cas d'échec d'installation.

Obliteratus travaille sur les poids des modèles compatibles Hugging Face. Ce n'est pas un fournisseur de chat interchangeable avec Ollama. Les fichiers GGUF déjà installés ne sont pas automatiquement modifiés. L'export, une éventuelle conversion GGUF et l'import dans Ollama restent des étapes distinctes. Le bon fonctionnement dépend du modèle, de la RAM/VRAM, de PyTorch et des pilotes ; l'installation générique ne configure pas à elle seule tous les environnements CUDA/ROCm.

Le projet amont indique qu'Android/Termux n'est pas un environnement pris en charge. Il ne faut donc pas lancer cette installation dans Termux pour espérer y faire fonctionner l'atelier local.

Sources consultées :
- https://github.com/elder-plinius/OBLITERATUS/blob/b847511776a2afa7ed076f676184a4abfef2b162/README.md
- https://github.com/elder-plinius/OBLITERATUS/blob/b847511776a2afa7ed076f676184a4abfef2b162/pyproject.toml
- https://github.com/elder-plinius/OBLITERATUS/blob/b847511776a2afa7ed076f676184a4abfef2b162/obliteratus/cli.py

## Problèmes restants et améliorations proposées

Ces éléments sont issus de la lecture du code ; ils ne sont pas annoncés comme corrigés dans cette livraison.

| Priorité | Constat et emplacement | Conséquence | Suite proposée |
|---|---|---|---|
| Élevée | `providers.chat_stream` vérifie l'arrêt seulement lorsqu'une ligne réseau arrive ; délai de lecture jusqu'à 900 s | Stop peut attendre longtemps si le serveur reste silencieux | Annulation active de la connexion et test avec un serveur muet |
| Élevée | `attachments.load_attachment` lit tout le fichier ; `zip_text` décompresse une entrée avant de vérifier sa taille | Pic mémoire, lenteur ou blocage avec un gros fichier/une archive très compressée | Plafonner les tailles avant lecture, lire par blocs et traiter les pièces jointes dans un travailleur |
| Élevée | `project_manager` et `tasks.TaskStore` écrivent encore directement leurs JSON | Historique ou tâches vulnérables à une interruption d'écriture | Étendre l'écriture atomique, conserver une copie précédente et proposer une restauration |
| Élevée | Chat : appliquer au dépôt utilise `git add -A` via `github_tools.pc_steps` | Le commit peut inclure des modifications préexistantes sans rapport avec la réponse | Aperçu du diff, staging limité aux fichiers appliqués, traitement explicite des modifications déjà indexées |
| Moyenne | `AIManager.get_available_models` appelle le réseau de façon synchrone et plusieurs onglets l'utilisent au démarrage | Retards cumulés si Ollama répond lentement | Un cache partagé, un chargement asynchrone unique et une distinction entre « vide » et « hors ligne » |
| Moyenne | Les clés de fournisseurs et de recherche sont conservées dans `settings.json` | Toute personne ayant accès à ce profil peut les lire | Coffre système pour les secrets et export des réglages sans clés |
| Moyenne | `model_search.group_gguf_files` regroupe uniquement par quantification | Deux variantes distinctes Q4 peuvent voir leurs tailles additionnées, faussant le conseil | Regrouper par modèle/variante puis par série de fragments et quantification |
| Moyenne | `web_tools.fetch_page` télécharge toute la réponse avant la troncature | Une très grande page consomme inutilement de la mémoire | Lecture limitée en octets, contrôle des redirections et exclusion des adresses privées pour les résultats publics |
| Moyenne | `system_analyzer.detect_gpu` retient seulement le premier GPU NVIDIA ; `benchmark` emploie des estimations | Recommandations imparfaites sur plusieurs GPU et matériels inconnus | Inventaire par GPU, choix du périphérique et priorité aux mesures réelles |
| Moyenne | Les erreurs métier sont reconnues par le début du texte « Erreur » | Une réponse normale peut être mal classée ; traitement fragile entre fournisseurs | Résultat structuré séparant contenu, erreur, interruption et statistiques |
| Moyenne | Le contexte du chat s'allonge avec l'historique et les pièces jointes | Dépassement du contexte, ralentissement ou coût accru pour les API | Jauge de contexte, sélection des pièces utiles et résumé de conversation conservant les consignes |
| Faible | Beaucoup d'onglets dans une seule barre | Navigation moins pratique sur un petit écran | Menu latéral avec groupes : discuter, modèles, projets et outils |

Les dépendances et leurs vulnérabilités n'ont pas fait l'objet d'un audit spécialisé ; leur ancienneté seule ne permet pas d'affirmer une vulnérabilité. Les accès API réels et les quotas fournisseurs n'ont pas été validés.

### Idées les plus utiles pour la suite

1. **Atelier de code avec retour arrière** : aperçu des fichiers, diff, sauvegarde avant application et restauration en un clic. C'est le meilleur complément au workflow ZIP/GitHub actuel.
2. **Bibliothèque documentaire par projet** : index des documents, recherche locale et citations des passages utilisés, pour éviter d'envoyer toutes les pièces jointes à chaque question.
3. **Profils de travail** : « code », « rédaction », « recherche » et « rapide », réunissant modèle, consignes, contexte et outils.
4. **Gestion de la mémoire GPU partagée** : mettre les générations lourdes en file, proposer de décharger Ollama avant un atelier Obliteratus et afficher la mémoire disponible. Le comparateur simultané peut être coûteux en VRAM.
5. **Suivi des ateliers Obliteratus** : modèle source, version de l'outil, paramètres, dossier exporté et comparaison qualité/vitesse avant-après. À construire une fois le lancement réel validé sur le matériel cible.

Ordre conseillé : fiabiliser l'arrêt et les pièces jointes, ajouter diff/restauration, puis mémoire documentaire et suivi des ateliers.

## Vérifications réalisées et limites

- Test de démarrage existant exécuté avant les changements : réussi.
- Cinq tests de régression exécutés après les changements : réussis (discussions, configuration, fichiers, processus Obliteratus simulés et file des tâches).
- Test de démarrage complet après modifications : réussi, y compris création de la fenêtre avec le nouvel onglet, streaming simulé, comparateur, exports et recherche web simulée.
- Compilation syntaxique de tous les modules Python et contrôle du diff : réussis.
- Les tests de régression sont ajoutés au workflow Windows avant le smoke test et PyInstaller.

Exécution de ces vérifications dans un environnement Linux/Python 3.12 avec les dépendances du projet. La compilation Windows/Python 3.11 du nouveau code n'a pas été lancée ici : elle s'exécutera après votre mise à jour. La réussite de la compilation n°21 concerne la base, pas ce correctif.

Les tests du pont Obliteratus utilisent de petits processus Python : ils couvrent l'enchaînement, l'échec, l'arrêt et l'environnement transmis. Aucun modèle n'a été téléchargé, aucun calcul GPU n'a été exécuté, et l'installation complète des dépendances lourdes n'a pas été validée ici. Un traitement Obliteratus réel reste à valider sur le PC cible.

## Contenu de la livraison

Le ZIP contient uniquement les fichiers nouveaux ou modifiés, sous `ia_manager/` :

- `src/backend/project_manager.py` : identifiants de discussions.
- `src/backend/settings.py` : configuration atomique et verrou interne.
- `src/backend/code_tools.py` : confinement des fichiers appliqués.
- `src/backend/obliteratus.py` : commandes et environnement dédié.
- `src/ui/tabs/obliteratus_tab.py` : nouvel onglet.
- `src/ui/main_window.py` : branchement de l'onglet et correction du planificateur.
- `tests/test_regressions.py` : cinq tests ciblés.
- `tests/smoke_test.py` : isolation du profil de test.
- `.github/workflows/build.yml` : exécution des nouveaux tests avant compilation.
- `README.md` : présentation et guide mis à jour.
- `ANALYSE_v22.md` : ce rapport.

Les modèles, conversations et réglages de votre installation ne sont pas inclus dans l'archive et ne sont pas remplacés par le script de mise à jour.
