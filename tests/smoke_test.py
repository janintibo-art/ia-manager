"""Test de démarrage lancé par GitHub avant la compilation.

Ouvre la fenêtre sans affichage et parcourt tous les onglets : analyse, catalogue,
projets (consignes, sauvegardes, classement), chat, GitHub (commandes PC et Termux).
Le moindre plantage fait échouer le build.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

errors = []


def hook(exc_type, exc_value, exc_tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, exc_tb)
    errors.append(exc_value)


sys.excepthook = hook  # une erreur dans un clic doit faire échouer le test

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QEventLoop, QTimer  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from src.backend import model_registry as reg  # noqa: E402
from src.backend import settings  # noqa: E402

print("PyQt", PYQT_VERSION_STR, "Qt", QT_VERSION_STR)

tmp = Path(tempfile.mkdtemp(prefix="ia_manager_test_"))
settings.set("projects_dir", str(tmp / "Projets"))
settings.set("github_owner", "exemple")

from src.ui.main_window import MainWindow  # noqa: E402
from src.ui.style import BASE_FONT_PT, STYLESHEET  # noqa: E402

app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", BASE_FONT_PT))
app.setStyleSheet(STYLESHEET)

w = MainWindow()
w.show()
app.processEvents()
print("Fenetre OK")


def wait_runner(runner, timeout_ms=60000):
    loop = QEventLoop()
    runner.done.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    runner.done.disconnect(loop.quit)


# ------------------------------------------------------------- Analyse
setup = w.setup_tab
setup.analyze_system()
print("Analyse :", setup.info)
for i in range(3):
    setup.prio_group.button(i).setChecked(True)
    setup.update_all()
setup.vram_slider.setValue(30)
setup.installed = [reg.MODELS[0]["id"]]
setup.update_recommendations()
for pc in [{"vram_gb": 0.0, "ram_gb": 8.0}, {"vram_gb": 8.0, "ram_gb": 32.0}, {"vram_gb": 24.0, "ram_gb": 64.0}]:
    for key in ("Rapidité maximale", "Équilibré", "Qualité maximale"):
        reg.recommend(pc, key)
print("Onglet Analyse OK")

# ------------------------------------------------------------- Modèles
models = w.models_tab
models.set_system_info(setup.info)
models.installed = [reg.MODELS[0]["id"], "modele-perso:latest"]
for row in range(models.category_list.count()):
    models.category_list.setCurrentRow(row)
    app.processEvents()
    for r in range(models.model_list.count()):
        models.model_list.setCurrentRow(r)
    print("Categorie", models.category_list.item(row).text(), ":", models.model_list.count())
models.search.setText("mistral")
assert models.model_list.count() > 0, "recherche"
models.search.clear()
w.open_model(reg.MODELS[5]["id"])
assert models.current_id == reg.MODELS[5]["id"], "select_model"
print("Onglet Modeles OK")

# ------------------------------------------------------------- Projets
projects = w.projects_tab
pid = projects.create_project("Mon projet test", "Développement")
pid2 = projects.create_project("Roman été", "Écriture")
projects.reload(select=pid)
assert projects.current_pid == pid
projects.template_combo.setCurrentIndex(1)
projects.insert_template()
projects.save_instructions()
assert projects.pm.get_instructions(pid).strip(), "consignes"
projects.tags_edit.setText("test, #android")
projects.favorite_check.setChecked(True)
projects.repo_edit.setText("exemple/mon-projet")
projects.local_edit.setText("mon_projet")
projects.pc_folder_edit.setText(str(ROOT))
projects.save_settings()
meta = projects.pm.get(pid)
assert meta["tags"] == ["test", "android"] and meta["favorite"], meta
for i in range(projects.sort_combo.count()):
    projects.sort_combo.setCurrentIndex(i)
for i in range(projects.category_filter.count()):
    projects.category_filter.setCurrentIndex(i)
projects.category_filter.setCurrentIndex(0)
for i in range(projects.tag_filter.count()):
    projects.tag_filter.setCurrentIndex(i)
projects.tag_filter.setCurrentIndex(0)
projects.search.setText("roman")
projects.search.clear()
projects.reload(select=pid)
print("Onglet Projets OK")

# ------------------------------------------------------------- Chat + sauvegardes
chat = w.chat_tab
w.on_projects_changed()
w.new_conversation(pid)
assert chat.project_id == pid, "projet actif"
assert "Consignes actives" in chat.hint.text(), chat.hint.text()
chat.messages.append({"role": "user", "content": "Bonjour <test> & co"})
chat.on_answer("llama3.2:3b", "Réponse\nsur deux lignes")
chat.messages.append({"role": "user", "content": "Deuxième question"})
chat.on_answer("llama3.2:3b", "Deuxième réponse")
convs = projects.pm.list_conversations(pid)
assert len(convs) == 1 and convs[0]["count"] == 4, convs
chat.messages.append({"role": "user", "content": "Question sans réponse"})
chat.on_answer("llama3.2:3b", "Erreur Ollama : 500")
assert chat.messages[-1]["role"] == "assistant", "erreur non gardée"

projects.reload(select=pid)
projects.inner_tabs.setCurrentIndex(1)
projects.conv_list.setCurrentRow(0)
projects.export_conversation()
projects.open_selected_conversation()
assert chat.conv_id == convs[0]["id"] and len(chat.messages) == 4, "reprise"
projects.pm.rename_conversation(pid, convs[0]["id"], "Titre renommé")
projects.refresh_conversations()
out = projects.pm.export_project(pid, str(tmp))
assert out.exists()
chat.clear_chat()
chat.project_select.setCurrentIndex(0)
assert chat.project_id is None
projects.pm.delete_project(pid2)
w.on_projects_changed()
projects.reload()
print("Chat + sauvegardes OK")

# ------------------------------------------------------------- GitHub
gh = w.github_tab
gh.refresh_projects()
idx = gh.project_combo.findData(pid)
gh.project_combo.setCurrentIndex(idx)
gh.fill_from_project(idx)
assert gh.t_local.text() == "mon_projet", gh.t_local.text()
for row in range(gh.t_actions.count()):
    gh.t_actions.setCurrentRow(row)
    app.processEvents()
    assert gh.command_blocks, gh.t_actions.item(row).text()
gh.t_actions.setCurrentRow(0)
gh.t_message.setText('Test "message" $HOME')
copy_btn = QPushButton("📋 Copier")
gh.copy_command("gh run watch -R exemple/mon-projet", copy_btn)
assert QApplication.clipboard().text() == "gh run watch -R exemple/mon-projet"
gh.refresh_tools()

gh.folder_edit.setText(str(ROOT))
gh.cmd_edit.setText("git --version")
gh.run_free_command()
wait_runner(gh.runner)
gh.run_action("status")
wait_runner(gh.runner)
console = gh.console.toPlainText()
print(console)
assert "git version" in console, "terminal integre"
print("Onglet GitHub OK")

w.close()
app.processEvents()
if errors:
    print(f"ECHEC : {len(errors)} erreur(s) pendant le test")
    sys.exit(1)
print("SMOKE TEST OK")
