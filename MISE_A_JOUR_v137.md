# IA Manager v137 — Unsloth LoRA / QLoRA avancé

Ajoute :
- choix LoRA / QLoRA ;
- profils Automatique GPU, Économe, Équilibré, Qualité, Personnalisé ;
- learning rate ;
- accumulation de gradient ;
- warmup ratio ;
- AdamW 8-bit, AdamW PyTorch, Paged AdamW 8-bit ;
- nombre de checkpoints conservés ;
- seed ;
- avertissement VRAM si LoRA paraît trop lourd.

Le runner existant est étendu sans supprimer l’historique, l’essai court,
les datasets, l’export du modèle complet ni l’import Ollama.
