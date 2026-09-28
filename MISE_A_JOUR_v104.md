# IA Manager v104 — Installation guidée des packs

Mise à jour différentielle après v103.

## Nouveautés

- Nouvel onglet **Installer un pack** dans Studio IA local.
- Installation séquentielle des moteurs que le gestionnaire v99 sait déjà piloter :
  - ComfyUI
  - AudioCraft
  - TripoSR
  - Hunyuan3D 2
- Choix séparé de Python 3.9 pour AudioCraft et Python 3.10/3.11 pour les moteurs image/3D.
- Profil NVIDIA/CPU partagé avec le gestionnaire d'outils existant.
- Reprise après arrêt ou coupure : le plan est conservé dans `settings.json` et les manifests
  existants déterminent les moteurs déjà terminés.
- Continuation automatique facultative vers le moteur suivant.
- Bouton d'arrêt propre « après l'étape en cours » : aucun processus n'est tué brutalement.
- Les outils non encore gérés automatiquement sont affichés comme installations manuelles
  avec leur description et leur page officielle.
- Le journal détaillé reste celui d'Outils locaux, moteur par moteur.

## Sécurité

La v104 ne crée pas de nouvel installateur générique. Elle réutilise uniquement les quatre
recettes déjà contrôlées par IA Manager. Les outils supplémentaires (FFmpeg système, Blender,
Chroma, FAISS, Audacity, etc.) ne sont pas installés automatiquement tant qu'une recette
dédiée et vérifiée n'existe pas.

Aucun modèle ou poids IA n'est téléchargé automatiquement par le nouvel assistant.
La préparation des poids reste une étape explicite après installation du moteur.

## Reprise

Si Internet coupe pendant une installation :
1. le moteur concerné reste marqué « installation incomplète » ;
2. le plan de pack reste enregistré ;
3. relancer IA Manager ;
4. ouvrir Studio IA local > Installer un pack ;
5. cliquer **Installer / reprendre**.

Le gestionnaire réutilise le dossier déjà créé et poursuit la recette du moteur concerné.
