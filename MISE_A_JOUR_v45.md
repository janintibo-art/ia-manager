# IA Manager v45 — export des fiches modèles

Chaque fiche détaillée peut maintenant être conservée localement.

## Contenu

Le bouton **Exporter la fiche** produit un JSON avec l'identifiant, la source, l'auteur, la licence, le format, les tailles disponibles, les versions et le lien du modèle. Le texte intégral du README n'est pas recopié afin de garder un fichier léger.

L'export fonctionne pour Hugging Face, GitHub, ModelScope et Civitai. Il ne contient aucune clé API, aucun jeton et aucune conversation.

## Vérification

La compilation syntaxique et les 40 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
