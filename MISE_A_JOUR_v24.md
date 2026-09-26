# IA Manager v24 — confort, documents et atelier local

Base vérifiée : v23 publiée, commit `fcc935d0203b1303aa9367c4fdc9834b24fffa48`. Sa compilation Windows n°23 est réussie. Le ZIP contient uniquement les fichiers nouveaux ou modifiés depuis cette base.

## 1. Arrêt du chat pendant une attente réseau

Le streaming utilise désormais un client HTTP asynchrone annulable. Le bouton Stop est contrôlé toutes les 50 ms pendant les attentes réseau, y compris avant les en-têtes HTTP et entre deux tokens. L'annulation ferme le flux côté application, conserve le texte déjà reçu et affiche l'interruption. La même mécanique est utilisée par le comparateur. Les tâches planifiées utilisent aussi ce transport.

Les demandes de métadonnées Ollama sont asynchrones. La détection matérielle lente n'est pas relancée pendant une génération ; si le matériel n'a pas encore été détecté, Ollama choisit la répartition, sauf réglage manuel exploitable. Les règles existantes reprennent ensuite lorsque la détection est disponible.

Le transport attend toujours une réponse longue lorsque Stop n'est pas demandé. Les 50 ms représentent la fréquence de contrôle, pas une garantie de délai sur toute machine. Fermer une connexion ne garantit pas qu'un fournisseur distant arrête immédiatement son calcul ou sa facturation.

Dépendance ajoutée : `httpx[socks]==0.28.1`, pour le réseau asynchrone et les environnements utilisant un proxy SOCKS. Le backend asynchrone AnyIO est explicitement inclus dans la commande PyInstaller.

## 2. Chargement des pièces jointes en arrière-plan

Le Chat lit désormais les fichiers dans un travailleur, avec le nom et le numéro du fichier en cours. L'interface reste utilisable. Le bouton d'annulation abandonne le lot : ses résultats tardifs ne sont pas ajoutés à la discussion. Une nouvelle discussion invalide aussi le chargement précédent et vide les pièces jointes en attente.

L'envoi est bloqué pendant un chargement actif, pour éviter d'envoyer la question sans ses fichiers. Après annulation, vous pouvez envoyer un message. Si un lecteur PDF est encore en train de terminer son fichier, un nouveau chargement doit attendre sa sortie : on évite ainsi d'empiler des lecteurs lourds.

L'annulation ne tue pas brutalement une bibliothèque en cours d'extraction ; elle ignore ses résultats et empêche la suite du lot. Les limites de taille introduites en v23 restent actives. Les images du presse-papiers gardent leur traitement existant.

## 3. Mémoire documentaire par projet

Ouvrir **Espace de travail → Mémoire documentaire** :

1. Sélectionner un projet existant, créé dans l'onglet Projets.
2. Ajouter ses documents texte, PDF, Word ou archives compatibles.
3. Dans le Chat, sélectionner ce même projet et cocher **Documents du projet**.
4. Poser une question contenant les termes recherchés.

L'indexation est locale dans `memoire.sqlite3`, à l'intérieur du dossier du projet. Elle découpe le texte en passages avec un léger recouvrement. La recherche ignore les accents, classe les passages selon les mots-clés et transmet au maximum quatre extraits. Les références `[D1]`, `[D2]`, etc. et les noms des passages transmis sont conservés dans la réponse sauvegardée. Leur affichage prouve quels extraits ont été transmis, pas que chaque phrase de l'IA est exacte.

Cette première version utilise les mots-clés, sans embeddings et sans téléchargement supplémentaire de modèle. Elle n'effectue pas d'OCR : les PDF purement scannés peuvent ne fournir aucun texte. Elle garde au maximum 120 000 caractères par document et 100 documents par projet. Un fichier de même nom remplace sa version indexée ; les fichiers originaux ne sont ni modifiés ni supprimés. Retirer un document ne supprime que son index. Les anciens messages contenant déjà des extraits restent dans l'historique.

Si le Chat utilise un fournisseur distant, les passages sélectionnés lui sont envoyés, comme indiqué dans l'interface. L'index lui-même reste local. Sans projet sélectionné ou sans passage pertinent, aucun extrait documentaire n'est ajouté.

## 4. Profils de travail

**Espace de travail → Profils de travail** propose trois points de départ : Développement, Rédaction et Recherche. Un profil réunit : modèle, consignes, recherche web, mode code et réglages Ollama (mode, contexte, température).

Choisir un modèle disponible dans la liste ou renseigner sa référence, modifier le profil, puis **Enregistrer** et **Appliquer au chat**. Un modèle absent est signalé ; une génération ou recherche en cours empêche le changement. Le profil actif est indiqué dans le Chat. Un nom différent crée un nouveau profil ; enregistrer sous un nom existant le remplace. Le bouton Supprimer retire le profil sélectionné.

