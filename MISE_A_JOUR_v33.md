# IA Manager v33 — téléchargements fiables

Les téléchargements de modèles GitHub disposent maintenant d'un vrai suivi.

## Progression et annulation

Une barre affiche les octets reçus et le total lorsqu'il est fourni par GitHub. Le bouton **Annuler** arrête proprement le transfert sans bloquer l'interface.

## Reprise

Le fichier partiel est conservé dans `~/.ia_manager/models/downloads`. En relançant le même modèle, IA Manager envoie une requête HTTP `Range` et reprend au dernier octet reçu. Si le serveur ne prend pas la reprise en charge, le transfert repart automatiquement de zéro.

## Contrôle d'intégrité

Quand GitHub fournit un condensat SHA-256, le fichier est vérifié avant son import dans Ollama. Un fichier incomplet ou corrompu n'est pas installé.

## Vérification

La compilation syntaxique et les 26 tests ciblés passent localement. GitHub Actions doit confirmer la construction Windows et le comportement visuel.
