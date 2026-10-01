# IA Manager v181 — Audio & Voix avancés

La v181 ajoute une nouvelle page **Audio & Voix avancés** avec des environnements Python isolés par moteur.

## Modèles

- Whisper large-v3
- Kokoro 82M
- XTTS-v2
- Stable Audio Open 1.0

## Installation

Chaque modèle possède :
- son propre environnement Python ;
- installation / réparation des dépendances ;
- préchargement des poids Hugging Face ;
- vérification de l’état ;
- dossier local facilement accessible.

## Dépendances

- Stable Audio Open : Python 3.10, `stable-audio-tools`
- Whisper large-v3 : Python 3.11, Transformers / Torch
- Kokoro : Python 3.11, paquet `kokoro`, `soundfile`, eSpeak NG sous Windows
- XTTS-v2 : Python 3.11, `coqui-tts`

## Stable Audio Open

Stable Audio Open est un cas particulier : le dépôt Hugging Face exige une autorisation d’accès.
IA Manager automatise l’environnement et le téléchargement une fois cet accès accordé, mais l’audit le conserve en **Partiel** tant que cette étape externe existe.

## Audit

Passent en **Automatique** :
- Whisper large-v3
- Kokoro 82M
- XTTS-v2

Stable Audio Open reste **Partiel** pour refléter honnêtement son accès Hugging Face protégé.
