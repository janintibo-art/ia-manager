# IA Manager v154 — Import automatique des modèles ComfyUI

Ajoute dans Outils locaux un bloc :
`📥 Importer les modèles téléchargés dans ComfyUI`.

Fonctions :
- scan du dossier Téléchargements ;
- reconnaissance automatique des fichiers modèles ;
- aperçu de la destination avant déplacement ;
- aucun écrasement de fichier existant ;
- import en un clic ;
- historique des déplacements ;
- ouverture directe du dossier `ComfyUI/models`.

Règles connues :
- `qwen_3_4b.safetensors` → `models/text_encoders`
- `z_image_turbo_bf16.safetensors` → `models/diffusion_models`

Règles génériques :
- qwen / text_encoder → `text_encoders`
- clip → `clip`
- vae → `vae`
- lora → `loras`
- controlnet → `controlnet`
- diffusion / unet → `diffusion_models`
- autres `.safetensors/.ckpt/.pt/.pth/.bin` → `checkpoints`

Après import : actualiser ou redémarrer ComfyUI.
