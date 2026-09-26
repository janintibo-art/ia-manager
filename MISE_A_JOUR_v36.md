# IA Manager v36 — source ModelScope

La recherche propose désormais **ModelScope** en plus de Hugging Face et GitHub.

## Recherche

Le nouveau choix de source interroge l'API publique ModelScope, trie les dépôts par téléchargements et affiche leur auteur, leur description et leur popularité. Le bouton d'ouverture permet de consulter la fiche originale.

## Compatibilité clairement affichée

ModelScope publie de nombreux formats : Safetensors, PyTorch, Diffusers, audio ou GGUF. IA Manager affiche la fiche et prévient lorsque le dépôt n'est pas directement installable dans Ollama. Les installations automatiques restent réservées aux fichiers GGUF compatibles.

## Vérification

La compilation syntaxique et les 30 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et le comportement visuel.
