# IA Manager v100 — Studio IA local

Cette mise à jour ajoute un nouvel écran **Studio IA local** sans remplacer les 19 onglets existants.

## Nouveautés

- Catalogue de **30+ modèles** classés : texte/code, image, audio, voix, vidéo, 3D, vision et RAG.
- Catalogue de **20 outils locaux** complémentaires : ComfyUI, Diffusers, rembg, Real-ESRGAN, Demucs, Whisper, Blender, Chroma, FAISS, etc.
- **12 pipelines** prêts à préparer : image propre, sprite, musique + stems, doublage, sous-titres, image→3D, texte→vidéo, RAG documents, assistant de code…
- Estimation de compatibilité à partir de la **RAM/VRAM** renvoyée par l'onglet Analyse.
- Filtres par catégorie, recherche libre et option « seulement les choix adaptés ».
- Accès direct aux pages officielles des modèles/outils.
- Bouton de retour vers le gestionnaire **Outils locaux** v99 pour installer/démarrer les moteurs déjà pris en charge.

## Sécurité et philosophie

Le Studio v100 est volontairement un **catalogue et orchestrateur de préparation** : il ne télécharge ni n'exécute automatiquement un nouveau moteur simplement parce qu'il apparaît dans la liste. Les installations v99 existantes restent protégées et séparées. Les valeurs de RAM/VRAM sont des repères prudents et non des garanties de fonctionnement.

## Intégration

La v100 est branchée via `src/ui/v100_extension.py`, appelée après la création de `MainWindow`. Les indices et raccourcis des 19 onglets précédents ne changent donc pas. La nouvelle entrée est ajoutée dynamiquement dans la navigation sous « STUDIO V100 ».

## Tests ajoutés

`tests/test_v100_studio.py` vérifie la taille du catalogue, les domaines, le filtrage, l'estimation de compatibilité et l'extraction RAM/VRAM.
