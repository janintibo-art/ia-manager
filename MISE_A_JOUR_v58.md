# v58 — correction de la préparation du SDK Android

Le journal GitHub indique « Failed to find package tools » dans setup-android@v3.
Cette action demande par défaut un ancien paquet SDK qui n’est plus disponible.
Le workflow définit désormais explicitement packages: platform-tools.
Les étapes suivantes installent toujours Android 35 et les Build Tools 34.0.0.

Fichier modifié : .github/workflows/android.yml.
Appliquer après v57. Le prochain push relance Android et Windows.
L’APK sera dans l’artefact ia_manager_android_v58 si la compilation réussit.
Le code et le numéro de version de l’application restent ceux de v57.

Validation : YAML lu et paramètre de paquet contrôlé ; compilation GitHub non exécutée ici.
Le blocage identifié intervient avant la compilation : son résultat reste à vérifier.

Référence : https://github.com/android-actions/setup-android
