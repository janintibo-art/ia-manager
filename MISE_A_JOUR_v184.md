# IA Manager v184 — grand check-up final

La v184 nettoie l’interface sans supprimer de fonction.

## Navigation
- correction du bug `CRÉATION` / `CRÉER` ;
- **Audio & Voix avancés** apparaît correctement dans CRÉER ;
- **Vidéo & 3D avancés** apparaît correctement dans CRÉER ;
- **Derniers blocages** reste dans SYSTÈME ;
- suppression des doublons de navigation.

## Mode Simple
Les écrans experts ne surchargent plus le Mode Simple :
- Audio & Voix avancés ;
- Vidéo & 3D avancés ;
- Derniers blocages ;
- Audit installations.

Ils restent disponibles en Mode Avancé.

## Audio · Vidéo · 3D
Les anciens blocs techniques v171/v172 restent utilisés en interne mais sont masqués visuellement.
Les panneaux v176/v177/v178 deviennent le seul parcours visible.
Le bloc générique **Démarrage rapide** est masqué lorsqu’un panneau 1-clic spécifique existe.

## Création d’images
Deux anciens raccourcis devenus redondants sont masqués :
- `Installer ComfyUI` qui ouvrait le site web ;
- `Installer / démarrer les outils locaux`.

Le panneau ComfyUI intégré reste le parcours principal.

## Audit installations
Le bouton **Ouvrir la bonne section** conduit maintenant directement vers :
- Audio & Voix avancés pour Whisper / Kokoro / XTTS ;
- Vidéo & 3D avancés pour CogVideoX / InstantMesh ;
- Derniers blocages pour Stable Audio Open / TRELLIS.

Aucune fonction n’est supprimée.
