// Les liens directs restent utilisables même si l'API GitHub est indisponible.
const repo = 'janintibo-art/ia-manager';
async function releaseInfo(endpoint, id, expectedName) {
  const label = document.getElementById(id + '-version');
  const button = document.getElementById(id + '-download');
  try {
    const response = await fetch('https://api.github.com/repos/' + repo + '/releases/' + endpoint,
      {signal: AbortSignal.timeout(8000), headers: {Accept: 'application/vnd.github+json'}});
    if (response.status === 404) {
      label.textContent = 'Publication en préparation — consultez les Releases.';
      button.textContent = 'Voir les versions disponibles ↗';
      button.href = 'https://github.com/' + repo + '/releases';
      return;
    }
    if (!response.ok) return;
    const release = await response.json();
    const asset = (release.assets || []).find(item => item.name === expectedName);
    if (!asset) {
      label.textContent = 'Fichier en cours de publication — réessayez dans quelques minutes.';
      button.textContent = 'Consulter la publication ↗';
      button.href = 'https://github.com/' + repo + '/releases';
      return;
    }
    // Utilise seulement les assets de ce dépôt, jamais un lien externe fourni en description.
    if (asset.browser_download_url.startsWith('https://github.com/' + repo + '/releases/download/')) {
      button.href = asset.browser_download_url;
    }
    const date = new Date(asset.updated_at || release.published_at);
    label.textContent = (id === 'android' ? 'Compagnon Android' : release.tag_name) + ' · ' +
      (asset.size / 1048576).toFixed(1).replace('.', ',') + ' Mo' +
      (Number.isNaN(date.getTime()) ? '' : ' · ' + date.toLocaleDateString('fr-FR'));
  } catch (_) { /* Le téléchargement direct ne dépend pas de cette information. */ }
}
releaseInfo('latest', 'windows', 'ia_manager.exe');
releaseInfo('tags/android-latest', 'android', 'ia_manager_android.apk');
