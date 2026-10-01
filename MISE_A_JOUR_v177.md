# IA Manager v177 — Vidéo Wan 2.1 / LTX-Video en parcours unifié

La v177 poursuit le chantier « tout installer depuis l'application » pour la vidéo.

## Modèles concernés

- Wan 2.1 T2V 1.3B
- LTX-Video

## Nouveau panneau Vidéo

Dans **Audio · Vidéo · 3D**, IA Manager affiche maintenant un panneau unique avec :

- état de ComfyUI ;
- état du pack vidéo ;
- bouton d'installation/réparation de ComfyUI ;
- bouton de téléchargement du pack ;
- bouton de démarrage ;
- bouton de vérification ;
- bouton pour ouvrir ComfyUI.

## Réutilisation des systèmes existants

La v177 réutilise :
- le moteur ComfyUI géré par **Outils locaux** ;
- le système v171 de téléchargement multi-fichiers ;
- la reprise des fichiers `.part` ;
- les dossiers automatiques `diffusion_models`, `text_encoders`, `vae` et `checkpoints`.

## Parcours utilisateur

1. Installer ComfyUI.
2. Télécharger le pack Wan/LTX.
3. Démarrer ComfyUI.
4. Vérifier.
5. Ouvrir ComfyUI et charger le workflow vidéo correspondant.

## Suite

La prochaine étape logique est la **v178 3D**, avec TripoSR et Hunyuan3D.
