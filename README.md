# IA Manager

**Vos IA, vos idées, votre espace.** IA Manager rassemble sur Windows le chat, les modèles locaux, les projets et les outils d’expérimentation. Son application compagnon Android permet de discuter depuis le téléphone avec les modèles qui tournent sur le PC.

**[Découvrir la page du projet](https://janintibo-art.github.io/ia-manager/)** · [Télécharger pour Windows](https://github.com/janintibo-art/ia-manager/releases/latest/download/ia_manager.exe) · [Télécharger l’APK Android](https://github.com/janintibo-art/ia-manager/releases/download/android-latest/ia_manager_android.apk) · [Signaler un problème](https://github.com/janintibo-art/ia-manager/issues)

## Ce que propose l’application

- **Discuter** avec Ollama, LM Studio, les serveurs compatibles OpenAI ou des fournisseurs API configurés dans Connexions.
- **Organiser** des projets, consignes, discussions et documents ; retrouver l’historique et exporter les échanges en PDF, Word ou Markdown.
- **Explorer** les modèles et les formats GGUF depuis plusieurs catalogues, suivre les téléchargements et enregistrer ses favoris.
- **Expérimenter** avec Obliteratus dans un environnement Python séparé et ajouter des checkpoints convertis en GGUF à Ollama.
- **Retrouver le chat sur Android** grâce à un serveur local à démarrer sur le PC, avec adresse et code d’accès affichés dans l’onglet Téléphone.

L’application compagnon ne charge pas les modèles sur le téléphone : le PC effectue le calcul. Les deux appareils doivent se trouver sur le même réseau local. Le serveur mobile actuel utilise HTTP ; réservez-le à un réseau local de confiance et ne redirigez pas son port sur Internet.

## Installation

### Windows

1. Téléchargez l’EXE dans la [dernière publication Windows](https://github.com/janintibo-art/ia-manager/releases/latest).
2. Lancez IA Manager, puis ouvrez **Connexions** pour configurer le moteur voulu. Pour les modèles locaux, [installez Ollama](https://ollama.com/download/windows) ou un autre moteur compatible et choisissez un modèle adapté à votre matériel.
3. Dans **Chat**, actualisez la liste des IA et sélectionnez votre modèle.

L’EXE n’est pas signé avec un certificat commercial. L’installation locale d’Obliteratus demande Python 3.10+ et télécharge séparément des dépendances volumineuses ; une carte compatible CUDA peut nécessiter PyTorch CUDA dans cet environnement dédié.

### Android

1. Installez l’[APK compagnon](https://github.com/janintibo-art/ia-manager/releases/download/android-latest/ia_manager_android.apk) (Android 8.0 minimum). C’est une version de test à installer manuellement.
2. Sur le PC, ouvrez **Téléphone** et démarrez le serveur.
3. Sur le téléphone, indiquez l’adresse locale et le code affichés par le PC. Laissez le PC et le moteur IA allumés pendant la discussion.

L’APK est signé avec une clé de débogage mise en cache pendant la compilation. Si cette clé change, une réinstallation peut être nécessaire et supprimer l’historique local sur le téléphone.

## Depuis les sources

Pour l’application PC : Python 3.11+, dépendances dans `requirements.txt`, puis `python main.py`. GitHub Actions exécute les tests et compile un EXE PyInstaller. La compilation Android se trouve dans `android/` et utilise Gradle avec Java 17. Les deux compilations sont indépendantes.

La page publique statique se trouve dans [`docs/`](docs/) et se déploie avec le workflow GitHub Pages. [Guide de mise en ligne](MISE_A_JOUR_v60.md).

## Licence et outils tiers

Consultez les licences du dépôt et des outils externes avant toute redistribution. Obliteratus et les modèles obtenus depuis des catalogues conservent leurs propres licences et conditions d’utilisation.
