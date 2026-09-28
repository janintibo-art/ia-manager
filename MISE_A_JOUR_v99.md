# IA Manager v99 — Gestionnaire des outils créatifs locaux

Mise à jour différentielle après la v98. Le ZIP contient le gestionnaire, pas les moteurs ni les poids de plusieurs Go.

## Outils proposés

| Moteur | Usage | Python de départ |
| --- | --- | --- |
| ComfyUI | Images, workflows FLUX/Wan/LTX | 3.10 ou 3.11 |
| AudioCraft | MusicGen Small, Melody et AudioGen | 3.9 |
| TripoSR | Image vers maillage 3D | 3.10 ou 3.11 |
| Hunyuan3D 2 | Forme et texture 3D | 3.10 ou 3.11 |

Nouvel onglet « Outils locaux », accessible aussi depuis Images et Audio/Vidéo/3D. Il permet de choisir le dossier avec Parcourir, sélectionner Python, installer/reprendre les recettes, diagnostiquer, démarrer et arrêter un moteur. Un seul processus d’installation ou moteur est piloté à la fois par cet onglet.

## Ce qui est automatisé

- Téléchargement du code depuis le dépôt officiel, en enregistrant le SHA dans le journal.
- Environnement Python séparé dans chaque sous-dossier de moteur.
- Installation de PyTorch CPU ou NVIDIA, des dépendances déclarées par le moteur et de FFmpeg dans cet environnement.
- Tentative de compilation des composants 3D nécessaires ; les erreurs restent visibles.
- Contrôle pip des dépendances et diagnostic des imports de base.
- Journal dans le dossier du moteur, conservation des installations incomplètes et reprise sans supprimer les fichiers.
- Lancement sur 127.0.0.1, sans partage Gradio ; désactivation des nœuds API ComfyUI.
- Variables de fonctionnement hors ligne des caches Hugging Face/Transformers au lancement, si la case est cochée.
- Renseignement des adresses locales dans les écrans Images et Audio/Vidéo/3D au démarrage du processus. Ce signal ne garantit pas que le serveur est déjà prêt : attendre son adresse dans le journal.

Une interface locale AudioCraft est fournie : choix MusicGen Small, Melody ou AudioGen, description, extrait de 1 à 20 secondes, référence audio facultative pour Melody et résultat WAV conservé dans le sous-dossier resultats.

## Ce qui reste nécessaire sur le PC

Python et Git doivent être installés ; les boutons ouvrent leurs installateurs officiels. Utiliser Parcourir pour sélectionner le vrai python.exe, pas IA Manager.exe. Après installation de Git, redémarrer IA Manager pour actualiser le PATH.

Pour les extensions 3D et certaines dépendances AudioCraft, installer les outils C++ Windows, éventuellement le CUDA Toolkit correspondant à PyTorch. Les boutons ouvrent les pages officielles ; le gestionnaire n’installe pas les pilotes système, Visual Studio ou CUDA à votre place. Le binaire FFmpeg privé ne remplace pas les bibliothèques de développement FFmpeg si une dépendance exige une compilation particulière.

Le profil NVIDIA moderne utilise l’index PyTorch CUDA 12.8 ; AudioCraft conserve PyTorch 2.1 / CUDA 11.8 selon sa pile historique. Cette pile ne convient pas à tous les GPU récents. Les recettes visent CPU/NVIDIA ; AMD, Intel et Apple nécessitent l’installation officielle adaptée. Le mode CPU est lent et désactive les textures Hunyuan au lancement, mais la recette Hunyuan tente toujours de compiler les modules de texture : si les prérequis manquent, l’installation peut échouer.

Les recettes suivent les dépôts officiels courants ; une modification de leurs dépendances peut provoquer un conflit. Un échec ne signifie pas que l’environnement est prêt. Le gestionnaire ne supprime pas une installation existante pour résoudre automatiquement ce conflit. Un dossier non géré ou un clonage incomplet n’est pas écrasé : choisir un autre dossier parent si nécessaire.

## Première utilisation

1. Ouvrir Outils locaux et choisir un moteur.
2. Choisir le dossier parent où ranger les moteurs, puis le Python demandé par sa fiche.
3. Choisir CPU ou NVIDIA et cliquer sur Installer / reprendre. Internet est nécessaire ; plusieurs Go peuvent être téléchargés.
4. En cas d’erreur, lire la dernière étape du journal et installer le prérequis indiqué avant de reprendre. Une nouvelle tentative réutilise le code déjà cloné, sans mise à jour automatique de celui-ci.
5. Pour préparer les poids, décocher temporairement « Démarrer hors ligne », démarrer puis ouvrir l’interface lorsque le journal affiche son adresse. Choisir/télécharger les modèles requis et effectuer un court essai.
6. Arrêter, recocher le mode hors ligne et redémarrer. Tester avec Internet coupé.

Les poids et workflows doivent toujours être préparés : SDXL/FLUX/Wan/LTX dans ComfyUI ; modèles AudioCraft via leur premier usage ; composants Hunyuan et TripoSR selon leur moteur. Des poids auxiliaires (encodeurs, détourage, etc.) peuvent n’être récupérés qu’à la première utilisation d’une fonction. Les variables hors ligne ne constituent pas un pare-feu pour les programmes tiers.

## Arrêt et conservation

Arrêter met fin au processus lancé par le gestionnaire ; sous Windows, son arbre de sous-processus est également visé. Fermer réellement IA Manager arrête le moteur piloté. Les sources, caches, modèles et résultats restent sur disque. Le dossier journal.log permet de retrouver la sortie des étapes précédentes.

## Validation

5 tests unitaires sur les recettes : chemins avec espaces/Windows, séparation des environnements, protection des dossiers non gérés, reprise, profils matériels, adresses locales et environnement hors ligne. Test de navigation réussi avec 19 onglets. Tests Qt hors écran avec processus Python simulés : succession des étapes, succès, arrêt sur erreur, annulation et libération du verrou. Interface inspectée visuellement ; syntaxe des modules et du script AudioCraft vérifiée.

Les installations réelles PyTorch/AudioCraft/ComfyUI/3D, la compilation des extensions CUDA et la génération sur GPU n’ont pas été exécutées ici. La compilation Windows complète reste à confirmer dans GitHub Actions.

## Références officielles

- https://github.com/comfyanonymous/ComfyUI
- https://github.com/facebookresearch/audiocraft
- https://github.com/VAST-AI-Research/TripoSR
- https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- https://pytorch.org/get-started/locally/
- https://pytorch.org/get-started/previous-versions/
