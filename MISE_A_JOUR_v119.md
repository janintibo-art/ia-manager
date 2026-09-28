# IA Manager v119 — Chat créatif multimodal

Le sélecteur du Chat contient maintenant aussi des modèles créatifs locaux.

## Image
- SDXL 1.0
- SDXL Turbo
- Animagine XL

Le Chat envoie le prompt à ComfyUI local, récupère l'image, la sauvegarde dans
`Creations Chat` sur le stockage choisi et l'affiche directement dans la conversation.

Le checkpoint correspondant doit déjà être présent dans ComfyUI.

## Audio
- MusicGen Small
- AudioGen

Le Chat utilise directement l'environnement AudioCraft géré par IA Manager.
Le WAV est généré localement et un bouton **Écouter le WAV** apparaît dans la conversation.
On peut demander par exemple `durée 12 s` ; limite v119 : 20 secondes.

## 3D
- Hunyuan3D 2
- TripoSR

La v119 prépare la référence image depuis la pièce jointe, l'enregistre dans
`Creations Chat`, puis propose un bouton pour installer/démarrer le moteur 3D.
La génération mesh entièrement automatique sera ajoutée après stabilisation des pipelines 3D.

## Sécurité / compatibilité
- les modèles texte Ollama et fournisseurs restent inchangés ;
- les créations restent locales ;
- aucun moteur créatif n'est téléchargé automatiquement depuis le Chat ;
- si un moteur ou un checkpoint manque, le Chat affiche ce qu'il faut installer.
