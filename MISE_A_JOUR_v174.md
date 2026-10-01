# IA Manager v174 — modèles Chat en 1 clic

Cette version poursuit le chantier « tout installer depuis l'application ».

## Catalogue des modèles Ollama

La fiche d'un modèle Chat possède maintenant un bloc **Installation et lancement**.

États gérés :
- Ollama absent → bouton **Préparer Ollama** ;
- Ollama installé mais arrêté → bouton **Démarrer Ollama** ;
- Ollama lancé et modèle absent → bouton natif **Télécharger** ;
- modèle installé → bouton **Utiliser dans le Chat** ;
- bouton **Vérifier** disponible pour actualiser l'état.

## Installation

Le bouton **Préparer Ollama** ouvre directement le Centre d'installation ajouté en v170/v173 et sélectionne Ollama.
Il n'est donc plus nécessaire de quitter IA Manager pour chercher l'installateur.

## Démarrage

IA Manager tente de lancer `ollama serve` automatiquement, puis vérifie l'API locale.

## Téléchargement du modèle

La v174 conserve le système existant de téléchargement Ollama et sa progression ; elle ajoute seulement la préparation automatique lorsque le moteur manque.

## Suite

Après Chat/Ollama, les prochaines versions appliqueront le même cycle aux modèles :
- Image ;
- Audio/Musique ;
- Vidéo ;
- 3D.
