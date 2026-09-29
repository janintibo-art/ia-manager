#!/usr/bin/env python3
import pkgutil
import sys, traceback
from datetime import datetime
from pathlib import Path
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.backend import settings, storage
from src.ui import style
from src.ui.branding import asset
from src.ui.main_window import MainWindow
from src.ui.v100_extension import install_v100
from src.ui.v120_extension import install_v120
from src.ui.v121_extension import install_v121
from src.ui.v126_extension import install_v126
from src.ui.v127_extension import install_v127
from src.ui.v128_extension import install_v128
from src.ui.v129_extension import install_v129
from src.ui.v130_extension import install_v130
from src.ui.v131_extension import install_v131
from src.ui.v132_extension import install_v132
from src.ui.v133_extension import install_v133
from src.ui.v134_extension import install_v134
from src.ui.v135_extension import install_v135
from src.ui.v136_extension import install_v136
from src.ui.v137_extension import install_v137
from src.ui.v138_extension import install_v138
from src.ui.v139_extension import install_v139
from src.ui.v140_extension import install_v140
from src.ui.v141_extension import install_v141
from src.ui.v142_extension import install_v142
from src.ui.v143_extension import install_v143
from src.ui.v144_extension import install_v144
from src.ui.v145_extension import install_v145
from src.ui.v146_extension import install_v146
from src.ui.v147_extension import install_v147
from src.ui.v148_extension import install_v148
from src.ui.v149_extension import install_v149
from src.ui.v150_extension import install_v150
from src.ui.v151_extension import install_v151
from src.ui.v152_extension import install_v152

LOG_FILE = Path.home() / ".ia_manager" / "erreurs.log"

def handle_exception(exc_type, exc_value, exc_tb):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
    except Exception:
        pass
    if QApplication.instance() is not None:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("IA Manager - erreur")
        box.setText("Une erreur est survenue, mais l'application continue de fonctionner.\n"
                    f"Détails enregistrés dans : {LOG_FILE}")
        box.setDetailedText(text)
        box.exec()

def main():
    storage.app_models().mkdir(parents=True, exist_ok=True)
    (Path.home() / ".ia_manager" / "config").mkdir(parents=True, exist_ok=True)
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    app.setApplicationName("IA Manager")
    app.setWindowIcon(QIcon(str(asset("ia_manager_icon.png"))))
    app.setQuitOnLastWindowClosed(False)
    style.apply_theme(settings.get("theme") or "sombre", settings.get("font_size") or 13)
    app.setFont(QFont("Segoe UI", style.BASE_FONT_PT))
    app.setStyleSheet(style.build_stylesheet())
    window = MainWindow()
    install_v100(window); install_v120(window); install_v121(window)
    install_v126(window); install_v127(window); install_v128(window)
    install_v129(window); install_v130(window); install_v131(window)
    install_v132(window); install_v133(window); install_v134(window)
    install_v135(window); install_v136(window); install_v137(window)
    install_v138(window); install_v139(window); install_v140(window)
    install_v141(window); install_v142(window); install_v143(window)
    install_v144(window); install_v145(window); install_v146(window)
    install_v147(window); install_v148(window); install_v149(window)
    install_v150(window); install_v151(window); install_v152(window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
