# IA Manager v102 — Correction Recherche

Mise à jour différentielle après v101.

## Corrections

- Hugging Face était associé par erreur à la clé interne `github`.
  Une recherche effectuée avec « Hugging Face » pouvait donc appeler GitHub et afficher
  « Limite GitHub atteinte ».
- La récupération de la fiche détaillée avait été déplacée par erreur dans
  `export_details()`. Sélectionner un résultat affichait donc
  « Chargement de la fiche… » sans jamais lancer le worker réseau.
- La v102 rétablit l'ordre réel des sources :
  Hugging Face, GitHub, ModelScope, Civitai.
- Le signal Qt de sélection est explicitement reconnecté au gestionnaire corrigé,
  car l'ancienne méthode avait déjà été mémorisée par Qt au démarrage.

## Effet attendu

1. Une recherche Hugging Face n'est plus bloquée par la limite GitHub.
2. Cliquer sur un modèle déclenche immédiatement le chargement de sa fiche.
3. Les quantifications GGUF apparaissent ensuite et le bouton de téléchargement
   redevient disponible lorsqu'une version compatible est proposée.

Aucun moteur, modèle ou réglage existant n'est supprimé.
