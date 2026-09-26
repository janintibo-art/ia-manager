"""Aperçu des différences avant toute écriture dans le dépôt."""
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout


class ChangeReviewDialog(QDialog):
    def __init__(self, review, parent=None):
        super().__init__(parent)
        self.publish = False
        self.setWindowTitle("Vérifier les fichiers proposés")
        self.resize(900, 650)
        root = QVBoxLayout(self)
        files = review["entries"]
        summary = QLabel(f"{len(files)} fichier(s) modifié(s) dans {review['root']}\n"
                         "Une sauvegarde sera créée avant l'écriture. Les lignes − sont retirées, les lignes + ajoutées.")
        summary.setWordWrap(True)
        root.addWidget(summary)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        text = "\n\n".join(f"{'NOUVEAU' if e['before'] is None else 'MODIFIÉ'} : {e['name']}\n{e['diff']}" for e in files)
        # Limite d'affichage explicite ; aucun fichier n'est écrit avant acceptation.
        complete = len(text) <= 400_000
        if not complete:
            text = text[:400_000] + "\n\nAPERÇU TRONQUÉ : ce lot est trop long. Annulez et demandez un lot plus petit."
        self.preview.setPlainText(text)
        root.addWidget(self.preview)
        note = QLabel("L'envoi GitHub porte sur ces fichiers entiers, y compris leurs modifications locales antérieures. "
                      "Les autres fichiers déjà modifiés ou indexés ne sont pas ajoutés à ce commit.")
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        local = QPushButton("Appliquer localement")
        local.clicked.connect(self.accept)
        publish = QPushButton("Appliquer et envoyer sur GitHub")
        publish.clicked.connect(self.accept_publish)
        local.setEnabled(bool(files) and complete)
        publish.setEnabled(bool(files) and complete)
        for button in (cancel, local, publish):
            buttons.addWidget(button)
        root.addLayout(buttons)

    def accept_publish(self):
        self.publish = True
        self.accept()
