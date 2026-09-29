# IA Manager v145 — ErisForge

Nouvel onglet `⚒️ ErisForge`.

## Principe
ErisForge travaille à partir de deux groupes d’instructions :
- comportement cible ;
- comportement de référence.

Il calcule une direction comportementale dans les activations, puis permet :
- de l’atténuer / l’ablater ;
- ou de la renforcer / l’ajouter.

## Fonctions
- environnement Python isolé ;
- ErisForge épinglé au commit `0d9e0de9980d61312cab0d2f0cc10e7cc27828b2` ;
- modèle Hugging Face ou dossier local ;
- deux fichiers texte, un prompt par ligne ;
- maximum d’instructions configurable ;
- batch configurable ;
- calcul de direction séparé de la transformation ;
- plage de couches configurable ;
- intensité 0.0 → 1.0 ;
- seed ;
- suggestion heuristique des couches depuis `config.json` ;
- journal en direct ;
- verrou de ressources locales ;
- historique des transformations ;
- modèle source conservé ;
- export checkpoint Hugging Face complet ;
- envoi direct vers `GGUF → Ollama`.

La direction calculée est sauvegardée séparément et peut être réutilisée.
