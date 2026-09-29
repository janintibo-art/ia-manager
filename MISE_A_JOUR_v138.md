# IA Manager v138 — Dataset Studio

Nouvel onglet Dataset Studio dans l’atelier Entraîner / Fusionner.

Fonctions :
- import JSONL et JSON ;
- accepte aussi quelques formats courants :
  - instruction/input/output ;
  - question/answer ;
  - prompt/completion ;
  - messages user/assistant ;
- normalisation des espaces et retours à la ligne ;
- normalisation Unicode NFC ;
- déduplication exacte insensible à la casse ;
- détection des instructions ou réponses vides ;
- rejet optionnel des exemples trop longs ;
- longueur maximale configurable ;
- analyse non destructive ;
- statistiques avant entraînement ;
- aperçu des 100 premiers exemples nettoyés ;
- liste des rejets avec raison ;
- création d’un nouveau JSONL propre ;
- rapport JSON associé ;
- bouton direct « Utiliser pour l’entraînement » vers Unsloth ;
- le fichier original n’est jamais modifié.
