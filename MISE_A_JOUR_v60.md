# v60 — Page publique et téléchargements

La page se trouve dans `docs/`. Elle s’adresse aux visiteurs du dépôt avec un descriptif, une illustration, un guide PC ↔ Android et des boutons de téléchargement directs. Aucun modèle IA ni exécutable volumineux n’est inclus dans ce correctif.

## Publication

1. Transférer le ZIP de mise à jour dans le dépôt avec le script habituel de Termux. La compilation Windows doit continuer à produire un EXE dans la dernière Release stable.
2. Dans GitHub, ouvrir **Settings → Pages → Build and deployment → Source** et sélectionner **GitHub Actions**. Le workflow `Publish project website` déploiera `docs/` ; lancer manuellement ce workflow si Pages ne se lance pas après avoir modifié ce réglage.
3. Le workflow Android modifié compile l’APK et le publie comme `ia_manager_android.apk` dans la publication `android-latest`, marquée version de test. Il publie aussi son empreinte SHA-256. Lors des publications suivantes, il met à jour ce fichier et les notes sans changer l’adresse de téléchargement.
4. Vérifier dans les Actions que les deux workflows réussissent. L’adresse de la page est `https://janintibo-art.github.io/ia-manager/`.

Si le dépôt est privé et le compte ne permet pas GitHub Pages pour ce dépôt, le workflow échouera et il faudra modifier les paramètres du dépôt. La publication de l’APK dépend aussi de la réussite de sa compilation Android. Le bouton APK indiquera « Publication en préparation » tant que le fichier n’existe pas dans la Release.

## Liens

- Windows : `/releases/latest/download/ia_manager.exe` ; généré par le workflow Windows existant.
- Android : `/releases/download/android-latest/ia_manager_android.apk` ; généré par le workflow Android modifié.
- La page interroge publiquement l’API GitHub pour afficher date et taille. Les liens continuent de fonctionner si l’API est inaccessible.

## Vérification locale

HTML, fichiers référencés, JavaScript et structure YAML vérifiés. L’environnement de travail ne dispose pas d’un navigateur compilé pour vérifier visuellement le rendu ou d’un SDK Android pour compiler l’APK. Les workflows et la page seront validés par GitHub Actions après l’envoi au dépôt.
