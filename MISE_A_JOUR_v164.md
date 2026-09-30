# IA Manager v164 — Assistant local IA Manager

Nouvel onglet `🤖 Assistant IA Manager`.

Deux modes :

## Diagnostic direct
Fonctionne même sans modèle IA.
Répond à partir de l'état réellement détecté :
- ComfyUI installé / Python / port 8188 ;
- Ollama / port 11434 / modèles disponibles ;
- CPU / GPU / VRAM / RAM ;
- chemins de stockage ;
- espace disque ;
- historique récent ;
- erreurs et avertissements récents.

## Réponse enrichie Ollama
- sélection d'un modèle Ollama déjà installé ;
- l'état IA Manager est fourni au modèle comme contexte ;
- consigne explicite de ne pas inventer des actions exécutées ;
- si une information n'est pas dans le contexte, le modèle doit l'indiquer comme non vérifiée.

Raccourcis inclus :
- Pourquoi ça ne marche pas ?
- État de ComfyUI
- État d'Ollama
- Quel modèle choisir ?
- Où sont mes fichiers ?
- Espace disque

L'assistant peut proposer et ouvrir l'écran pertinent :
Centre de santé, Outils locaux, Bibliothèque IA, Stockage ou Historique.

Les questions à l'assistant sont inscrites dans l'Historique universel.
