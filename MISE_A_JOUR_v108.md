# IA Manager v108 — Sources+ et Termux

## Sources+

Nouvel onglet dans Studio IA local :

- Stability Matrix
- Hugging Face Spaces
- Comfy Registry
- OpenModelDB

La recherche Hugging Face Spaces est intégrée directement.
Les autres sources sont ouvertes dans leur interface officielle afin de ne pas
dépendre de scrapers fragiles.

Stability Matrix complète bien Pinokio pour l'image/vidéo locale : package manager,
installations isolées, modèles partagés et plusieurs WebUI.

## Termux

Nouvel onglet principal **Termux** :

- générateur de commandes pour le workflow ZIP → commit → push ;
- suivi GitHub Actions ;
- état/pull du dépôt ;
- commandes courantes Termux prêtes à copier ;
- configuration SSH téléphone ;
- test de connexion ;
- exécution d'une commande distante après confirmation ;
- port 8022 proposé par défaut pour OpenSSH sous Termux ;
- clé SSH facultative ;
- aucun mot de passe stocké.

Les commandes SSH passent par `QProcess` avec une liste d'arguments et non par un shell local.
