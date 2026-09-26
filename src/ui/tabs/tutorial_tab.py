"""Guide intégré, consultable sans réseau."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget


GUIDE = """
<h1>📘 Bien utiliser IA Manager</h1>
<p>Ce guide résume les fonctions principales et les petits réflexes utiles. Il reste disponible sans Internet.</p>
<h2>1. Premier démarrage</h2>
<ol><li>Ouvrez <b>Analyse</b> pour connaître votre RAM, votre VRAM et les modèles adaptés.</li>
<li>Installez et lancez <b>Ollama</b> sur l'ordinateur qui héberge les modèles locaux.</li>
<li>Commencez par un petit modèle 3B ou 7B avant de passer à un modèle plus lourd.</li></ol>
<h2>2. Trouver un modèle</h2>
<p><b>Recherche</b> propose Hugging Face, GitHub, ModelScope et Civitai.</p>
<ul><li>GGUF : installable dans Ollama.</li><li>Safetensors, LoRA, VAE : destinés aux outils image.</li>
<li>Utilisez les favoris, le filtre « Favoris uniquement » et l'export JSON.</li>
<li>La fiche affiche la taille : gardez environ 20 % de mémoire libre.</li></ul>
<h2>3. Installer sans se tromper</h2>
<p>Pour un GGUF, choisissez la version conseillée puis téléchargez-la. Un téléchargement GitHub peut être annulé et repris. Les fichiers image Civitai vont dans un cache séparé et ne sont pas envoyés à Ollama.</p>
<h2>4. Chat et profils</h2>
<ul><li><b>Architecte Code</b> : diagnostic, corrections et fichiers complets.</li>
<li><b>Directeur Artistique Image</b> : prompts, cohérence de série et contraintes d'assets.</li>
<li>Pour une réponse plus stable, réduisez la température ; pour des idées variées, augmentez-la.</li>
<li>Quand la jauge de contexte devient orange ou rouge, créez une nouvelle discussion ou réduisez l'historique.</li></ul>
<h2>5. Projets et mémoire</h2>
<p>Dans <b>Projets</b>, sauvegardez les discussions. Dans <b>Espace de travail → Mémoire documentaire</b>, ajoutez vos documents et recherchez un passage avant de l'envoyer au chat.</p>
<h2>6. Performance et mémoire</h2>
<ul><li>Un seul gros modèle chargé à la fois est souvent plus rapide.</li><li>Utilisez <b>Rafraîchir les caches IA</b> après une modification externe.</li>
<li>Déchargez un modèle dans la page Mémoire GPU avant d'en charger un autre.</li><li>Nettoyez régulièrement les téléchargements interrompus.</li></ul>
<h2>7. Confidentialité</h2>
<p>Le <b>mode hors ligne</b> bloque les fournisseurs distants et le web, tout en laissant les services locaux. Les diagnostics, sauvegardes et favoris n'exportent pas les clés API.</p>
<h2>8. Dépannage rapide</h2>
<ul><li><b>Ollama absent</b> : vérifiez qu'il est lancé et que le modèle apparaît dans Modèles.</li>
<li><b>Modèle trop lent</b> : choisissez une quantification plus petite ou déchargez les autres modèles.</li>
<li><b>Recherche refusée</b> : vérifiez le mode hors ligne et les jetons facultatifs dans Connexions.</li>
<li><b>Erreur après mise à jour</b> : exportez un diagnostic sans secrets et consultez le journal GitHub Actions.</li></ul>
<h2>Conseil général</h2><p>Testez d'abord avec une petite consigne, vérifiez le résultat, puis augmentez progressivement le contexte, les pièces jointes et la taille du modèle.</p>
"""


class TutorialTab(QWidget):
    open_tab = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        for label, target in (("🔍 Ouvrir Recherche", "search"), ("🔌 Ouvrir Connexions", "connections"),
                              ("💬 Ouvrir Chat", "chat"), ("📚 Ouvrir Espace de travail", "workspace")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, name=target: self.open_tab.emit(name))
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Rechercher un conseil dans le tuto…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_guide)
        layout.addWidget(self.search)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(GUIDE)
        layout.addWidget(self.browser)

    def filter_guide(self, query: str):
        if not query.strip():
            self.browser.setHtml(GUIDE)
            return
        needle = query.casefold()
        chunks = [chunk for chunk in GUIDE.split("<h2>") if needle in chunk.casefold()]
        self.browser.setHtml("<h1>Résultats du tuto</h1>" + "<h2>".join(chunks) if chunks else
                             "<h1>Aucun conseil trouvé</h1><p>Essayez un autre mot-clé.</p>")
