# v98 — Création locale et correction du test de navigation

À appliquer après la v97. Ce ZIP n’inclut pas les poids ni les moteurs.

## Correction de la compilation

Le test de navigation créait exactement 16 onglets fictifs. Les ajouts Images et Audio/Vidéo/3D ont porté le nombre d’onglets à 18, ce qui produisait l’échec vu dans GitHub Actions. Le test vérifie maintenant le nombre d’onglets enregistrés dans la fenêtre principale, l’unicité et la continuité des indices de navigation, puis la synchronisation des liens dans les deux sens.

Le ConnectionAbortedError de la capture se produit dans un test d’annulation marqué « ok ». L’échec signalé à la fin est celui de la navigation.

## Mode local activé par défaut

Images et Audio/Vidéo/3D disposent d’une case « 100 % local ». Elle limite l’adresse du moteur à localhost ou une IP de boucle locale (127.0.0.1, ::1). Les adresses Internet et du réseau local sont refusées tant que cette case est cochée. Le choix est mémorisé.

Les appels ComfyUI de l’onglet Images désactivent également les proxies d’environnement et refusent les redirections HTTP. Le workflow intégré utilise des nœuds de génération locale SDXL. La case ne peut pas changer pendant une requête.

## Modèles utilisables sur le PC

- Images : SDXL, SDXL Turbo et Animagine avec ComfyUI ; FLUX avec son workflow propre.
- Musique : MusicGen Small ou Melody, avec AudioCraft.
- Sons : AudioGen, avec AudioCraft.
- Vidéo : Wan 2.1 et LTX-Video, avec leur moteur/workflow local adapté.
- 3D : Hunyuan3D 2 et TripoSR, avec leur installation locale et une image de référence.

Les boutons de documentation et téléchargement ouvrent toujours Internet volontairement. Télécharger une fois le moteur, ses dépendances et tous les poids nécessaires. Ensuite sélectionner les poids locaux, éviter les fournisseurs API et nœuds cloud, couper Internet puis faire un essai court. Une interface web ouverte sur localhost fonctionne sur votre PC ; elle n’est pas un service cloud.

La restriction d’adresse contrôle la destination ouverte par IA Manager. Elle ne constitue pas un pare-feu et ne peut pas empêcher un moteur tiers ou une extension d’accéder à Internet. Certains moteurs tentent de récupérer des poids manquants : ils doivent être installés avant l’essai hors ligne. La génération doit être testée hors ligne avec la configuration choisie.

Les fonctions Audio/Vidéo/3D restent un catalogue avec accès aux outils externes, sans génération par API intégrée dans IA Manager. Le bouton ouvre l’interface déjà lancée ; il ne démarre pas le moteur. Les modèles 3D ne produisent pas automatiquement un squelette ou des animations.

## Validation

6 tests unitaires passent : adresses locales, refus distant avant toute requête, port invalide, proxies et redirections, lecture des checkpoints simulée. Le test de navigation corrigé passe avec les 18 onglets. Les deux interfaces sont instanciées hors écran et vérifiées pour l’activation locale par défaut, le refus distant et l’état occupé. Syntaxe Python vérifiée.

La suite GitHub complète et le build Windows n’ont pas été relancés ici. Aucun moteur lourd ni génération GPU réelle n’a été exécuté.
