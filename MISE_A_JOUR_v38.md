# IA Manager v38 — téléchargement des modèles Civitai

Les modèles image trouvés sur Civitai peuvent maintenant être téléchargés directement dans le cache local.

## Fichiers disponibles

La fiche Civitai liste les fichiers principaux des versions publiées (`.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin` et `.zip`). Le téléchargement utilise la même barre de progression, l'annulation et la reprise que les GGUF GitHub.

## Séparation des moteurs

Le bouton devient **Télécharger pour outil image**. Le fichier est placé dans `~/.ia_manager/models/image_downloads` et enregistré dans l'historique, sans être envoyé à Ollama. Il peut ensuite être utilisé dans ComfyUI, AUTOMATIC1111 ou l'outil image compatible de votre choix.

## Vérification

La compilation syntaxique et les 33 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
