# IA Manager v116 — Pipeline personnage complet

Nouvel onglet **Pipeline personnage**.

## Entrées
- BLEND
- GLB / GLTF
- FBX
- OBJ
- STL
- PLY

Une source non-BLEND est d'abord convertie en scène Blender de travail.

## Étapes chaînables
1. import
2. nettoyage
3. low poly
4. UV
5. auto-rig
6. animation procédurale
7. retargeting facultatif
8. LOD
9. collisions
10. export Godot / Unity / Unreal

Chaque étape peut être activée ou désactivée depuis l'interface.

## Reprise
Un fichier `ia_manager_character_pipeline.json` est écrit dans le dossier du pipeline :
- étape courante ;
- dernier fichier produit ;
- historique ;
- options ;
- dernière erreur.

Le bouton **Reprendre un pipeline** recharge ce manifest.

## Sécurité
- aucun fichier source n'est écrasé ;
- chaque étape produit une nouvelle scène ou un nouvel export ;
- arrêt automatique possible après l'étape courante ;
- une erreur stoppe la chaîne et laisse le manifest reprenable ;
- possibilité d'ignorer manuellement une étape problématique.
