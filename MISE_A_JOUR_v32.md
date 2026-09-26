# IA Manager v32 — recherche multi-sources

L'onglet **Recherche** propose maintenant une source **GitHub (GGUF)** en plus de Hugging Face.

## GitHub

La recherche interroge les dépôts populaires qui contiennent des modèles GGUF. En ouvrant un dépôt, IA Manager lit ses releases et affiche uniquement les fichiers `.gguf` directement installables. Après confirmation de la taille, le fichier est téléchargé dans le cache local puis importé dans Ollama.

Les archives découpées en plusieurs fichiers et les fichiers `mmproj` sont signalés ou ignorés pour éviter une installation incomplète. Le bouton d'ouverture mène au dépôt GitHub pour consulter sa licence et sa documentation.

## Autres sources disponibles

Hugging Face reste disponible pour les dépôts GGUF détaillés. Ollama possède aussi sa recherche directe et son champ d'installation par nom. Les fichiers GGUF locaux peuvent enfin être importés depuis **Connexions**. Cette séparation évite de présenter comme installables les modèles image ou les formats qui ne sont pas compatibles avec Ollama.

## Vérification

La compilation syntaxique et les 25 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
