# IA Manager v28 — deux assistants spécialisés

Cette version ajoute deux profils intégrés dans **Espace de travail → Profils de travail**.

**Architecte Code** est réglé pour analyser un projet existant, fournir des fichiers complets et des chemins exacts, vérifier les imports et appels, respecter le workflow téléphone/Termux et distinguer un diagnostic d’une vérification réellement exécutée. Le contexte est réglé à 16 384 tokens et la température à 0,25.

**Directeur Artistique Image** transforme une idée en prompt de production : dimensions, vrai fond transparent, cadrage, lumière, cohérence de série, textures tileables, planches d’animation, rig 3D et noms de fichiers. Il vérifie aussi l’absence de texte parasite et de faux damier. Le contexte est réglé à 12 288 tokens et la température à 0,65.

Les profils utilisent le modèle choisi dans le champ Modèle. Pour l’Architecte Code, choisissez un modèle de code ou de raisonnement ; pour l’image, choisissez un modèle capable de comprendre les images si vous joignez des références. Ces profils rédigent et analysent les consignes ; un moteur de génération d’images séparé reste nécessaire pour produire directement un PNG.

La migration est non destructive : si vos profils existent déjà, ils sont conservés ; les deux nouveaux profils sont ajoutés seulement s’ils manquent. Vous pouvez modifier, dupliquer ou supprimer leurs réglages comme les autres profils.

Vérification : compilation Python et 19 tests ciblés réussis.
