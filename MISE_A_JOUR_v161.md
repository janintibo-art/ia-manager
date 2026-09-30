# IA Manager v161 — Gestionnaire de stockage

Nouvel onglet `💽 Stockage`.

Fonctions :
- analyse en arrière-plan des dossiers volumineux ;
- taille et nombre de fichiers par catégorie ;
- modèles / téléchargements IA Manager ;
- modèles Ollama ;
- conversions ;
- archives de chat ;
- configuration IA Manager ;
- installations ComfyUI / AudioCraft / TripoSR / Hunyuan3D ;
- affichage des 50 plus gros fichiers ;
- détection prudente des doublons potentiels par `nom + taille` ;
- détection des fichiers temporaires `.part`, `.tmp`, `.temp`, `.download` ;
- nettoyage limité aux temporaires sûrs ;
- ouverture directe des dossiers.

Migration :
- déplacement des données IA Manager par copie vérifiée ;
- déplacement des modèles Ollama par copie vérifiée ;
- changement de configuration seulement après réussite ;
- aucun ancien dossier n'est supprimé automatiquement ;
- redémarrage d'Ollama demandé après migration de ses modèles.

Sécurité :
- pas de suppression automatique des doublons ;
- pas de suppression automatique des anciens dossiers ;
- les fichiers complets sont conservés.
