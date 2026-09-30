# IA Manager v168 — installation directe des modèles d’image

Correction du blocage visible dans l’onglet **Création d’images** : le nom du checkpoint était affiché, mais l’utilisateur devait encore télécharger et déplacer manuellement le fichier.

## Changements

- Nouveau bouton **« Télécharger et installer ce modèle »**.
- SDXL Turbo est téléchargé directement depuis Hugging Face dans `ComfyUI/models/checkpoints`.
- Barre de progression avec pourcentage et quantité téléchargée.
- Téléchargement repris depuis le fichier `.part` lorsqu’une coupure survient.
- Détection automatique du ComfyUI installé par IA Manager.
- Si ComfyUI n’est pas géré par IA Manager, sélection du dossier une seule fois avec l’explorateur Windows.
- Actualisation automatique des checkpoints après installation.
- Sélection automatique du checkpoint correspondant au modèle choisi.
- SDXL Turbo conserve ses réglages conseillés : 512×512, 4 étapes, CFG 1.
- Le workflow de génération envoyé par IA Manager reste un workflow SDXL simple et ne dépend pas du workflow éventuellement ouvert dans l’interface ComfyUI.

## Utilisation

1. Ouvrir **Création d’images**.
2. Choisir **SDXL Turbo**.
3. Cliquer **Télécharger et installer ce modèle**.
4. Attendre 100 %.
5. Une fois ComfyUI lancé, cliquer **Connecter / actualiser les modèles** si l’actualisation automatique n’a pas encore répondu.
6. Écrire le prompt et cliquer **Générer une image**.
