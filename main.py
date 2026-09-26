#!/usr/bin/env python3
"""
IA Manager - Application desktop pour gérer les IA locales
"""

import sys
from pathlib import Path
from src.ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def main():
    """Point d'entrée principal"""
    # Créer les dossiers de configuration s'ils n'existent pas
    models_dir = Path.home() / ".ia_manager" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    config_dir = Path.home() / ".ia_manager" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Lancer l'application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
