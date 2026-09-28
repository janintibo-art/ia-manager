# IA Manager v97 — Musique, sons, vidéo et 3D

À appliquer après la v96. Archive différentielle : uniquement les fichiers ajoutés/modifiés, sous ia_manager/.

## Ce que cette version ajoute

Un onglet « Audio · Vidéo · 3D » avec sept fiches, regroupées en trois catégories :

| Catégorie | Modèles | Usage |
| --- | --- | --- |
| Musique et sons | MusicGen Small, MusicGen Melody, AudioGen Medium | Musique, mélodie de référence, bruitages et ambiances |
| Vidéo | Wan 2.1 T2V 1.3B, LTX-Video | Vidéos depuis du texte ; image de référence avec un workflow LTX approprié |
| Modélisation 3D | Hunyuan3D 2, TripoSR | Création d’un maillage depuis une image ; texture selon le moteur |

Chaque fiche précise la spécialité, le type d’entrée, le moteur nécessaire, les précautions matérielles et les étapes de prise en main. Les boutons ouvrent le dépôt du modèle et sa documentation officielle.

La recherche filtre les noms et usages. Une description ou des notes, l’adresse du moteur et un dossier de résultats sont mémorisés séparément pour chaque modèle. Un exemple peut être ajouté sans effacer un brouillon. Le texte est copiable ; le dossier se sélectionne avec Parcourir.

## Limites de l’intégration

Il s’agit d’un catalogue et d’un accès aux outils externes. Cette version n’installe pas les moteurs ou les poids et n’envoie pas de génération audio, vidéo ou 3D par API. Elle n’ajoute pas ces modèles au chat Ollama et ne les marque pas comme installés.

Le bouton Ouvrir l’interface ouvre une adresse que vous avez renseignée ; il ne lance pas le processus du moteur et ne vérifie pas que les poids sont installés. AudioGen propose surtout une API Python : le champ web est facultatif, pour les personnes disposant d’une interface compatible.

Le dossier sélectionné est un raccourci pour retrouver vos fichiers ; il ne modifie pas le dossier d’export du moteur. Les images/audio de référence sont à importer dans ce moteur. Les notes de préparation 3D ne sont pas envoyées comme prompt texte à un modèle image-vers-3D.

La génération réelle reste effectuée par les outils installés sur le PC. Le calcul n’est pas effectué par Termux. La compatibilité dépend du GPU, des poids et des options : aucune compatibilité matérielle automatique n’est annoncée.

## Utilisation

1. Ouvrir Audio · Vidéo · 3D et choisir une catégorie puis une fiche.
2. Suivre le Guide d’installation officiel pour le moteur et les poids de ce modèle.
3. Lancer le moteur sur le PC. S’il propose une interface web, recopier son adresse dans IA Manager.
4. Préparer une description, la copier puis ouvrir l’interface ; importer les références dans l’outil si nécessaire.
5. Générer et exporter depuis cet outil. Enregistrer dans IA Manager un raccourci vers le dossier choisi.

Pour un personnage 3D de jeu : préparer une image montrant le corps entier, bras séparés du torse et jambes espacées ; contrôler ensuite toutes les faces du maillage. Les modèles proposés ne créent pas automatiquement un squelette ni des animations.

## Vérifications

Syntaxe Python, unicité des sept fiches, filtres, validation des URL, sauvegarde/rechargement des préférences, conservation des brouillons entre catégories, non-écrasement par les exemples, ouverture de lien simulée et état sans résultat testés. Onglet PyQt6 ouvert hors écran et inspecté visuellement. Les 18 indices de navigation sont cohérents.

Les moteurs et modèles lourds n’ont pas été installés ni exécutés dans cet environnement. Le lancement complet de l’application Windows reste à vérifier sur votre PC.

## Sources officielles consultées le 28 septembre 2026

- https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md
- https://github.com/facebookresearch/audiocraft/blob/main/docs/AUDIOGEN.md
- https://github.com/Wan-Video/Wan2.1
- https://github.com/Lightricks/LTX-Video
- https://huggingface.co/Lightricks/LTX-Video
- https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- https://github.com/VAST-AI-Research/TripoSR
