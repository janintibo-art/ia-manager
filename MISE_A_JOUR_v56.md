# IA Manager v56 — Obliteratus : détection Python intégrée

Mise à jour à appliquer à votre installation existante v55. Cette archive contient uniquement les fichiers modifiés ou ajoutés, sous ia_manager/.

- Bouton « Détecter Python automatiquement », sans commande à saisir.
- Vérification réelle de Python 3.10+ et de la disponibilité de venv.
- Recherche du Python choisi, du Python de l’application hors EXE, du lanceur py, du PATH, des dossiers Windows habituels et du registre Python.
- Exclusion du raccourci direct Microsoft Store qui provoquait le code 9009.
- Le chemin réel détecté est renseigné et mémorisé automatiquement.
- Installer / réparer vérifie Python avant de démarrer l’installation existante.
- Détection asynchrone, délai de 5 secondes maximum par candidat et bouton Arrêter.
- Page organisée en étapes et accès au téléchargement officiel si Python manque.

Utilisation : ouvrez Obliteratus, cliquez sur Détecter Python automatiquement, puis Installer / réparer. Une fois l’installation terminée, cliquez sur Lancer en local et ouvrez l’interface locale.

Le code de détection est intégré ; Python et les dépendances volumineuses d’Obliteratus ne sont pas inclus dans ce ZIP. Si aucun interpréteur n’est installé, utilisez le bouton de téléchargement officiel puis relancez la détection.

Validation : quatre tests automatisés du détecteur, compilation Python, vérification Qt hors écran de la détection réelle, du cas absent et de l’enchaînement vers l’installation. Installation complète d’Obliteratus et test sur Windows non exécutés dans cet environnement Linux.
