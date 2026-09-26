# v55 — Correction du test d’archivage sur Windows

À appliquer après la v54.

Le test relisait les archives JSON et Markdown sans préciser leur encodage. Sur le runner Windows, l’encodage par défaut déformait les accents alors que l’application écrivait correctement les fichiers en UTF-8. Cela faisait échouer la comparaison des messages et bloquait la compilation.

`tests/test_chat_history.py` : lecture explicitement en UTF-8 pour les deux archives.

Les trois tests d’archivage passent localement. Le programme et le format des sauvegardes ne changent pas. La compilation Windows reste à relancer sur GitHub.
