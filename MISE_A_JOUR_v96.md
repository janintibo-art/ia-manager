# IA Manager v96 — Création d’images

Mise à jour différentielle après la v95. Les modèles eux-mêmes ne sont pas inclus dans ce petit ZIP.

## Ajouts

Nouvel onglet « Création d’images » dans CRÉER, avec fiches, spécialités et accès aux téléchargements officiels :

- SDXL 1.0 : images généralistes, illustrations et décors.
- SDXL Turbo : essais rapides, préréglage 512 × 512 / 4 étapes / guidage 1.
- Animagine XL 4.0 : illustrations anime et personnages.
- FLUX.1 Schnell : fiche disponible ; génération dans son workflow ComfyUI uniquement, pas avec le bouton simplifié.

Connexion ComfyUI, liste des checkpoints installés, description positive et négative, formats carrés 512/768/1024, réglages des étapes et du guidage, aperçu et enregistrement PNG. Les appels réseau s’effectuent en arrière-plan.

## Première utilisation sur le PC

1. Ouvrir « Création d’images », puis « Installer ComfyUI » et installer/lancer ComfyUI.
2. Sélectionner une fiche et ouvrir « Fiche et téléchargement ». Télécharger le checkpoint indiqué dans la fiche depuis les fichiers du dépôt officiel.
3. Mettre ce checkpoint dans le dossier models/checkpoints de ComfyUI (ou un dossier de modèles configuré dans ComfyUI), puis actualiser/redémarrer ComfyUI.
4. Renseigner son adresse dans IA Manager. L’adresse proposée est http://127.0.0.1:8188 ; utiliser le port affiché par votre installation s’il diffère.
5. Cliquer sur « Connecter / actualiser les modèles », puis choisir le checkpoint correspondant à la fiche. La sélection de la fiche règle les paramètres ; elle ne télécharge ni ne sélectionne automatiquement le checkpoint.
6. Décrire l’image et cliquer sur « Générer une image ». Les résultats sont conservés par ComfyUI ; « Enregistrer en PNG » permet d’en choisir une copie avec le sélecteur de fichiers.

SDXL et ses dérivés utilisent le workflow simple intégré (Euler). FLUX demande plusieurs composants et un workflow adapté : utiliser les modèles de workflow de ComfyUI. Le téléchargement et l’installation du moteur et des poids ne sont pas automatisés dans cette version.

Le calcul s’effectue sur le PC exécutant ComfyUI, pas dans Termux. Une carte graphique dédiée est fortement conseillée ; la vitesse et les modèles utilisables dépendent du matériel. Ces modèles ne sont pas ajoutés à la liste du chat Ollama. Un PNG enregistré n’implique pas automatiquement un fond transparent.

En cas d’attente longue, ouvrir ComfyUI pour voir la file et éventuellement interrompre le calcul. Fermer IA Manager n’arrête pas une tâche déjà envoyée à ComfyUI. Le suivi expire après 30 minutes ; consulter ComfyUI avant de relancer. Une erreur réseau peut aussi laisser le calcul en cours côté serveur.

## Validation

Compilation des fichiers Python réussie. Tests du client avec réponses simulées : URL, structure du workflow, liste des checkpoints, retour d’image et erreur d’exécution. Onglet PyQt6 ouvert hors écran : fiches, réglages, activation des boutons, aperçu et PNG vérifiés. Aucun modèle de plusieurs Go ni moteur ComfyUI n’est installé dans l’environnement de test : la génération réelle sur GPU et l’application Windows complète restent à valider sur le PC.

## Sources officielles

- https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- https://huggingface.co/stabilityai/sdxl-turbo
- https://huggingface.co/cagliostrolab/animagine-xl-4.0
- https://huggingface.co/black-forest-labs/FLUX.1-schnell
- https://comfy.org/download
- https://docs.comfy.org/basic-concepts/models
- https://docs.comfy.org/development/comfyui-server/comms_routes
