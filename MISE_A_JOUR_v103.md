# IA Manager v103 — Mon Studio intelligent

Mise à jour différentielle après la v102.

## Nouveautés

- Nouvel onglet **Mon Studio** en première position du Studio IA local.
- 8 packs : Essentiel local, Développement & code, Image & assets 2D, Audio & musique,
  Vidéo, 3D & personnages, Documents & RAG et Studio complet.
- Le pack utilise la RAM et la VRAM déjà détectées par l'onglet Analyse.
- Chaque modèle est classé : bon candidat, limite, difficile ou à vérifier.
- « Préparer ce pack » ajoute uniquement les modèles raisonnables aux favoris et
  charge le pipeline conseillé, sans téléchargement automatique.
- Enrichissement du catalogue avec plus de 15 modèles additionnels :
  Qwen3, DeepSeek R1 Distill, SDXL Turbo, FLUX Fill, SAM 2, Depth Anything V2,
  ACE-Step, Bark, RIFE, Video2X, Stable Fast 3D, MVDream, Jina Embeddings v3,
  BGE Reranker, etc.
- Plus de 10 outils supplémentaires : llama.cpp, Open WebUI, AnythingLLM,
  InvokeAI, Kohya SS, RVC, Audacity, RIFE, Video2X, MeshLab, ONNX Runtime…
- 6 nouveaux modèles de pipelines préparés.

## Stabilité

- La correction v102 de l'onglet Recherche reste intégrée.
- L'enrichissement du catalogue est idempotent : aucun doublon si l'extension
  est appelée plusieurs fois.
- Aucun moteur lourd, poids IA ou dépendance système n'est inclus dans le ZIP.
- Aucun téléchargement n'est déclenché automatiquement.

## Validation

- Tests de non-régression sur l'extension du catalogue, les packs, la
  compatibilité matérielle, l'exclusion des modèles trop exigeants et la
  conservation du correctif Recherche v102.
