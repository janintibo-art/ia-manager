# IA Manager v109 — Recherche universelle

Nouvel onglet **Recherche universelle** dans Studio IA local.

## Sources interrogées simultanément

- Hugging Face GGUF
- Hugging Face Spaces
- Pinokio
- GitHub
- Civitai
- ModelScope

Chaque source possède son propre worker. Une erreur ou une limite sur une source
n'interrompt donc plus la recherche globale.

## Filtres

- source ;
- type : texte/code, image, audio, vidéo, 3D, voix, RAG/documents, application/outil ;
- local uniquement ;
- favoris.

## Favoris

Les favoris de résultats sont persistants dans `settings.json` sous une clé dédiée.
Ils ne téléchargent rien : ils servent à retrouver rapidement une ressource vue dans
un des catalogues.

## Sources complémentaires

Stability Matrix, Comfy Registry et OpenModelDB restent dans **Sources+**.
Elles ne sont pas agrégées automatiquement tant qu'une API de recherche stable et
documentée n'est pas utilisée par IA Manager.
