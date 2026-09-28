# IA Manager v112 — Blender Game Ready

Nouvel onglet **Game Ready** à côté de Blender Studio.

## Outils
- réduction de polygones avec ratio réglable ;
- génération LOD0 / LOD1 / LOD2 / LOD3 en GLB ;
- UV automatique Smart Project ;
- auto-rig de base avec squelette générique ;
- collisions convexes ou boîtes ;
- préparation du baking et dossier dédié ;
- export GLB pour Godot, Unity ou Unreal.

## Principe
La source `.blend` n'est jamais écrasée :
- `_lowpoly.blend`
- `_uv.blend`
- `_rig.blend`
- `_collision.blend`
- dossier `_LODs`
- exports moteur séparés.

L'auto-rig est volontairement un squelette générique de départ, pas un remplacement d'un rig humain expert ou de Rigify.
