# IA Manager v141 — Évaluation qualitative explicite

Ajoute au Benchmark une section `Évaluation qualitative Avant / Après`.

Types de tests :
- `contient`
- `exact`
- `regex`
- `nombre`
- `python` : syntaxe Python vérifiée avec `ast.parse`, sans exécuter le code
- `manuel`

Fonctions :
- deux modèles comparés sur les mêmes tests ;
- température 0 et seed 42 ;
- réponse attendue par test ;
- diagnostic détaillé Avant / Après ;
- réponses complètes conservées dans l’historique ;
- taux de réussite uniquement sur les critères automatiquement vérifiables ;
- aucun classement global de qualité ;
- arrêt propre après la requête en cours ;
- historique JSON sous `~/.ia_manager/benchmarks/qualitatif/`.

Le score indique seulement si les critères explicitement définis ont été satisfaits.
Il ne remplace pas l’évaluation humaine de la qualité générale des réponses.
