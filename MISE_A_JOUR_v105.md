# IA Manager v105 — Utilitaires installables automatiquement

Mise à jour différentielle après v104.

## Nouveaux utilitaires automatisables

Chaque utilitaire possède son propre environnement Python et son propre manifest :

- FFmpeg privé via `imageio-ffmpeg`
- rembg + ONNX Runtime
- Real-ESRGAN (dépôt officiel)
- faster-whisper
- Demucs
- ChromaDB
- FAISS CPU

Les packs v103 sont enrichis automatiquement avec ces utilitaires quand ils sont utiles.

## Installation et reprise

L'onglet **Studio IA local > Installer un pack** gère maintenant deux types d'étapes :

- `moteur` : ComfyUI, AudioCraft, TripoSR, Hunyuan3D 2, via le gestionnaire existant ;
- `utilitaire` : les sept outils v105 ci-dessus, via un environnement dédié.

Chaque utilitaire écrit son état dans `ia_manager_utility.json` et son journal dans
`journal.log`. Une installation incomplète reste sur disque et peut être reprise.

Les anciens plans v104 sont migrés vers le format v105. L'indice est réinitialisé, puis
les manifests existants permettent de sauter automatiquement tout ce qui est déjà terminé.

## Sécurité

- Aucun `shell=True`.
- Commandes sous forme programme + liste d'arguments.
- Un dossier non géré n'est jamais adopté ni écrasé.
- FFmpeg est privé à IA Manager et ne modifie pas le PATH système permanent.
- Les poids de Whisper, Demucs, rembg et Real-ESRGAN ne sont pas préchargés automatiquement.
- FAISS CPU dépend de la disponibilité d'une roue compatible avec la plateforme ; en cas
  d'échec, le plan reste reprenable et le journal indique l'erreur.
