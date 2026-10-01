# IA Manager v180 — packs Image avancés

La v180 réduit la liste orange de l’audit avec quatre installations Image directement gérées dans IA Manager.

## Nouveaux packs

- FLUX.1-dev FP8
- Stable Diffusion 3.5 Medium FP8
- ControlNet Union SDXL ProMax
- IP-Adapter Plus SDXL

## Installation

Un nouveau bloc **Packs Image avancés — installation directe** apparaît dans Création d’images.

Il sait :
- détecter le ComfyUI géré par IA Manager ;
- demander le dossier d’un ComfyUI externe si nécessaire ;
- télécharger les fichiers dans les bons sous-dossiers ;
- reprendre un téléchargement `.part` après une coupure ;
- vérifier les fichiers déjà présents ;
- installer automatiquement le nœud `ComfyUI_IPAdapter_plus` pour IP-Adapter.

## Dossiers

- FLUX.1-dev → `models/checkpoints`
- SD 3.5 Medium → `models/checkpoints`
- ControlNet Union SDXL → `models/controlnet`
- IP-Adapter → `models/ipadapter`
- CLIP Vision IP-Adapter → `models/clip_vision`
- nœud IP-Adapter → `custom_nodes/ComfyUI_IPAdapter_plus`

## Audit

Ces quatre entrées passent maintenant de **Partiel** à **Automatique** dans la page Audit installations.

La génération avancée continue de se faire via les workflows adaptés dans ComfyUI.
