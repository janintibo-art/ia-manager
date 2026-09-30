# IA Manager v169 — installation directe images + Pinokio

Cette version regroupe la correction v168 des modèles d’image et corrige le même blocage dans Pinokio.

## Création d’images
- bouton **Télécharger et installer ce modèle** réellement visible et fonctionnel ;
- téléchargement direct de SDXL/SDXL Turbo dans `ComfyUI/models/checkpoints` ;
- progression, reprise après coupure, détection du dossier ComfyUI et actualisation des checkpoints.

## Pinokio
- détection séparée de **Pinokio**, **npm** et **pterm** ;
- nouveau bouton **Installer pterm automatiquement** ;
- utilisation de la commande officielle `npm install -g pterm` ;
- bouton **Installer / ouvrir Pinokio** vers le site officiel ;
- bouton **Installer Node.js** si npm manque ;
- après installation de pterm, les boutons **Télécharger dans Pinokio** et **Installer / lancer dans Pinokio** deviennent disponibles ;
- messages plus clairs lorsque Pinokio, Node.js ou pterm manque.

## Ordre conseillé
1. Ouvrir la page Pinokio.
2. Si npm est absent, cliquer **Installer Node.js**, terminer l’installation puis relancer IA Manager.
3. Cliquer **Installer pterm automatiquement**.
4. Installer/ouvrir Pinokio si nécessaire.
5. Rechercher une application, puis cliquer **Télécharger dans Pinokio**.
