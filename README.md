# IA Manager

Application de bureau Python/PyQt6, principalement destinée à Windows, pour utiliser et gérer des IA locales et des connexions API.

## Fonctions

- Chat en continu, commandes rapides, pièces jointes et recherche web facultative.
- Ollama, LM Studio et serveurs compatibles OpenAI ; connexions OpenAI et Anthropic.
- Catalogue, recherche Hugging Face/GGUF, téléchargement via Ollama.
- Projets, consignes, discussions sauvegardées, recherche et exports PDF/Word/Markdown.
- Comparateur, tableau de bord, mesures et estimations de vitesse.
- Tâches planifiées pendant que l'application reste ouverte.
- Outils GitHub et commandes Termux pour envoyer les mises à jour.
- Atelier **Obliteratus** : accès web, installation Python séparée et lancement local avec journal.

## Utilisation

Télécharger l'exécutable depuis les [releases](https://github.com/janintibo-art/ia-manager/releases). Installer et lancer Ollama séparément pour ses modèles locaux ; les autres moteurs se configurent dans **Connexions**.

Pour exécuter les sources : Python 3.11+, dépendances de `requirements.txt`, puis `python main.py`. L'application utilise le dossier `~/.ia_manager` pour sa configuration et le dossier de projets choisi dans ses réglages.

## Obliteratus

L'onglet ouvre la version web officielle sans installation locale. Pour utiliser le mode local sur le PC, choisir un Python 3.10+ installé, cliquer sur **Installer / réparer**, puis **Lancer en local**. Attendre l'annonce du serveur dans le journal avant **Ouvrir l'interface locale**.

Les dépendances lourdes sont téléchargées dans `~/.ia_manager/tools/obliteratus/.venv`, séparément de l'EXE. Le lancement est limité à `127.0.0.1`, avec télémétrie désactivée pour le processus local. Une machine adaptée au modèle et un environnement PyTorch compatible restent nécessaires. Android/Termux n'est pas un environnement pris en charge par Obliteratus.

