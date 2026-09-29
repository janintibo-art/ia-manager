# IA Manager v121 — Aperçu 3D dans le Chat + Game Ready automatique

## Aperçu 3D
Après génération d'un GLB par Hunyuan3D ou TripoSR, le Chat propose :
**👁️ Générer l’aperçu 3D**

Blender est lancé en arrière-plan pour :
- importer le GLB ;
- calculer son cadrage ;
- créer une caméra ;
- créer un éclairage 3 points ;
- rendre une vignette 512×512 ;
- afficher cette image directement dans la conversation.

L'aperçu est sauvegardé à côté du GLB et son chemin est conservé dans l'historique du Chat.

## Préparer automatiquement pour le jeu
Le bouton :
**🎮 Préparer automatiquement pour le jeu**

préconfigure le Pipeline personnage avec :
- nettoyage ;
- low-poly 50 % ;
- UV automatique ;
- auto-rig ;
- LOD ;
- collisions convexes ;
- export Godot.

Une confirmation est demandée avant de lancer réellement toutes les étapes.

## Réglages manuels
Le bouton Pipeline manuel v120 reste présent pour pouvoir modifier :
- ratio low-poly ;
- moteur cible ;
- animation ;
- retargeting ;
- type de collision ;
- autres étapes.

## Prérequis
Blender doit être configuré dans Blender Studio pour générer l'aperçu ou lancer le pipeline.
