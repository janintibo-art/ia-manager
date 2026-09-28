# IA Manager v113 — Animation & Retargeting

Nouvel onglet **Animation & Retargeting** dans Studio IA local.

## Bibliothèque procédurale intégrée
Pour le rig générique IA Manager :
- Idle
- Marche
- Course
- Attaque
- Saut

Chaque animation crée une nouvelle scène `.blend` et ne remplace pas la source.

## Retargeting
- cible : personnage riggé IA Manager ;
- source : autre scène Blender animée ;
- correspondance simple par noms/alias d'os ;
- contraintes Copy Rotation / Copy Location ;
- baking des frames choisies ;
- sortie `_retarget.blend`.

Le retargeting est volontairement générique : pour des rigs très différents, une future version ajoutera un mapping d'os éditable.

## Export animé
- GLB animé ;
- FBX animé ;
- export des actions/animations Blender.

## Suite naturelle
- mapping d'os visuel ;
- import BVH/FBX/Mixamo ;
- bibliothèque d'animations externes ;
- retargeting par profils de squelette ;
- prévisualisation et découpage de clips.