Les consignes et options d'outils fonctionnent avec tous les fournisseurs. Les réglages de génération de cette première version concernent Ollama ; les API distantes conservent leurs paramètres actuels. L'application d'un profil remet l'allocation manuelle de couches sur automatique selon son mode. Les profils sont conservés sur disque, mais il faut en sélectionner un après redémarrage pour l'activer dans le Chat.

## 5. Coordination des générations locales et mémoire GPU

**Espace de travail → Mémoire GPU / file** permet de :

- activer ou désactiver la sérialisation des générations locales (activée par défaut) ;
- voir le travail actif et les travaux en attente ;
- actualiser l'utilisation RAM/VRAM et les modèles chargés dans Ollama ;
- décharger explicitement un modèle Ollama sélectionné.

Le chat, le comparateur et les tâches planifiées de cette instance partagent une file FIFO pour Ollama et les fournisseurs configurés sur une adresse de boucle locale. Les API distantes ne sont pas mises dans cette file. Un travail en attente peut être annulé.

Lorsque la sérialisation est active, le serveur Obliteratus lancé par IA Manager réserve le créneau local jusqu'à son arrêt. Si un travail local est déjà actif ou en attente, son lancement est refusé avec un message explicite. Les générations locales attendent tant que l'atelier reste ouvert, même s'il ne calcule pas. Arrêter l'atelier libère le créneau.

Cette coordination évite des chevauchements connus ; elle ne garantit pas qu'un modèle tienne en mémoire. Elle ne contrôle pas les applications externes, les autres instances d'IA Manager, les tests de vitesse ou les serveurs sur une autre machine. Désactiver la sérialisation autorise à nouveau des travaux concurrents. La mémoire n'est pas libérée automatiquement : utiliser le bouton de déchargement avant l'atelier si nécessaire.

Les mesures GPU reprennent les capacités du tableau de bord existant, notamment leurs limites pour les GPU non NVIDIA et les configurations multi-GPU. Aucun essai GPU réel n'a été réalisé ici.

## 6. Carnet d'essais Obliteratus

**Espace de travail → Carnet Obliteratus** conserve le nom d'un essai, les références source/résultat, la méthode et les paramètres, le dossier exporté, la version utilisée, les réponses avant/après et les vitesses mesurées. Le calcul de variation compare les vitesses que vous renseignez. Un essai sélectionné peut être modifié ; **Nouvel essai** crée une autre fiche.

Les champs sont saisis manuellement : ce carnet ne lit pas automatiquement l'interface Gradio. La version est préremplie avec la révision locale configurée et reste modifiable, notamment pour un essai effectué en ligne. Les fichiers de modèles ne sont pas dupliqués par ce carnet : il conserve leurs références et le chemin d'export, pas une sauvegarde des poids.

Après import des deux modèles dans Ollama ou un autre moteur configuré, **Comparer les modèles** prépare les deux colonnes du comparateur. Il reste à saisir une question identique et lancer la comparaison. Le carnet ne quantifie pas et n'importe pas lui-même les exports. Les résultats du comparateur ne sont pas automatiquement recopiés dans la fiche. Limite : 100 essais enregistrés.

## Vérifications

- Base locale comparée à la v23 publiée : identique avant modifications.
- 19 tests automatisés, dont arrêt avant en-têtes, arrêt entre tokens, streaming Anthropic simulé, annulation de pièces jointes, recherche/mise à jour/suppression de documents, file locale, profils et carnet.
- Test de démarrage complet comprenant un échange simulé vérifiant la présence des consignes du profil ET des extraits du projet, ainsi que la préparation du comparateur depuis un essai.
- Rendu visuel des nouveaux écrans et du Chat, syntaxe Python et contrôle du diff.

Ces vérifications ont lieu sur Linux/Python 3.12. La compilation Windows/Python 3.11 de v24 se fera après la mise à jour. Aucun appel à une API payante, téléchargement de modèle ou essai Obliteratus sur GPU n'a été exécuté pendant les tests.

## Principaux fichiers

- `stream_transport.py`, `providers.py`, `workers.py` : réseau annulable, coordination et chargement en arrière-plan.
- `project_memory.py` : index et recherche locale.
- `local_jobs.py` : file FIFO et réservation de l'atelier.
- `workspace_tab.py`, `resources_tab.py`, `trials_tab.py` : documents, profils, ressources et carnet.
- `chat_tab.py`, `comparator_tab.py`, `obliteratus_tab.py`, `main_window.py` : intégration des parcours.
- `requirements.txt`, workflow Windows, tests et documentation : dépendance, packaging et validation.
