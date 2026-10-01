# IA Manager v182 — CogVideoX, InstantMesh et TRELLIS

## CogVideoX-2B
- environnement Python 3.11 isolé ;
- installation Diffusers / Transformers / Torch ;
- téléchargement du modèle officiel `zai-org/CogVideoX-2b` ;
- cache local dédié ;
- passe en **Automatique** dans l’audit.

## InstantMesh
- environnement Python 3.10 isolé ;
- clone du dépôt officiel TencentARC ;
- PyTorch 2.1 / CUDA 12.1 ;
- xformers / Ninja et requirements officiels ;
- préchargement des poids lorsque possible ;
- bouton de démarrage ;
- passe en **Automatique** dans l’audit.

## TRELLIS
TRELLIS reste volontairement **Partiel** :
- clone du dépôt officiel avec sous-modules ;
- diagnostic système / WSL / NVIDIA / CUDA ;
- dossier local préparé ;
- pas de faux statut “Automatique” sous Windows natif.

Le projet officiel privilégie Linux/WSL2 et compile plusieurs extensions CUDA, ce qui rend une installation native Windows moins fiable.
