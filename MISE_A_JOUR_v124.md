# IA Manager v124 — Arrêt réel et file des créations

Cette mise à jour poursuit les corrections du grand check-up.

## Changements

- bouton Arrêter actif pour les créations image, audio et 3D du Chat ;
- arrêt réel des sous-processus AudioCraft, TripoSR, Hunyuan3D et Blender, y compris leurs processus enfants ;
- interruption transmise à ComfyUI pour arrêter une image en cours ;
- délai maximal surveillé sans laisser le moteur tourner en arrière-plan ;
- file locale commune entre chat texte, téléphone, entraînement, créations et aperçu Blender ;
- une création en attente peut être annulée avant son démarrage ;
- fermeture de l’application : arrêt et attente des travailleurs créatifs ;
- le bouton Arrêter du Chat reste correctement relié après l’installation des extensions v119 à v121.

## Validation

- 197 tests pytest réussis ;
- tests d’annulation et de dépassement de délai réussis ;
- test de démarrage complet réussi sur 21 pages.
