# IA Manager v111 — Blender Studio

Nouveau **Blender Studio** dans Studio IA local :

- détection et sélection de Blender ;
- diagnostic de version ;
- projets sur le disque choisi ;
- scènes de départ personnage, objet et environnement ;
- structure `assets / textures / exports / renders / scripts` ;
- conversion headless GLB / GLTF / FBX / OBJ / STL / PLY ;
- copie nettoyée d'une scène `.blend` ;
- lancement normal de Blender.

Pipeline visé :

`Image / prompt → TripoSR ou Hunyuan3D → Blender → nettoyage → conversion → export jeu`

Aucun asset source n'est supprimé automatiquement.
