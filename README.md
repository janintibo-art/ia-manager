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
