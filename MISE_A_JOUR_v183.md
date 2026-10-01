# IA Manager v183 — derniers blocages

## Stable Audio Open
- ajout d'un champ de jeton Hugging Face masqué ;
- enregistrement local dans IA Manager ;
- vérification de l'accès au dépôt ;
- transmission du jeton au téléchargement par variables d'environnement ;
- le jeton n'apparaît pas dans la ligne de commande.

Stable Audio Open reste **Partiel** tant que l'autorisation Hugging Face n'est pas accordée.

## TRELLIS
- détection WSL / WSL2 ;
- détection NVIDIA / nvidia-smi ;
- détection CUDA Toolkit / nvcc ;
- installation WSL2 + Ubuntu avec validation UAC ;
- bootstrap Linux ;
- clone TRELLIS avec sous-modules.

TRELLIS reste **Partiel** tant que l'environnement WSL/CUDA n'est pas complètement fonctionnel.

## Résultat
Les deux derniers cas orange ont maintenant un parcours guidé et vérifiable depuis IA Manager.
