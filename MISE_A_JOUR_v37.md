# IA Manager v37 — source Civitai

La recherche multi-sources accueille maintenant **Civitai** pour les modèles d'image.

## Recherche image

La source Civitai interroge le catalogue public et affiche le nom, le type (Checkpoint, LoRA, VAE, etc.), l'auteur et les téléchargements. La fiche originale s'ouvre directement sur Civitai.

## Compatibilité

Les modèles Civitai sont destinés aux outils d'image et ne sont pas installés dans Ollama. IA Manager l'indique explicitement afin d'éviter de télécharger un fichier incompatible avec le moteur de discussion. Les sources GGUF gardent leur installation Ollama séparée.

## Vérification

La compilation syntaxique et les 32 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
