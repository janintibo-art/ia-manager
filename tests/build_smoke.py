"""Validation rapide de l'interface pour construire l'EXE dans GitHub Actions.

Le test d'intégration étendu reste disponible dans tests/smoke_test.py.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
profile = tempfile.TemporaryDirectory(prefix="ia_manager_build_smoke_")
os.environ["HOME"] = profile.name
os.environ["USERPROFILE"] = profile.name
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.backend import settings  # noqa: E402

settings.set("projects_dir", str(Path(profile.name) / "Projets"))

from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.v100_extension import install_v100  # noqa: E402
from src.ui.v120_extension import install_v120  # noqa: E402
from src.ui.v121_extension import install_v121  # noqa: E402


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    install_v100(window)
    install_v120(window)
    install_v121(window)
    window.show()
    app.processEvents()
    assert window.tabs.count() >= 15, f"Onglets manquants : {window.tabs.count()}"
    for index in range(window.tabs.count()):
        tab = window.tabs.widget(index)
        assert tab is not None, f"Onglet {index} absent"
        # Le benchmark démarre une analyse au premier affichage ; sa construction
        # est déjà vérifiée par MainWindow() sans déclencher ce scan réseau.
        if tab is not window.bench_tab:
            window.tabs.setCurrentIndex(index)
            app.processEvents()
        print("OK :", window.tabs.tabText(index), flush=True)
    window.really_quit = True
    QTimer.singleShot(0, window.close)
    app.processEvents()
    print("BUILD SMOKE TEST OK", flush=True)


if __name__ == "__main__":
    main()
