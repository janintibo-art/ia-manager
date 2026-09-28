# IA Manager v90 — Entraîner / Fusionner

Mise à jour différentielle basée sur le commit b969d4f (v89).
Le ZIP ne contient que les fichiers ajoutés ou modifiés, sous ia_manager/.
Appliquer avec le script habituel de mise à jour puis reconstruire l'EXE avec
le workflow Windows existant. Cette livraison ne publie aucun commit ni release.

## Nouvel atelier

La navigation contient Entraîner / Fusionner, avec quatre pages :
- Entraînement QLoRA via Unsloth : modèle de départ Qwen/Qwen2.5-3B-Instruct,
  contexte 1024, rang 8, batch 1, accumulation 8, 1 à 3 époques.
- Fusion linéaire pondérée via MergeKit, sur CPU/RAM.
- Import d'un modèle complet Safetensors dans Ollama avec quantification Q4_K_M.
- Guide d'utilisation et format des exemples.

Les modèles originaux ne sont pas modifiés. Chaque tâche reçoit un dossier unique.
Les exemples sont copiés dans la tâche et les doublons exacts retirés.
20 % des exemples sont réservés à l'évaluation ; les métriques avant/après sont
sauvegardées. Les exemples trop longs sont refusés au lieu d'être tronqués.
Un adaptateur LoRA est sauvegardé avant l'export du modèle complet.
Les calculs restent dans un processus externe, avec sortie en direct, journal
sur disque et arrêt des sous-processus. La fermeture arrête la tâche.
L'atelier réserve la file locale de l'application ; les autres logiciels et
les tâches non soumises à cette file ne sont pas contrôlés.

## Prérequis Windows

L'EXE ne contient pas les bibliothèques d'entraînement ni les poids des modèles.
Installer Unsloth dans un environnement Python dédié suivant le guide officiel :
https://unsloth.ai/docs/get-started/install/windows-installation

Sélectionner son python.exe dans l'atelier puis lancer le diagnostic CUDA.
Pour la fusion, utiliser un environnement Python contenant MergeKit, suivant :
https://github.com/arcee-ai/mergekit#installation
On peut sélectionner un interpréteur différent pour chaque opération.
Les dépendances de ces outils évoluent ; leur installation et l'entraînement
CUDA n'ont pas pu être testés sur le PC Windows cible.

Avec une RTX 4070, commencer avec le modèle 3B proposé, fermer les modèles
Ollama chargés et les applications GPU gourmandes. Le 14B/30B proposé auparavant
pour la conversation n'est pas le réglage initial de cet atelier d'entraînement.
Les 32 Go de RAM servent aux données, exports et fusions ; ils ne s'ajoutent pas
à la VRAM comme une mémoire GPU équivalente pour QLoRA.
Prévoir plusieurs dizaines de Go sur disque pour les téléchargements et exports.

## Données

Fichier UTF-8 .jsonl, un objet par ligne, par exemple :

    {"instruction":"Comment organiser une sauvegarde ?","input":"Projet personnel","output":"Conserve une copie datée avant chaque modification."}

Au moins 10 exemples distincts ; plusieurs centaines de bons exemples sont
préférables. Le seuil de 10 est un seuil technique, pas une garantie de qualité.
Les réponses devraient être relues et correctes. Ne pas entraîner seulement sur
une répétition des mêmes phrases. Aucun historique n'est collecté automatiquement.
Les exemples ne sont pas téléversés par le runner. Les modèles sont téléchargés
si nécessaire. Les bases soumises à accès restreint nécessitent une authentification
Hugging Face déjà configurée dans l'environnement externe.

## Fusion : limites explicites

Fournir deux modèles Safetensors non quantifiés issus de la même base,
avec configurations et vocabulaires compatibles. Contrôle préalable de la
configuration, du vocabulaire et des tokens spéciaux. Les métadonnées ne permettent
pas de prouver à elles seules une origine commune : l'utilisateur doit la vérifier.
Pas de fusion directe des fichiers GGUF d'Ollama et pas de combinaison arbitraire
de familles ou de tailles différentes. MergeKit peut refuser d'autres incompatibilités.
Une fusion peut dégrader les réponses : comparer avec les originaux.

## Import Ollama

Après succès, le dossier model est proposé dans la page Ollama. Donner un nouveau
nom pour conserver l'ancienne version. Un nom existant sera remplacé après confirmation.
L'import dépend des architectures prises en charge par la version locale d'Ollama.
Si refusé, une conversion GGUF externe est nécessaire ; cette conversion n'est pas
automatisée par cette version. Le modèle importé peut ensuite être sélectionné
avec les autres modèles locaux d'IA Manager.

## Validation

- 72 tests unitaires passent, dont validation JSONL, génération des tâches,
  contrôle d'import, navigation et cycle réel de sous-processus Qt.
- Les 16 onglets sont construits et ouverts avec succès en mode offscreen.
  Détection des interfaces réseau simulée uniquement pour ce test : permission
  réseau système indisponible dans l'environnement de validation.
- Vérification visuelle du nouvel onglet et compilation Python réussies.
- Pas d'exécution réelle Unsloth/MergeKit, d'entraînement NVIDIA, d'import Ollama
  ou de compilation EXE Windows dans cette session. Ces chemins restent à valider
  sur le poste cible. Aucune promesse de vitesse ou de gain de qualité.
- Pas de reprise automatique des entraînements interrompus dans cette version.

Sources techniques :
https://unsloth.ai/docs/get-started/fine-tuning-llms-guide.md
https://github.com/arcee-ai/mergekit
https://github.com/ollama/ollama/blob/main/docs/import.mdx
