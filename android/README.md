# IA Manager Mobile — première version Android (v57)

Client Android natif (Android 8 ou plus récent) du serveur intégré à IA Manager PC.
Le PC exécute les modèles. Aucun modèle ni moteur Python n'est installé sur le téléphone.

## Dans le même dépôt

L'archive de mise à jour conserve le dossier racine `ia_manager/`. Après application,
le dépôt possède `android/`, `.github/workflows/android.yml` et les fichiers Python PC.
Le workflow Windows existant reste en place. Cette mise à jour suppose la v56 déjà appliquée.

## Récupérer l'APK avec GitHub

1. Appliquer la mise à jour puis envoyer les modifications dans le dépôt habituel.
2. Ouvrir **Actions → Build Android APK**. Le workflow démarre sur un push main/master
   modifiant Android, ou manuellement avec **Run workflow**.
3. Attendre le résultat vert. Ouvrir l'exécution puis **Artifacts → ia_manager_android_v57**.
4. Télécharger l'archive de compilation et installer `app-debug.apk` sur le téléphone.
   Android peut demander d'autoriser l'installation pour l'application utilisée pour ouvrir le fichier.
5. Récupérer également le nouvel EXE avec le workflow Windows habituel.

Le ZIP fourni contient les sources et le workflow, pas un APK précompilé.
Compilation : JDK 17, Gradle 8.9, Android Gradle Plugin 8.7.3, SDK 35.
Le workflow appelle Gradle installé par l'action officielle ; aucun gradle-wrapper.jar n'est nécessaire.
Dans Android Studio, ouvrir le dossier `android/`, utiliser Gradle 8.9 et JDK 17.

L'APK est signé avec la clé de développement mise en cache par GitHub Actions.
Si ce cache est perdu, une nouvelle clé sera créée et Android pourra demander de désinstaller
l'ancienne application avant l'installation suivante. Cela efface son historique local.
Pour les prochaines versions durables, une clé de signature privée persistante dans les secrets
GitHub permettra de garantir les mises à jour sans désinstallation.

## À distance avec Tailscale

Installer Tailscale sur le PC Windows et le téléphone Android, puis connecter les deux appareils
au même réseau privé Tailscale. Sur le PC, dans **Téléphone**, sélectionner
**Partout · accès privé Tailscale** et démarrer le serveur. Copier l’adresse HTTPS `*.ts.net:8443`
affichée et le code d’accès dans l’application Android. Le PC, IA Manager, Ollama et
Tailscale doivent rester actifs. Aucun port n’est à ouvrir sur la box ; ne pas activer
Tailscale Funnel (publication sur Internet). Sur Android, un autre VPN peut empêcher Tailscale
de fonctionner simultanément. Le code change au redémarrage du serveur.

## Première connexion

1. Mettre PC et téléphone sur le même réseau local (PC Ethernet et téléphone Wi-Fi conviennent).
2. Lancer Ollama avec au moins un modèle installé, ou le serveur local LM Studio/llama.cpp/Jan
   déjà configuré dans **Connexions** sur le PC.
3. Dans **Téléphone**, choisir l'adresse IPv4 Wi-Fi/Ethernet, puis **Démarrer le serveur**.
4. Si Windows affiche une demande de pare-feu, autoriser IA Manager sur le réseau privé.
5. Sur Android, recopier l'adresse affichée (`http://192.168.1.20:8765`, par exemple)
   et le code d'accès. Toucher **Connecter / actualiser les modèles**.
6. Choisir un modèle et envoyer un message. Le premier chargement du modèle peut prendre du temps.

Le code change à chaque démarrage du serveur. Il n'est pas enregistré sur Android.
L'adresse du PC et les derniers échanges sont enregistrés dans le stockage privé de l'application.
Le bouton **Nouveau** efface cet historique après confirmation. Le contexte conserve au maximum
40 messages et environ 70 000 caractères ; les échanges les plus anciens sortent du contexte.
Une réponse interrompue reste affichée temporairement et n'est pas ajoutée à l'historique.

## Fonctionnement de cette v1

- Connexion locale protégée par un code aléatoire, serveur arrêté par défaut.
- Liste des modèles Ollama et des serveurs compatibles OpenAI sur localhost/127.0.0.1/::1.
- Réponses texte progressives et arrêt de la génération.
- Une génération mobile à la fois ; si la sérialisation des travaux locaux est activée sur le PC,
  un travail PC en cours provoque un message invitant à réessayer.
- Pas d'accès mobile aux fichiers, outils d'exécution, API cloud ou réglages du PC.
- Pas encore de synchronisation des projets/chats PC, pièces jointes, accès Internet distant ou QR code.
- Le PC doit rester allumé, sans veille, avec IA Manager et le moteur local en fonctionnement.

Cette version utilise HTTP sur un réseau privé de confiance. Le code contrôle l'accès mais les échanges
ne sont pas chiffrés. Ne pas exposer ce port sur la box. L'application mobile accepte uniquement une
adresse IPv4 privée (192.168.x.x, 10.x.x ou 172.16–31.x.x). L'accès extérieur/TLS est une étape distincte.

## Dépannage

- **Connexion impossible** : serveur PC démarré, adresse correcte, même réseau, réseau Windows privé,
  pare-feu autorisant l'EXE. Un réseau invité peut interdire les échanges entre appareils.
- **Code incorrect** : recopier le nouveau code du PC après un redémarrage du serveur.
- **Aucun modèle** : démarrer Ollama/LM Studio sur le PC et actualiser la liste.
- **PC occupé** : attendre la fin du travail PC ou de l'autre génération mobile.
- **Serveur arrêté** : la fermeture réelle d'IA Manager arrête aussi le serveur.
- **Discussion trop longue** : utiliser Nouveau pour repartir avec un contexte vide.

## API locale

Authentification `Authorization: Bearer <code>` pour chaque requête.
- `GET /v1/models` : modèles locaux et avertissements de disponibilité.
- `POST /v1/chat` : `model`, `request_id`, `messages` (rôles user/assistant).
  Réponse NDJSON : événements start, token, done ou error.
- `POST /v1/cancel` : annulation par `request_id`.

Requêtes limitées à 256 Kio, 64 messages et 100 000 caractères au total. Les appels moteur
sont limités à dix minutes et les réponses à 512 K caractères. Pas de redirection réseau ni de proxy
hérité pour les appels aux moteurs locaux. Les navigateurs envoyant Origin sont refusés.

## Validation effectuée

Tests HTTP réels sur boucle locale : authentification, exclusion des secrets, flux Unicode,
annulation, PC occupé, requêtes invalides, modèle distant interdit et arrêt du serveur.
Test Qt hors écran de l'onglet et navigation. Syntaxe Python/Java/XML vérifiée.
Pas de compilation APK ni de test sur téléphone physique dans l'environnement de préparation.
GitHub Actions compile l'APK et lance Android Lint ; le test PC↔téléphone reste à faire chez vous.
