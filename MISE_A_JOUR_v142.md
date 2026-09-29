# IA Manager v142 — Heretic intégré

Ajoute un nouvel onglet `🔥 Heretic`.

## Installation
- environnement Python isolé ;
- installation/réparation en un clic ;
- Heretic épinglé au commit `3521f8648a0dccf6e12a92666862632235fac7e6` ;
- diagnostic Torch / CUDA / GPU / VRAM / RAM.

## Traitement
- modèle Hugging Face ou dossier local ;
- profils Rapide / Équilibré / Approfondi / Personnalisé ;
- nombre d’essais Optuna configurable ;
- seed configurable ;
- quantification `bnb_4bit` activable ;
- reprise ou redémarrage d’un checkpoint ;
- export :
  - adaptateur LoRA ;
  - modèle fusionné.

## Intégration IA Manager
- réservation des ressources locales ;
- journal temps réel ;
- arrêt propre ;
- registre local `~/.ia_manager/heretic_versions.json` ;
- sortie sous le stockage de modèles IA Manager dans `Heretic/` ;
- bouton direct vers le pipeline existant `GGUF → Ollama → Chat`
  lorsque la sortie est un modèle fusionné complet.

Heretic automatise une variante d’abliteration directionnelle avec optimisation
des paramètres. Les modèles originaux ne sont pas modifiés.
