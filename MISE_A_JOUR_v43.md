# IA Manager v43 — export des favoris

Les favoris de modèles peuvent maintenant être déplacés entre installations.

## Export

Le bouton **Exporter favoris** crée un petit fichier JSON contenant uniquement la source, l'identifiant, le nom et la date d'enregistrement de chaque modèle.

## Import

Le bouton **Importer favoris** vérifie le format et recharge au maximum 200 entrées. Aucun jeton GitHub, Civitai, API ou contenu de conversation n'est inclus.

Les favoris sont également inclus dans la sauvegarde générale de configuration.

## Vérification

La compilation syntaxique et les 38 tests ciblés passent localement. GitHub Actions doit confirmer la compilation Windows et l'interface complète.