Ce module lance l'outil officiel ; il ne transforme pas directement les modèles Ollama/GGUF et n'importe pas automatiquement les exports. Voir [la documentation officielle](https://github.com/elder-plinius/OBLITERATUS) et [l'analyse v22](ANALYSE_v22.md) pour le détail et les limites de validation.

## Vérification et compilation

GitHub Actions exécute les tests de régression, le test de démarrage hors écran puis PyInstaller, avant de publier l'exécutable. Les tests utilisent un profil temporaire.

L'[analyse v22](ANALYSE_v22.md) décrit les corrections, les problèmes restants et les prochaines améliorations proposées.

## Mise à jour v23

Le Chat propose un aperçu des différences avant d'appliquer du code, une sauvegarde automatique et un bouton pour restaurer la dernière application. L'envoi GitHub est limité aux fichiers de l'aperçu. Les pièces jointes disposent de limites de lecture avant décompression. Voir [le guide v23](MISE_A_JOUR_v23.md) pour les détails et les limites.

## Mise à jour v24

Stop réseau annulable, documents chargés en arrière-plan et nouvel **Espace de travail** : mémoire documentaire par projet, profils, file des générations locales, déchargement Ollama et carnet manuel des essais Obliteratus. Voir [le guide v24](MISE_A_JOUR_v24.md) pour les étapes et les limites.

## Mise à jour v27

Protection du contexte : jauge colorée, avertissement à 75/90 % et blocage préventif des historiques trop longs. Voir [le guide v27](MISE_A_JOUR_v27.md).

## Mise à jour v28

Deux profils spécialisés sont disponibles : **Architecte Code** et **Directeur Artistique Image**. Ils utilisent le modèle choisi et fournissent des consignes détaillées pour vos projets. Voir [le guide v28](MISE_A_JOUR_v28.md).

## Mise à jour v29

Optimisations de performance : caches partagés pour Ollama, réglages relus seulement si nécessaire, index documentaire SQLite en WAL et bouton de vidage des caches IA. Voir [le guide v29](MISE_A_JOUR_v29.md).

## Mise à jour v30

Le **mode hors ligne** bloque les services distants et la recherche web tout en laissant les moteurs locaux disponibles. Un bouton exporte aussi un diagnostic JSON sans clés API, URL, prompts ni conversations. Voir [le guide v30](MISE_A_JOUR_v30.md).

## Mise à jour v31

La configuration peut être exportée puis restaurée depuis **Connexions**. La sauvegarde exclut les clés API et la restauration les conserve sur l'appareil lorsqu'elles existent déjà. Voir [le guide v31](MISE_A_JOUR_v31.md).

## Mise à jour v32

La recherche propose désormais **GitHub (GGUF)**, avec lecture des releases et installation directe dans Ollama. Hugging Face, Ollama et l'import de fichiers GGUF locaux restent disponibles. Voir [le guide v32](MISE_A_JOUR_v32.md).

## Mise à jour v33

Les téléchargements GitHub affichent leur progression, peuvent être annulés et reprennent après interruption. Les fichiers partiels sont contrôlés par SHA-256 quand GitHub fournit cette information. Voir [le guide v33](MISE_A_JOUR_v33.md).

## Mise à jour v34

Un historique local des modèles GitHub installés indique le nombre de fichiers et l'espace occupé. Le nettoyage retire les téléchargements temporaires ou devenus inutiles sans supprimer les modèles Ollama. Voir [le guide v34](MISE_A_JOUR_v34.md).

## Mise à jour v35

La recherche GitHub accepte un jeton facultatif pour éviter les limites de l'API. Le jeton reste masqué et n'est pas exporté dans les diagnostics ou sauvegardes. Voir [le guide v35](MISE_A_JOUR_v35.md).

## Mise à jour v36

La recherche multi-sources inclut maintenant **ModelScope**. Les formats non compatibles avec Ollama sont identifiés avant toute installation ; les fichiers GGUF restent installables automatiquement. Voir [le guide v36](MISE_A_JOUR_v36.md).

## Mise à jour v37

La recherche inclut **Civitai** pour les modèles image, LoRA, VAE et embeddings. Les formats image sont clairement séparés des modèles GGUF installables dans Ollama. Voir [le guide v37](MISE_A_JOUR_v37.md).

## Mise à jour v38

Les fichiers image disponibles sur Civitai peuvent être téléchargés avec progression, annulation et reprise dans un cache séparé d'Ollama. Voir [le guide v38](MISE_A_JOUR_v38.md).

## Mise à jour v39

La recherche et les téléchargements Civitai acceptent un jeton facultatif pour les limites API et les fichiers protégés. Le jeton reste masqué et exclu des sauvegardes et diagnostics. Voir [le guide v39](MISE_A_JOUR_v39.md).

## Mise à jour v40

Le cache des modèles GGUF et des fichiers image Civitai est maintenant suivi et nettoyé ensemble, avec affichage de l'espace occupé et des téléchargements interrompus. Voir [le guide v40](MISE_A_JOUR_v40.md).

## Mise à jour v41

Les résultats de recherche peuvent être ajoutés aux favoris, quelle que soit leur source (Hugging Face, GitHub, ModelScope ou Civitai). Voir [le guide v41](MISE_A_JOUR_v41.md).

## Mise à jour v42

Un filtre **Favoris uniquement** permet d'afficher rapidement les modèles enregistrés, en respectant leur source. Voir [le guide v42](MISE_A_JOUR_v42.md).

## Mise à jour v43

Les favoris peuvent être exportés et importés en JSON, sans secrets. Ils sont aussi inclus dans la sauvegarde générale. Voir [le guide v43](MISE_A_JOUR_v43.md).

## Mise à jour v44

Les fiches détaillées des modèles sont conservées 60 secondes pour accélérer la navigation et limiter les requêtes réseau. Le vidage des caches IA force une actualisation complète. Voir [le guide v44](MISE_A_JOUR_v44.md).

## Mise à jour v45

Une fiche Hugging Face, GitHub, ModelScope ou Civitai peut être exportée en JSON, sans README volumineux ni secrets. Voir [le guide v45](MISE_A_JOUR_v45.md).

## Mise à jour v46

Les résultats de recherche sont réutilisés pendant 120 secondes et restent consultables en mode hors ligne lorsqu'ils sont déjà en cache. Voir [le guide v46](MISE_A_JOUR_v46.md).

## Mise à jour v47

Les métadonnées des 100 dernières recherches sont conservées sur disque pour rester disponibles hors ligne après redémarrage, sans enregistrer de contenu sensible. Voir [le guide v47](MISE_A_JOUR_v47.md).

## Mise à jour v48

La recherche ModelScope accepte un jeton facultatif pour les dépôts privés et les limites API. Le jeton est masqué et exclu des exports. Voir [le guide v48](MISE_A_JOUR_v48.md).
