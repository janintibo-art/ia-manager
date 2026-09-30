# IA Manager v171 — packs ComfyUI téléchargeables

## Ajouts

- FLUX.1 Schnell FP8 peut maintenant être téléchargé depuis l'onglet Création d'images.
- Wan 2.1 T2V 1.3B : téléchargement automatique du modèle, de l'encodeur UMT5 FP8 et du VAE dans les bons dossiers ComfyUI.
- LTX-2 FP8 : téléchargement automatique du checkpoint et de l'encodeur de texte, avec avertissement avant le très gros téléchargement.
- Reprise des téléchargements interrompus grâce aux fichiers `.part`.
- Vérification du pack avant/après téléchargement.
- Les fichiers déjà présents ne sont pas retéléchargés.

## Dossiers utilisés

Wan 2.1 :
- `ComfyUI/models/diffusion_models/`
- `ComfyUI/models/text_encoders/`
- `ComfyUI/models/vae/`

LTX-2 :
- `ComfyUI/models/checkpoints/`
- `ComfyUI/models/text_encoders/`

FLUX.1 Schnell FP8 :
- `ComfyUI/models/checkpoints/`

## Remarque

Le téléchargement des poids ne garantit pas qu'un modèle très lourd soit adapté au GPU installé.
IA Manager conserve les contrôles matériel et les avertissements séparément de la possibilité de téléchargement.
