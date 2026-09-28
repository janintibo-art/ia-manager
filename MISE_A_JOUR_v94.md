# v94 — Exemples, historique et fusion SLERP

Mise à jour différentielle à appliquer après v93 (et le correctif v92).

## Exemples
Nouvelle page dans Entraîner / Fusionner. Ajout, modification, suppression
et import de questions, contextes facultatifs et réponses attendues.
L’édition se fait dans des champs multilignes. Import ajoute les exemples au
jeu en cours ; aucune conversation n’est récupérée automatiquement.
Enregistrer crée une nouvelle copie JSONL dans Entrainement/Exemples et sélectionne
ce fichier dans la page Entraînement. Les doublons exacts sont retirés.
Les brouillons de moins de 10 exemples peuvent être sauvegardés, mais ne sont pas
entraînables. L’éditeur accepte 2000 exemples ; les fichiers plus grands peuvent
être sélectionnés directement dans la page Entraînement (limite globale 50 Mo).
Les modifications non enregistrées restent en mémoire et sont perdues à la fermeture.

## Historique
Affiche jusqu’à 200 tâches récentes : diagnostic, essai, entraînement, fusion.
États : en cours dans cette instance, terminé, échec, arrêté ou incomplet.
Une tâche restée en cours lors d’un arrêt brutal est signalée incomplète à la
réouverture. Les anciennes tâches sont retrouvées à partir de leurs fichiers.
Les métriques disponibles sont consultables : loss avant/après et pic VRAM des essais.
Une tâche réussie avec poids Safetensors et config.json peut préparer un import
Ollama ou renseigner la source A/B d’une future fusion. Ces boutons ne lancent
ni calcul, ni import automatiquement. Le dossier peut être ouvert pour voir
le journal complet. Les imports Ollama ne sont pas encore inclus dans cette liste.

## Fusion
Choix entre moyenne pondérée (linéaire) et interpolation sphérique SLERP.
SLERP désigne A comme base et B comme autre modèle ; le réglage de contribution
de B correspond au paramètre t. Recette sauvegardée avec la tâche.
Les contrôles de configuration et de vocabulaire restent actifs. Deux modèles
issus de la même base sont requis ; pas de fusion arbitraire de GGUF.
Aucune méthode ne garantit une amélioration : comparer les réponses après import.
Référence : https://github.com/arcee-ai/mergekit/blob/main/docs/multimerge.md

## Validation
86 tests passent, dont brouillons JSONL, doublons, absence d’écrasement, états
de l’historique et recette SLERP transmise au runner. Les tests ML utilisent
des moteurs simulés : aucune fusion réelle ni entraînement CUDA effectué ici.
Les 16 onglets s’ouvrent en mode offscreen (détection réseau simulée uniquement
pour le contrôle de fenêtre dans cet environnement). Affichage de l’éditeur
vérifié en thème sombre. Compilation Windows à confirmer avec GitHub Actions.
