# IA Manager v107 — Source Pinokio

Pinokio est intégré comme source d'applications et modèles locaux dans Studio IA.

## Nouvel onglet Pinokio

- recherche dans le registre officiel Pinokio ;
- filtres tri, plateforme et GPU ;
- affichage du nom, auteur, description et tags ;
- détection de `pterm` dans le PATH ;
- détection du serveur local Pinokio sur `127.0.0.1:42000` ;
- ouverture de la fiche ou du dépôt source ;
- téléchargement explicite via `pterm download` ;
- lancement explicite via `pterm run ... --open`.

## Sécurité

Pinokio est un launcher capable d'exécuter des commandes. IA Manager sépare donc :

1. **Télécharger dans Pinokio** : clone l'application sans lancer ses scripts.
2. **Lancer / installer dans Pinokio** : action séparée avec avertissement et confirmation.

IA Manager n'exécute jamais automatiquement une entrée du registre.

## Dépendance facultative

La recherche du registre fonctionne sans `pterm`.
Pour télécharger/lancer depuis IA Manager, `pterm` doit être disponible dans le PATH.

Documentation officielle :
- https://github.com/pinokiocomputer/pterm
- https://github.com/pinokiocomputer/pinokio
