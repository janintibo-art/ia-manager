# v61 — Correction build Windows et activation du site

## Build Windows

Le test v59 comparait littéralement l'adresse du checkpoint. Sur le runner Windows, `Path.resolve()` peut remplacer le nom court d'un dossier temporaire (par exemple `RUNNER~1`) par son nom long : les deux chemins désignent le même dossier, mais leurs chaînes diffèrent. Le test compare désormais les fichiers réels avec `samefile()`. Il ne modifie pas le mécanisme de conversion ni l'application.

Après la mise à jour, vérifier que **Build Windows EXE** devient vert et produit la Release Windows.

## Publication GitHub Pages

Le journal v60 affiche `Get Pages site failed ... Not Found` lors de l'étape `actions/configure-pages@v5` : aucun site Pages n'est activé pour le dépôt. Le workflow fourni en v60 attend l'activation initiale.

Dans le dépôt GitHub : **Settings → Pages → Build and deployment → Source → GitHub Actions**. Une fois enregistré, dans **Actions → Publish project website**, relancer le workflow avec **Re-run jobs** ou **Run workflow**. L'adresse attendue après un résultat vert est `https://janintibo-art.github.io/ia-manager/`.

L'option `enablement: true` de configure-pages requiert un jeton autre que `GITHUB_TOKEN` avec les droits d'administration Pages ; le réglage ponctuel dans GitHub convient sans ajouter de secret au dépôt.

## Vérification

Le test ciblé passe sous Linux avec les fichiers v59 superposés. La compilation Windows et le déploiement Pages nécessitent l'exécution de GitHub Actions après installation de cette mise à jour et activation de Pages.
