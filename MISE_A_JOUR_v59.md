# v59 — Import Obliteratus dans mes IA

La page Obliteratus contient une section « Ajouter un modèle Obliteratus à mes IA ».

1. Terminer le traitement dans l'atelier et attendre la sauvegarde.
2. Dans IA Manager, arrêter l'atelier, puis cliquer sur Actualiser dans la nouvelle section.
3. Sélectionner le checkpoint (les plus récents sont en premier), ou Autre dossier.
4. Choisir le nom Ollama. Un nom existant sera remplacé après confirmation ; changer de nom pour garder deux versions.
5. Cliquer sur Convertir et ajouter à mes IA. Le journal affiche la préparation, la conversion puis l'importation.
6. Après le message de réussite, ouvrir Chat et cliquer sur son bouton d'actualisation.

Le convertisseur et son Python sont dans ~/ia-conversion, séparés de l'environnement CUDA d'Obliteratus. Les outils installés pendant le dépannage sont réutilisés. Au premier usage, les sources officielles llama.cpp et leurs dépendances sont téléchargées. La conversion conserve la précision F16 et crée un nouveau fichier dans ia-conversion/exports ; les checkpoints ne sont pas modifiés. Prévoir plusieurs Go d'espace disque. Chaque import conserve son GGUF, même si l'import Ollama échoue.

Le serveur Ollama doit être installé et démarré sur le PC. Certaines architectures peuvent ne pas être prises en charge par le convertisseur ou Ollama : le journal conserve l'erreur et la chaîne s'arrête. Arrêter interrompt l'étape courante. Une conversion interrompue peut laisser un GGUF partiel dans exports ; relancer crée une autre sortie.

Cette mise à jour ne relance pas l'installation CUDA. Elle automatise la procédure GGUF validée manuellement par l'utilisateur avec TinyLlama. Le rafraîchissement du sélecteur Chat reste manuel.

Validation : compilation syntaxique Python et tests de découverte, rejet des noms invalides, séparation des environnements, construction des commandes et préservation des sorties. Pas de compilation Windows ni de test réel GPU/Ollama dans cet environnement. PyQt6 indisponible pour un test visuel local.
