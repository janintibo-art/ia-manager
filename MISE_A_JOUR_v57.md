# IA Manager v57 — le PC devient serveur pour Android

Mise à jour légère pour la v56 existante, dans le même dépôt.

- Nouvel onglet PC « Téléphone » : adresse réseau, port, code d'accès, démarrage/arrêt.
- Serveur Python intégré à l'application PC : pas de script à lancer séparément.
- Client Android natif dans android/ : connexion, modèles, chat progressif, arrêt et historique local.
- Nouveau workflow GitHub Actions « Build Android APK » indépendant du workflow Windows.
- Les modèles restent sur le PC. Ollama et les serveurs OpenAI compatibles locaux sont disponibles.

Après mise à jour, compiler le nouvel EXE et l'APK via GitHub Actions. Le fichier fourni ici est
une archive de sources modifiées, pas un APK. Le guide détaillé est dans android/README.md.

Première version prévue pour le réseau local de confiance en HTTP avec code d'accès.
Le PC doit rester allumé. Les projets/conversations du PC ne sont pas synchronisés.

Tests : serveur HTTP, authentification, streaming, annulation, limites, disponibilité locale,
interface Qt et navigation. Syntaxe Java/XML vérifiée. La compilation Android et le test physique
Windows/Android sont à effectuer via GitHub et sur les appareils.
