# IA Manager v179 — audit global des installations

La v179 ajoute une vraie page de suivi du chantier « tout installer depuis l'application ».

## Nouvelle page : Audit installations

Chaque modèle du catalogue Studio est classé dans l'un des trois niveaux :

- ✅ **Automatique** : le parcours d'installation/lancement est déjà pris en charge ;
- 🟠 **Partiel** : le modèle est connu mais certaines étapes restent manuelles ;
- 🔴 **À intégrer** : pas encore de parcours complet depuis IA Manager.

La page affiche aussi :
- le moteur concerné ;
- la catégorie ;
- un filtre par niveau ;
- un bouton **Ouvrir la bonne section**.

## Pourquoi cette page

Après les v173 à v178, les grands parcours sont couverts :
- Chat / Ollama ;
- Image / ComfyUI ;
- AudioCraft / MusicGen / AudioGen ;
- Vidéo / Wan / LTX ;
- 3D / TripoSR / Hunyuan3D.

La v179 sert maintenant de feuille de route interne pour les modèles plus avancés encore partiels, par exemple :
- FLUX.1-dev ;
- Stable Diffusion 3.5 Medium ;
- ControlNet ;
- IP-Adapter ;
- Stable Audio Open ;
- Whisper large-v3 ;
- Kokoro ;
- XTTS-v2 ;
- CogVideoX-2B ;
- InstantMesh ;
- TRELLIS.

## Suite conseillée

Les prochaines versions pourront traiter directement la liste orange en priorité, jusqu'à faire disparaître progressivement les installations manuelles.
