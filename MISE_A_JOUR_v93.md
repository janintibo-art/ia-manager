# v93 — Choix visuel du dossier de stockage

Dans Connexions, section Emplacement des modèles et sauvegardes :
1. Cliquer sur Choisir le dossier de stockage.
2. Naviguer dans les disques et dossiers dans l’explorateur, puis valider.
3. Cliquer sur Copier les données et utiliser ce dossier pour appliquer le choix.

Le chemin est affiché en lecture seule : aucune saisie nécessaire. Le sélecteur
part du dossier actuel s’il existe, sinon du dossier personnel. Annuler conserve
le choix précédent. Pendant une copie, le choix d’un autre dossier est désactivé.
La procédure existante de copie, sa validation et la conservation des originaux
sont maintenues. Cette mise à jour ne déplace aucun fichier à elle seule.

Validation : syntaxe Python et interactions Qt (sélection simulée et annulation)
vérifiées. Le dialogue natif Windows n’a pas été exécuté dans cet environnement.

Correctif différentiel à appliquer après les versions précédentes, notamment v92.
