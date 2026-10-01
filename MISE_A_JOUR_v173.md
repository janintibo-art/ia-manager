# IA Manager v173 — installation universelle

Objectif : poursuivre le chantier « tout installer depuis l’application » sans casser les installateurs déjà présents.

## Changements

- Pinokio n’est plus traité comme une installation manuelle.
- Installation directe de Pinokio via WinGet avec l’identifiant `pinokiocomputer.pinokio`.
- Détection locale de Pinokio même lorsqu’il n’est pas lancé.
- Nouveau bloc **Installation universelle** dans le Centre d’installation.
- Nouveau bouton **Tout préparer automatiquement**.
- Installation en chaîne des composants manquants dans l’ordre des dépendances :
  1. Git
  2. GitHub CLI
  3. Node.js LTS
  4. pterm
  5. Python 3.11
  6. Ollama
  7. Blender
  8. Pinokio
- Les composants déjà présents sont automatiquement ignorés.
- En cas d’échec ou de coupure, il suffit de relancer : IA Manager reprend uniquement ce qui manque.
- Barre d’état globale basée sur les composants réellement détectés.
- ComfyUI reste géré par l’installateur interne **Outils locaux**, déjà présent dans IA Manager.

## Continuité avec v168 à v172

La v173 conserve :
- téléchargement direct des modèles SDXL/Animagine ;
- packs FLUX/Wan/LTX pour ComfyUI ;
- poids MusicGen/AudioGen/TripoSR/Hunyuan3D ;
- reprise des téléchargements ;
- centre d’installation existant.

## Suite conseillée

La prochaine étape sera de faire le même audit « 1 clic » pour chaque fiche de modèle :
Chat, Image, Son, Vidéo, 3D et Entraînement/Fusion.
