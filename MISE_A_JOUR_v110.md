# IA Manager v110 — Actions adaptées à la recherche universelle

La recherche universelle devient un centre d'actions.

## Selon la source

### Hugging Face GGUF
Bouton **Installer / choisir la version** :
- ouvre l'onglet Recherche existant ;
- sélectionne Hugging Face ;
- lance la recherche sur le modèle ;
- permet ensuite de choisir la quantification et d'installer via Ollama.

### GitHub
Bouton **Voir les fichiers GGUF** :
- ouvre Recherche > GitHub ;
- charge le dépôt ;
- permet d'utiliser le téléchargement/import GGUF déjà présent.

### Civitai
Bouton **Choisir et télécharger le fichier** :
- ouvre Recherche > Civitai ;
- utilise la fiche détaillée et les variantes déjà prises en charge.

### ModelScope
Ouvre le résultat dans la source ModelScope de Recherche.

### Pinokio
Bouton **Télécharger dans Pinokio** :
- utilise `pterm download` ;
- télécharge uniquement ;
- n'exécute pas automatiquement les scripts Pinokio.

### Hugging Face Spaces
Bouton **Cloner ce Space** :
- demande un dossier parent ;
- utilise `git clone --depth 1` ;
- ne lance aucun code du Space après le clone.

## Sécurité

Les installateurs existants sont réutilisés au lieu d'être dupliqués.
Les actions potentiellement exécutables restent séparées des téléchargements.
Aucun script Pinokio ou Space n'est lancé automatiquement.
