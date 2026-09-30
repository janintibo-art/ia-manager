# IA Manager v172 — poids Audio / 3D téléchargeables depuis l'application

Ajouts :
- MusicGen Small : préchargement direct des poids officiels.
- MusicGen Melody : préchargement direct des poids officiels.
- AudioGen Medium : préchargement direct des poids officiels.
- TripoSR : préchargement de config.yaml + model.ckpt.
- Hunyuan3D : préchargement du modèle Mini Turbo utilisé par défaut par l'interface et des poids de texture.
- Vérification de l'état des poids.
- Bouton pour ouvrir le cache local du moteur.
- Les téléchargements passent par huggingface_hub dans l'environnement du moteur afin que le moteur retrouve directement son cache.

La préparation des poids nécessite que le moteur correspondant soit déjà installé dans Outils locaux.
