# IA Manager v136 — Unsloth autonome

Cette mise à jour rend l’atelier d’entraînement Unsloth beaucoup plus autonome.

Ajouts :
- bloc `🦥 Unsloth autonome` dans `Entraîner / Fusionner` ;
- installation / réparation sans terminal ;
- environnement isolé sous `~/.ia_manager/tools/unsloth/.venv` ;
- utilisation de `uv`, conformément au flux d’installation Unsloth Core actuel ;
- installation `unsloth`, `trl`, `datasets` et `psutil` ;
- sélection automatique du moteur Python Unsloth dans l’atelier ;
- diagnostic CUDA / GPU / VRAM ;
- journal intégré ;
- arrêt propre de l’installation ou du diagnostic ;
- l’environnement IA Manager principal reste séparé.

L’entraînement QLoRA déjà présent dans IA Manager réutilise ensuite ce moteur.
