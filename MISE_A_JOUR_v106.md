# IA Manager v106 — Poids & stockage

Mise à jour différentielle après v105.

## Nouvel onglet : Poids & stockage

Le Studio IA local possède maintenant un écran dédié aux fichiers volumineux :

- choix du dossier principal par navigation, par exemple `D:\IA Manager` ;
- réutilisation du réglage `storage_root` déjà présent dans IA Manager ;
- inventaire des zones connues :
  - téléchargements IA Manager ;
  - modèles Ollama ;
  - caches des moteurs créatifs configurés ;
- taille occupée et espace libre par disque ;
- inventaire des gros fichiers de poids connus (`GGUF`, `safetensors`, `ckpt`, `ONNX`, etc.) ;
- détection des téléchargements incomplets ;
- nettoyage confirmé des seuls fichiers temporaires reconnus ;
- estimation de l'espace nécessaire avant de préparer un pack Studio IA ;
- marge de 25 % ajoutée à l'estimation pour caches et fichiers temporaires.

## Sécurité

- Aucun modèle complet n'est supprimé automatiquement.
- Le nettoyage accepte uniquement les fichiers reconnus incomplets dans les zones gérées.
- Les liens symboliques sont ignorés pendant l'inventaire.
- Changer `storage_root` ne déplace pas silencieusement les anciens fichiers.
- L'emplacement Ollama reste géré séparément par le mécanisme déjà présent dans IA Manager.

## Suite possible

La migration physique vérifiée d'un ancien stockage vers un nouveau disque pourra être
ajoutée dans une version suivante avec copie, comparaison et suppression uniquement après
validation explicite.
