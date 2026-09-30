# IA Manager v167 — Correctif visibilité

Deux défauts visibles corrigés.

## 1. Double titre sur toutes les pages
Le grand bandeau supérieur du `StudioShell` répétait le titre déjà présent dans chaque page.

Exemple avant :
- bandeau global : `Catalogue conseillé`
- page : `Catalogue des modèles`

Correction :
- le grand bandeau global est masqué ;
- chaque page conserve son propre titre ;
- gain important de hauteur utile sur tous les écrans ;
- la navigation latérale continue de fonctionner normalement.

## 2. Entraîner / Fusionner : contenu inaccessible
La page était composée de plusieurs blocs ajoutés au-dessus du QTabWidget principal.
Sur certains écrans, le bas de la page sortait de la zone visible.

Correction :
- ajout d'un scroll vertical global autour de toute la page ;
- maintien des scrolls internes des sous-pages ;
- hauteur du QTabWidget bornée pour qu'il ne pousse plus les commandes hors écran ;
- consoles techniques limitées en hauteur ;
- barre de défilement verticale disponible dès que nécessaire.

Aucune fonction d'entraînement ou de fusion n'est supprimée.
