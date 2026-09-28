# IA Manager v115 — Bibliothèque d’animations

Nouvel onglet **Bibliothèque animations**.

## Indexation locale
Ajoutez un ou plusieurs dossiers contenant :
- FBX
- BVH
- BLEND

IA Manager les indexe sans les déplacer.

## Classement automatique
Détection par nom :
- Idle
- Walk
- Run
- Attack
- Jump
- Dance
- Hit
- Death
- Emote
- Other

La catégorie peut être corrigée manuellement et sauvegardée dans un sidecar `.ia.json`.

## Recherche et favoris
- recherche texte ;
- filtre par catégorie ;
- favoris persistants ;
- taille et format affichés.

## Intégration Blender
- envoyer un résultat vers **Rig Mapping & Clips** ;
- prévisualiser directement un `.blend` en MP4 ;
- les FBX/BVH passent d’abord par l’import Blender puis peuvent être retargetés.

Les fichiers d’animation d’origine ne sont jamais modifiés ou déplacés.
