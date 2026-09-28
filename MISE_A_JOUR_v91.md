# IA Manager v91 — Atelier adapté au matériel

Mise à jour cumulative de l'atelier v90/v91, basée sur le dépôt v89 b969d4f.
Peut s'appliquer après v90. Archive différentielle sous le dossier ia_manager/,
compatible avec le script habituel. Aucune publication GitHub effectuée ici.

## Matériel partagé avec l'application

L'atelier reçoit directement le résultat de l'onglet Analyse : CPU, GPU, VRAM,
RAM totale et RAM disponible. Le bouton Actualiser le matériel relance cette
analyse commune. La détection GPU mise en cache est invalidée lors d'une nouvelle
analyse, ainsi que le cache du calculateur d'allocation. Un remplacement de carte
peut donc être pris en compte sans conserver l'ancienne détection en mémoire.

## Profils évolutifs

Profils QLoRA proposés : Qwen2.5 Instruct 1,5B, 3B, 7B et 14B.
Le choix automatique est prudent, selon VRAM NVIDIA mesurée et RAM totale :
- >= 5 Go VRAM et >= 10 Go RAM : 1,5B, contexte 1024.
- >= 8 Go VRAM et >= 14 Go RAM : 3B, contexte 1024.
- >= 15 Go VRAM et >= 28 Go RAM : 7B, contexte 2048.
- >= 30 Go VRAM et >= 60 Go RAM : 14B, contexte 2048.

Ces seuils sont des heuristiques de départ, PAS des garanties ou des minima
universels. Le modèle, les données, les versions des bibliothèques et les autres
applications modifient la consommation réelle. VRAM incertaine / GPU non NVIDIA :
pas de recommandation automatique affirmative. L'entraînement de cet atelier est
actuellement CUDA ; la fusion CPU reste accessible sans NVIDIA.

La première analyse peut appliquer un profil si rien n'a été modifié. Ensuite,
le conseil évolue mais les réglages restent intacts jusqu'au clic sur le bouton.
Possibilité de choisir un autre modèle, un contexte 512/1024/2048/4096,
un rang LoRA 4/8/16/32 et un lot 1/2/4. Ces valeurs sont transmises au runner,
sauvegardées dans job.json et utilisées par Unsloth/TRL.

## Estimations et contrôles réels

Budgets indicatifs RAM, VRAM et disque affichés pour les modèles du catalogue.
Pour les modèles personnalisés, budget affiché comme inconnu. La VRAM n'est
jamais additionnée à la RAM pour calculer la capacité d'entraînement.
La RAM libre de la fiche est celle de la dernière analyse, pas un compteur temps réel.

Avant la tâche, le moteur mesure son propre GPU CUDA 0 et sa VRAM libre,
l'espace libre sur le disque de sortie et, si psutil est installé dans cet
environnement, la RAM disponible. Rapport hardware.json et versions des outils.
Les budgets insuffisants produisent un avertissement, pas une fausse garantie
ni une interdiction basée uniquement sur l'estimation. Moins de 1 Go libre sur
le disque de sortie bloque les travaux train/fusion pour éviter un échec immédiat.
Le cache Hugging Face peut être sur un autre disque : sa place libre doit aussi
être surveillée ; il n'est pas couvert par la mesure du disque de sortie.

Un GPU unique est utilisé pour l'entraînement. Pas d'addition automatique des
VRAM de plusieurs cartes. Si CUDA_VISIBLE_DEVICES a été configuré, le GPU vu par
le moteur peut différer de la première carte détectée par l'analyse Windows.

## Essai court

Le bouton Essai court effectue deux étapes d'optimisation avec les réglages
choisis, sur une copie du jeu d'exemples. Il mesure les pics de mémoire PyTorch
allouée et réservée, et conserve trial.json. Il ne sauvegarde pas de modèle final.
Les téléchargements et le chargement initial peuvent être longs même pour un essai.
Un essai réussi valide ce court calcul ; il ne garantit pas toutes les séquences,
l'évaluation complète ni la fusion/export FP16. Les exemples restent contrôlés
pour éviter la troncature silencieuse. Un jeu représentatif est préférable.

Le diagnostic indique maintenant clairement qu'une absence de CUDA empêche
l'entraînement, mais pas nécessairement une fusion CPU avec MergeKit.

## Interface et prérequis

Pages de réglages défilantes pour les fenêtres plus petites. Guide enrichi.
Environnement externe Unsloth/TRL et MergeKit toujours nécessaire, comme en v90.
Pas de nouvel ajout lourd aux dépendances de l'EXE. Pas d'installation automatique
ni de réentraînement permanent. Chaque tâche garde un dossier distinct.

## Vérifications

80 tests unitaires réussis, dont changements de GPU avec invalidation du cache,
évolution de profils, VRAM/RAM distinctes, conservation des choix utilisateur,
paramètres réellement reçus par le runner et essai sans export.
Le test du runner utilise des moteurs ML simulés (pas de calcul GPU réel).
Construction et ouverture des 16 onglets réussies, avec seule la détection des
interfaces réseau simulée pour contourner une limitation de l'environnement de test.
Vérification visuelle en thème sombre et petite fenêtre.
Entraînement CUDA, performances, export/import et EXE Windows restent à vérifier
sur le matériel cible. Aucun accès direct au PC de l'utilisateur.

Références :
https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements
https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
