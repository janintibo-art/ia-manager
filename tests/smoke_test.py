"""Test de démarrage lancé par GitHub avant la compilation.

Ouvre la fenêtre sans affichage, parcourt tous les onglets, toutes les catégories,
toutes les fiches et toutes les priorités. Le moindre plantage fait échouer le build.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.backend import model_registry as reg  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.style import BASE_FONT_PT, STYLESHEET  # noqa: E402

print("PyQt", PYQT_VERSION_STR, "Qt", QT_VERSION_STR)

app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", BASE_FONT_PT))
app.setStyleSheet(STYLESHEET)

w = MainWindow()
w.show()
app.processEvents()
print("Fenetre OK")

# --- Onglet Analyse
setup = w.setup_tab
setup.analyze_system()
print("Analyse :", setup.info)
for i in range(3):
    setup.prio_group.button(i).setChecked(True)
    setup.update_all()
setup.vram_slider.setValue(30)
setup.installed = [reg.MODELS[0]["id"]]
setup.update_recommendations()
print("Onglet Analyse OK")

# --- Faux PC pour tester toutes les branches de recommandation
fake_pcs = [
    {"vram_gb": 0.0, "ram_gb": 8.0},
    {"vram_gb": 4.0, "ram_gb": 16.0},
    {"vram_gb": 8.0, "ram_gb": 32.0},
    {"vram_gb": 24.0, "ram_gb": 64.0},
]
for pc in fake_pcs:
    for key, _label, _desc in [("Rapidité maximale", 0, 0), ("Équilibré", 0, 0), ("Qualité maximale", 0, 0)]:
        reco = reg.recommend(pc, key)
        print(pc, key, {c: (m["id"] if m else None) for c, m in reco.items()})

# --- Onglet Modèles
models = w.models_tab
models.set_system_info(setup.info)
models.installed = [reg.MODELS[0]["id"], "modele-perso:latest"]
for btn in models.chip_group.buttons():
    btn.click()
    app.processEvents()
    for row in range(models.model_list.count()):
        models.model_list.setCurrentRow(row)
    print("Filtre", btn.text(), ":", models.model_list.count(), "modeles")
models.select_model(reg.MODELS[5]["id"])
assert models.current_id == reg.MODELS[5]["id"], "select_model"
w.open_model(reg.MODELS[3]["id"])
print("Onglet Modeles OK")

# --- Onglet Chat
chat = w.chat_tab
chat.refresh_models()
chat.bubble("Vous", "Bonjour <test> & co\nligne 2", "#000", "#fff")
chat.on_answer("llama3.2:3b", "Réponse\nsur deux lignes")
chat.clear_chat()
print("Onglet Chat OK")

w.close()
print("SMOKE TEST OK")
