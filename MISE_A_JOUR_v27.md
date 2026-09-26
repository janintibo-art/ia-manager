# IA Manager v27 — protection du contexte

Cette mise à jour complète la réduction manuelle de l’historique introduite en v26.

Le Chat estime maintenant les tokens à partir du texte envoyé et compare cette estimation à la limite du mode Ollama du modèle. L’indicateur change de couleur quand le contexte atteint 75 %, puis affiche un avertissement à 90 %. Si l’historique dépasse 8 192 tokens avec plusieurs échanges, l’envoi est suspendu et propose de cliquer sur **Réduire l’historique**.

La limite est une estimation : les tokens réels dépendent du tokenizer, des consignes, des images et du fournisseur. Les API distantes peuvent utiliser une limite différente. Une réduction conserve les six derniers messages et ajoute un repère local indiquant qu’un historique précédent a été condensé. Vérifications : 19 tests ciblés réussis et compilation Python contrôlée.
