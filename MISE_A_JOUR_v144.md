# IA Manager v144 — Abliteration Lab

Nouvel onglet `🧬 Abliteration Lab`.

## Moteur
Intégration épinglée de `jim-plus/llm-abliteration`
au commit `ca6e223843f3aec83b47a0926f5b4c78859c120b`.

## Méthodes
- Conventionnelle
- Projected
- Biprojected
- Norm-preserving biprojected / MPOA

## Workflow
1. Choisir le modèle source
2. Lire éventuellement son `config.json`
3. Mesurer les directions harmful / harmless
4. Choisir les couches et la force
5. Appliquer l’intervention
6. Envoyer le checkpoint complet vers `GGUF → Ollama`

## Fonctions
- environnement Python isolé
- installation/réparation sans terminal
- mesure 4-bit optionnelle
- batch configurable
- suggestion heuristique de plage de couches pour les modèles locaux
- YAML généré automatiquement
- journal temps réel
- arrêt propre
- verrou de ressources locales
- historique des traitements
- conservation du modèle source
- sortie dans `AbliterationLab/`

La mesure projetée utilise l’option officielle `--projected`.
Le mode MPOA combine projection à la mesure, projection pendant l’intervention
et `--normpreserve`.
