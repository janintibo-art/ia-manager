#!/usr/bin/env python3
"""
IA Manager - Application desktop pour gérer les IA locales
"""

import pkgutil  # noqa: F401  requis par PyQt6, a embarquer dans l exe
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.ui.main_window import MainWindow
from src.ui.style import BASE_FONT_PT, STYLESHEET

LOG_FILE = Path.home() / ".ia_manager" / "erreurs.log"


def handle_exception(exc_type, exc_value, exc_tb):
    """Affiche l'erreur au lieu de fermer brutalement l'application"""
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
    except Exception:
        pass
    sys.__stderr__ and sys.__stderr__.write(text)
    if QApplication.instance() is not None:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("IA Manager - erreur")
        box.setText("Une erreur est survenue, mais l'application continue de fonctionner.\n"
                    f"Détails enregistrés dans : {LOG_FILE}")
        box.setDetailedText(text)
        box.exec()


def main():
    """Point d'entrée principal"""
    (Path.home() / ".ia_manager" / "models").mkdir(parents=True, exist_ok=True)
    (Path.home() / ".ia_manager" / "config").mkdir(parents=True, exist_ok=True)

    sys.excepthook = handle_exception

    app = QApplication(sys.argv)
    app.setApplicationName("IA Manager")
    # La fenêtre peut être réduite près de l'horloge (tâches planifiées) : on quitte explicitement
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", BASE_FONT_PT))
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
