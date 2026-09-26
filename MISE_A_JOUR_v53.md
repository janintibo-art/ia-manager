# IA Manager v53 — Présentation atelier

Cette mise à jour s’applique au projet ayant déjà reçu la v52.

- `src/ui/navigation.py` : navigation latérale défilante, quatre groupes de fonctions, titre et description de chaque écran. Sélection synchronisée avec les liens existants et navigation clavier native.
- `src/ui/main_window.py` : intégration du nouvel habillage ; réglages du thème et du texte en bas de la navigation, avec noms accessibles.
- `src/ui/style.py` : surfaces et en-têtes harmonisés, sélection contrastée, états de focus et de pression, menus et défilement horizontal assortis.
- `tests/test_studio_navigation.py` : vérification des 14 destinations et des ouvertures programmatiques.

Les indices et instances des onglets sont conservés. Aucun changement des moteurs IA, des conversations, des clés ou des données sauvegardées. Le bandeau « HORS LIGNE » statique a été retiré car il ne représentait pas l’état réel de la connexion.

Validation : compilation syntaxique Python ; navigation testée hors écran avec PyQt6 ; rendus du composant inspectés en clair et sombre ; vérifications aux tailles 10, 13 et 20. Les rendus de contrôle utilisent des pages de démonstration. L’archive v52 est partielle : le démarrage de toute l’application et l’EXE Windows ne peuvent pas être validés avec ces seuls fichiers. Le workflow GitHub existant effectue ces contrôles sur le dépôt complet.
