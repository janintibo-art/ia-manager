# IA Manager v31 — sauvegarde de configuration

L'onglet **Connexions** propose maintenant deux boutons pour déplacer facilement les réglages entre installations.

## Sauvegarder

**Sauvegarder la configuration** crée un fichier JSON avec les réglages, les fournisseurs, les modèles mémorisés et le mode hors ligne. Les clés API et la clé Brave sont volontairement exclues du fichier.

## Restaurer

**Restaurer** vérifie le format avant de modifier les réglages. Une confirmation est demandée. Les clés API déjà présentes sur l'appareil sont conservées lorsqu'elles ne figurent pas dans la sauvegarde.

Cette sauvegarde sert à retrouver rapidement l'organisation de l'application après une réinstallation ou un changement de dossier. Elle ne contient ni conversation, ni document, ni secret.

## Vérification

La compilation syntaxique et les 23 tests ciblés passent localement. La construction Windows complète reste vérifiée par GitHub Actions.
