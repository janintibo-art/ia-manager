# IA Manager v120 — Chat 3D direct

La 3D du Chat devient réellement générative.

## TripoSR
Une image jointe est transmise au `run.py` officiel de TripoSR :
- détourage automatique ;
- reconstruction ;
- extraction du mesh ;
- export GLB.

Le GLB revient dans la conversation.

## Hunyuan3D 2
La génération utilise l'API Python officielle :
`Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(...)`
puis export du trimesh en GLB.

## Depuis le résultat du Chat
- ouvrir le GLB ;
- ouvrir son dossier ;
- envoyer vers Blender Studio ;
- envoyer vers Pipeline personnage.

## Prérequis
Le moteur choisi doit déjà être installé dans **Outils locaux**.
Au premier lancement, Internet reste nécessaire si les poids n'ont pas encore été mis en cache.

## Sécurité
- pas de shell ;
- arguments subprocess séparés ;
- délai maximal d'une heure ;
- l'image source et le GLB sont conservés dans `Creations Chat` ;
- aucun fichier source n'est écrasé.
