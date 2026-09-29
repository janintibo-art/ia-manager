# IA Manager v132 — MergeKit Studio

Nouvel atelier local intégré pour fusionner des modèles Hugging Face.

Fonctions :
- nouvel onglet `🧩 MergeKit` ;
- installation / réparation dans un environnement Python isolé ;
- installation épinglée sur une révision MergeKit vérifiée ;
- deux modèles sources : identifiants Hugging Face ou dossiers locaux ;
- choix d’un checkpoint local avec navigateur de dossiers ;
- méthodes :
  - Linear ;
  - SLERP ;
  - TIES ;
  - DARE-TIES ;
- poids A / B réglables ;
- densité réglable pour TIES / DARE-TIES ;
- tokenizer `union` et chat template automatique ;
- aperçu du YAML généré ;
- fusion CPU ou CUDA ;
- `--lazy-unpickle` pour limiter l’utilisation mémoire ;
- sorties conservées dans le dossier de modèles IA Manager sous `Fusionnes/` ;
- refus d’écraser une fusion précédente ;
- journal de progression intégré ;
- arrêt propre du processus ;
- télémétrie Hugging Face désactivée pour le processus.

Important :
les modèles fusionnés doivent avoir des architectures compatibles.
MergeKit valide la configuration et affiche les erreurs dans le journal.

Suite prévue :
conversion directe du résultat en GGUF/Ollama, MoE, extraction LoRA et fusion multi-étapes.
