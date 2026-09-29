# IA Manager v140 — Benchmark VRAM/CPU et évaluation automatique

Nouvel onglet `📊 Benchmark`.

Fonctions :
- sélection de plusieurs modèles Ollama ;
- même batterie de prompts pour tous ;
- répétitions configurables ;
- température 0 et seed 42 ;
- temps total, temps de chargement, temps prompt et génération ;
- tokens d’entrée / sortie ;
- tokens par seconde ;
- chronométrage mural ;
- RAM système avant / après chaque test ;
- VRAM du modèle chargé via `/api/ps` quand disponible ;
- résumé par modèle ;
- détail prompt par prompt ;
- arrêt après la requête en cours ;
- sauvegarde automatique JSON dans `~/.ia_manager/benchmarks/`.

La VRAM indiquée est celle du modèle chargé rapportée par Ollama,
pas un pic échantillonné en continu.
