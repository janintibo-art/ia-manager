# IA Manager v123 — Fiabilité générale

Cette mise à jour applique le premier lot de corrections du grand check-up.

## Corrections principales

- les créations image, audio et 3D terminées en retard ne sont plus ajoutées à une autre conversation ;
- les aperçus 3D restent liés au bon message ;
- Blender et le pipeline se débloquent si un programme refuse de démarrer ;
- les scripts Blender renvoient maintenant un code d'erreur en cas d'échec Python ;
- le pipeline vérifie la présence réelle de ses exports et dossiers produits ;
- les scripts d'export animé GLB et FBX ne s'écrasent plus ;
- les références et créations reçoivent un nom réellement unique ;
- le mode hors ligne global est transmis aux créations AudioCraft, TripoSR et Hunyuan3D ;
- la sauvegarde des réglages inclut Blender, ComfyUI et les outils créatifs ;
- les conversations et métadonnées de projets sont écrites de manière atomique ;
- la vérification SHA-256 des gros modèles travaille par blocs au lieu de charger le fichier entier en mémoire ;
- un téléchargement corrompu est supprimé correctement ;
- une erreur de lecture des interfaces réseau ne bloque plus toute l'application ;
- le contrôle d'écriture du dossier de stockage ne peut plus supprimer une ancienne sonde.

## Validation

- 195 tests pytest réussis ;
- test de démarrage complet réussi avec 21 pages, dont Studio IA local et Termux ;
- tests ciblés réussis pour les changements de conversation et les échecs de démarrage Blender ;
- GitHub Actions utilise désormais pytest et construit les extensions v100, v120 et v121 pendant le contrôle d'interface.

Les créations réelles avec GPU, les gros modèles et WinGet restent à valider sur le PC Windows de destination.
