"""Extension v131 : français / anglais pour l'atelier Obliteratus intégré."""
from types import MethodType

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout

from src.backend import settings


FR_LOG_REPLACEMENTS = (
    ("Loading model", "Chargement du modèle"),
    ("Loading tokenizer", "Chargement du tokenizer"),
    ("Loading checkpoint", "Chargement du checkpoint"),
    ("Collecting activations", "Collecte des activations"),
    ("Probing", "Analyse des activations"),
    ("Distilling", "Extraction des directions"),
    ("Extracting refusal directions", "Extraction des directions de refus"),
    ("Applying projection", "Application de la projection"),
    ("Refinement pass", "Passe de raffinement"),
    ("Verifying", "Vérification"),
    ("Verification", "Vérification"),
    ("Saving checkpoint", "Enregistrement du checkpoint"),
    ("Saving model", "Enregistrement du modèle"),
    ("Model saved", "Modèle enregistré"),
    ("Checkpoint saved", "Checkpoint enregistré"),
    ("Completed", "Terminé"),
    ("Finished", "Terminé"),
    ("Downloading", "Téléchargement"),
    ("Using device", "Périphérique utilisé"),
    ("GPU memory", "Mémoire GPU"),
    ("Refusal rate", "Taux de refus"),
    ("Perplexity", "Perplexité"),
    ("Coherence", "Cohérence"),
    ("Error:", "Erreur :"),
    ("Warning:", "Avertissement :"),
)


def _translate_log(text: str, language: str) -> str:
    if language != "fr":
        return text
    result = text
    for source, target in FR_LOG_REPLACEMENTS:
        result = result.replace(source, target)
    return result


def install_v131(window):
    tab = getattr(window, "obliteratus_tab", None)
    if tab is None or getattr(window, "_v131_obliteratus", False):
        return

    group = QGroupBox("Langue / Language")
    layout = QVBoxLayout(group)

    row = QHBoxLayout()
    tab.v131_language_label = QLabel("Langue de l’atelier")
    row.addWidget(tab.v131_language_label)
    tab.v131_language = QComboBox()
    tab.v131_language.addItem("🇫🇷 Français", "fr")
    tab.v131_language.addItem("🇬🇧 English", "en")
    row.addWidget(tab.v131_language, 1)
    layout.addLayout(row)

    tab.v131_hint = QLabel()
    tab.v131_hint.setWordWrap(True)
    layout.addWidget(tab.v131_hint)

    tab.layout().insertWidget(2, group)

    def v131_apply_language(self):
        lang = self.v131_language.currentData() or "fr"
        settings.set("obliteratus_language", lang)

        if lang == "fr":
            self.v131_language_label.setText("Langue de l’atelier")
            self.v131_hint.setText(
                "L’interface Obliteratus intégrée est affichée en français. "
                "Les messages techniques courants du moteur sont également traduits dans le journal."
            )
            if hasattr(self, "v126_run"):
                self.v126_run.setText("▶ Lancer dans IA Manager")
                self.v126_stop.setText("■ Arrêter")
            if hasattr(self, "v127_prepare"):
                self.v127_prepare.setText("⬇ Préparer / télécharger la source HF")
                self.v127_open.setText("📁 Ouvrir la source")
            if hasattr(self, "v128_compare"):
                self.v128_compare.setText("⚖️ Comparer les deux modèles")
                self.v128_to_chat_before.setText("💬 Ouvrir l’original dans Chat")
                self.v128_to_chat_after.setText("💬 Ouvrir la version Obliteratus dans Chat")
            if hasattr(self, "v129_add"):
                self.v129_add.setText("＋ Enregistrer la version actuelle")
                self.v129_save.setText("💾 Enregistrer les modifications")
                self.v129_compare.setText("⚖️ Envoyer au comparatif")
                self.v129_chat.setText("💬 Ouvrir dans Chat")
                self.v129_open.setText("📁 Ouvrir les fichiers")
                self.v129_delete.setText("🗑 Supprimer de la liste")
        else:
            self.v131_language_label.setText("Workshop language")
            self.v131_hint.setText(
                "The integrated Obliteratus interface is displayed in English. "
                "Raw engine terminology is kept in the log."
            )
            if hasattr(self, "v126_run"):
                self.v126_run.setText("▶ Run in IA Manager")
                self.v126_stop.setText("■ Stop")
            if hasattr(self, "v127_prepare"):
                self.v127_prepare.setText("⬇ Prepare / download HF source")
                self.v127_open.setText("📁 Open source")
            if hasattr(self, "v128_compare"):
                self.v128_compare.setText("⚖️ Compare both models")
                self.v128_to_chat_before.setText("💬 Open original in Chat")
                self.v128_to_chat_after.setText("💬 Open Obliteratus version in Chat")
            if hasattr(self, "v129_add"):
                self.v129_add.setText("＋ Save current version")
                self.v129_save.setText("💾 Save changes")
                self.v129_compare.setText("⚖️ Send to comparison")
                self.v129_chat.setText("💬 Open in Chat")
                self.v129_open.setText("📁 Open files")
                self.v129_delete.setText("🗑 Remove from list")

    tab.v131_apply_language = MethodType(v131_apply_language, tab)
    tab.v131_language.currentIndexChanged.connect(tab.v131_apply_language)

    if hasattr(tab, "v126_process"):
        def v126_append_log(self):
            text = bytes(self.v126_process.readAllStandardOutput()).decode(
                "utf-8", errors="replace"
            )
            if not text:
                return
            lang = self.v131_language.currentData() or "fr"
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(_translate_log(text, lang))

        tab.v126_append_log = MethodType(v126_append_log, tab)
        try:
            tab.v126_process.readyReadStandardOutput.disconnect()
        except (TypeError, RuntimeError):
            pass
        tab.v126_process.readyReadStandardOutput.connect(tab.v126_append_log)

    if hasattr(tab, "v127_process"):
        def v127_read_output(self):
            text = bytes(self.v127_process.readAllStandardOutput()).decode(
                "utf-8", errors="replace"
            )
            if not text:
                return
            self.v127_output_buffer += text
            lang = self.v131_language.currentData() or "fr"
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(_translate_log(text, lang))

        tab.v127_read_output = MethodType(v127_read_output, tab)
        try:
            tab.v127_process.readyReadStandardOutput.disconnect()
        except (TypeError, RuntimeError):
            pass
        tab.v127_process.readyReadStandardOutput.connect(tab.v127_read_output)

    saved = str(settings.get("obliteratus_language") or "fr")
    idx = tab.v131_language.findData(saved)
    if idx < 0:
        idx = tab.v131_language.findData("fr")
    tab.v131_language.setCurrentIndex(max(0, idx))
    tab.v131_apply_language()

    window._v131_obliteratus = True
