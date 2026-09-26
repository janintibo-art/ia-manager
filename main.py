#!/usr/bin/env python3
"""
IA Manager - Application desktop pour gérer les IA locales
"""

import pkgutil  # noqa: F401  requis par PyQt6, a embarquer dans l exe
import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.style import BASE_FONT_PT, STYLESHEET


def main():
    """Point d'entrée principal"""
    (Path.home() / ".ia_manager" / "models").mkdir(parents=True, exist_ok=True)
    (Path.home() / ".ia_manager" / "config").mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", BASE_FONT_PT))
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
