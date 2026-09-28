# v92 — Correction du test Windows

Correctif à appliquer sur v90 ou v91. Conserve toutes les fonctions installées.

Le test test_import_checks_and_path_quoting comparait le chemin temporaire brut
au chemin résolu exporté dans le Modelfile. Windows peut normaliser la casse
du lecteur (C: / c:) lors de resolve(), ce qui provoquait un faux échec.

Le test compare maintenant le chemin résolu, vérifie qu’il désigne le même dossier,
contrôle les guillemets JSON et conserve la vérification du paramètre num_ctx.
Aucun test supprimé ou ignoré. Aucun changement du code d’import Ollama.

Validation : 80 tests passent dans l’environnement Linux disponible. Le résultat
de la compilation Windows sera confirmé par GitHub Actions après envoi.
L’exception de connexion locale visible plus haut dans la capture ne correspond
pas au test en échec : le résumé indique un unique échec de comparaison du chemin.
