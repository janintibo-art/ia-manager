# IA Manager v166 — Grand check-up / consolidation UX

Cette version ne cherche pas à ajouter de nouvelles fonctions.
Elle réduit les doublons visuels et clarifie les pages les plus chargées.

## Doublons / recouvrements identifiés

### Accueil
Avant :
- Tableau de bord
- Que voulez-vous faire ?
- Assistant IA Manager

Décision :
- en Mode Simple, garder surtout `Démarrer` + `Aide intelligente`;
- le Tableau de bord reste disponible en Mode Avancé.

### Modèles
Avant :
- Modèles
- Bibliothèque IA
- Recherche

Décision :
- `Mes modèles` = gestion quotidienne et compatibilité;
- `Trouver un modèle` = recherche externe;
- `Catalogue conseillé` reste disponible en Mode Avancé pour les fiches détaillées.

### Analyse système
Avant :
- Analyse
- Centre de santé
- Profils matériels

Décision :
- `Mon PC` = matériel réel et recommandations;
- `Diagnostic` = état logiciel / ports / ComfyUI / Ollama;
- `Matériel & profils` = simulations et profils de configuration.

### Studio IA
Le Studio IA contient plusieurs fonctions proches de Recherche, Stockage et Outils locaux,
mais ses fonctions Blender / rig / animation / pipeline sont uniques.
Il est renommé `Studio 3D / Blender` et reste surtout un écran expert.

## Pages allégées

### Chat
- ajout d'un bouton `Options avancées`;
- masquage initial en Mode Simple de :
  - Mode projet de code
  - Internet
  - Documents du projet
  - commandes rapides
  - tâches préparées
  - export / reprise
  - profil et contexte
  - réduction / archives
  - restauration de code
- toutes les fonctions restent disponibles en un clic.

### Outils locaux
- ComfyUI Doctor replié au démarrage;
- Import modèles ComfyUI replié au démarrage;
- Journal technique replié au démarrage;
- boutons dédiés pour les afficher.

### Mon PC / Analyse
- bloc `Bien démarrer` masqué car il fait doublon avec l'écran Démarrer et le Centre de santé;
- réglage VRAM / RAM replié derrière un bouton;
- matériel et recommandations restent visibles immédiatement.

## Correctifs Mode Simple
- correction du filtre de navigation qui pouvait réafficher les écrans avancés;
- l'écran `Mode Simple / Avancé` reste toujours accessible;
- noms simplifiés et orientés usage en Mode Simple;
- aucune suppression physique d'onglet.

## Principe
Aucune fonctionnalité n'est supprimée.
La v166 agit principalement sur la présentation, le regroupement et la navigation.
