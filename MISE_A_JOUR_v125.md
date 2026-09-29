# IA Manager v125 — Correctif compilation Windows

- Corrige le test Blender qui utilisait par erreur un fichier `.blend` comme faux exécutable.
- Le test crée maintenant `blender.exe` sous Windows et vérifie séparément la scène source.
- Aucun comportement de l’application n’est retiré : toutes les corrections v123 et v124 restent actives.
- 197 tests réussis localement.
