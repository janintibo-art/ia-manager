# IA Manager v133 — MergeKit vers GGUF / Ollama / Chat

Cette mise à jour complète le workflow MergeKit.

Nouveau flux :
1. fusion de deux modèles avec MergeKit ;
2. sélection automatique de la dernière fusion ;
3. validation du checkpoint Hugging Face ;
4. conversion en GGUF via llama.cpp ;
5. création automatique du modèle dans Ollama ;
6. ouverture immédiate dans le Chat IA Manager.

Fonctions ajoutées :
- section « Exporter la fusion vers Ollama » ;
- bouton « Utiliser la dernière fusion » ;
- nom Ollama personnalisable ;
- conversion GGUF automatique ;
- téléchargement/préparation automatique du convertisseur llama.cpp si nécessaire ;
- import Ollama automatique ;
- bouton « Ouvrir dans Chat » après succès ;
- actualisation du cache des modèles Ollama ;
- journal partagé avec MergeKit ;
- arrêt propre et protection contre les traitements simultanés.

Les anciennes fusions et conversions restent conservées.
