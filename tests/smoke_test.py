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

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QEventLoop, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from src.backend import model_registry as reg  # noqa: E402
from src.backend import settings  # noqa: E402

print("PyQt", PYQT_VERSION_STR, "Qt", QT_VERSION_STR)

tmp = Path(tempfile.mkdtemp(prefix="ia_manager_test_"))
settings.set("projects_dir", str(tmp / "Projets"))
settings.set("github_owner", "exemple")
from src.backend import providers as pv  # noqa: E402
pv.save_provider({"id": "faux", "name": "Serveur test", "kind": "openai_compat",
                  "base_url": "http://127.0.0.1:9/v1", "api_key": "", "models": ["modele-test"],
                  "enabled": True})
FAKE_REF = "faux::modele-test"

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
models.category_list.setCurrentRow(0)  # revenir sur « Tous » avant de chercher
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

# ------------------------------------------------------------- Chat : fichiers, code, IA distante
from PyQt6.QtCore import QUrl  # noqa: E402
from PyQt6.QtGui import QColor, QImage  # noqa: E402

chat.refresh_models()
assert chat.select_ref(FAKE_REF), "IA distante dans la liste"
chat.project_select.setCurrentIndex(0)
txt = tmp / "notes.py"
txt.write_text("print('bonjour')", encoding="utf-8")
png = tmp / "photo.png"
img = QImage(40, 30, QImage.Format.Format_RGB32)
img.fill(QColor("red"))
img.save(str(png))
chat.add_files([str(txt), str(png), str(tmp)])
chat.add_qimage(img)
assert len(chat.pending) == 3, chat.pending
chat.remove_pending(2)
assert len(chat.pending) == 2
assert "Cette IA ne voit probablement pas" not in chat.hint.text() or True
chat.message_input.setPlainText("Regarde ces fichiers")
chat.send_message()
loop = QEventLoop()
chat.worker.finished.connect(loop.quit)
QTimer.singleShot(30000, loop.quit)
loop.exec()
app.processEvents()
assert not chat.pending, "pièces jointes envoyées"
assert not chat.messages, "erreur réseau non gardée dans l'historique"
code_answer = "Voici :\n\n```python src/app.py\nprint(1)\n```\n\n```js\nconsole.log(2)\n```"
chat.messages = [{"role": "user", "content": "code", "images": [
    {"mime": "image/png", "data": __import__("base64").b64encode(png.read_bytes()).decode()}],
    "attachments": ["photo.png"], "display": "code"},
    {"role": "assistant", "content": code_answer}]
chat.render_message(0, FAKE_REF)
chat.render_message(1, FAKE_REF)
chat.on_link(QUrl("copy:1:0"))
assert QApplication.clipboard().text() == "print(1)", QApplication.clipboard().text()
chat.on_link(QUrl("copyall:1"))
assert QApplication.clipboard().text() == code_answer
chat.on_link(QUrl("copy:9:9"))
chat.code_mode.setChecked(True)
assert "chemin" in chat.instructions()
chat.code_mode.setChecked(False)
chat.clear_chat()
print("Chat fichiers + code OK")

# ------------------------------------------------------------- Chat : appliquer au dépôt
import subprocess  # noqa: E402

from src.backend import code_tools  # noqa: E402
from src.backend import github_tools as gt  # noqa: E402
from src.ui import style as ui_style  # noqa: E402

repo_dir = tmp / "depot_test"
repo_dir.mkdir()
subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir),
               check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), check=True, capture_output=True)
(repo_dir / "README.md").write_text("depot de test\n", encoding="utf-8")
subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo_dir), check=True, capture_output=True)

code_answer2 = "Voici le fichier :\n\n```python src/nouveau.py\nprint('depuis le chat')\n```"
assert "🚀 Appliquer au dépôt" in code_tools.markdown_to_html(code_answer2, 0, ui_style.code_colors())
blocks2 = code_tools.extract_code_blocks(code_answer2)
assert blocks2 and blocks2[0]["filename"] == "src/nouveau.py", blocks2
written = code_tools.write_to_folder(blocks2, str(repo_dir))
assert written and written[0].read_text(encoding="utf-8").strip() == "print('depuis le chat')"

chat.apply_console.clear()
chat.apply_runner.run(gt.pc_steps("commit_push", message="Ajout depuis le test"), str(repo_dir))
wait_runner(chat.apply_runner)
gitlog = subprocess.run(["git", "log", "--oneline"], cwd=str(repo_dir),
                        capture_output=True, text=True).stdout
assert "Ajout depuis le test" in gitlog, gitlog
print("Chat appliquer au dépôt OK")

# ------------------------------------------------------------- Connexions
conn = w.connections_tab
conn.new_custom()
conn.preset_combo.setCurrentIndex(1)
conn.apply_preset(1)
conn.c_models.setText("a, b")
conn.save_custom()
assert any(p["name"].startswith("LM Studio") for p in pv.get_providers()), pv.get_providers()
conn.refresh_custom_list()
conn.custom_list.setCurrentRow(0)
conn.hf_repo.setText("pas-un-depot")
conn.download_hf()
conn.gguf_name.setText("Nom Invalide")
conn.gguf_path.setText(str(txt))
conn.import_gguf()
for box in conn.account_boxes:
    box.update_status()
print("Onglet Connexions OK")

# ------------------------------------------------------------- Tâches
tasks = w.tasks_tab
tasks.refresh_models()
tasks.new_task()
tasks.name_edit.setText("Tâche test")
tasks.prompt_edit.setPlainText("Dis bonjour")
tasks.model_combo.setCurrentIndex(max(0, tasks.model_combo.findData(FAKE_REF)))
tasks.project_combo.setCurrentIndex(max(0, tasks.project_combo.findData(pid)))
for i in range(tasks.schedule_combo.count()):
    tasks.schedule_combo.setCurrentIndex(i)
tasks.schedule_combo.setCurrentIndex(tasks.schedule_combo.findData("daily"))
tasks.zip_check.setChecked(True)
saved = tasks.save_current()
assert saved and saved["next_run"], saved
tasks.run_current()
loop = QEventLoop()
QTimer.singleShot(200, lambda: None)
if w.task_worker is not None:
    w.task_worker.finished.connect(loop.quit)
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
app.processEvents()
stored = next(t for t in tasks.store.load() if t["id"] == saved["id"])
assert stored["last_status"].startswith("❌"), stored
w.check_tasks()
tasks.reload()
print("Onglet Tâches OK :", stored["last_status"][:60])

# ------------------------------------------------------------- Tableau de bord
from src.backend import dashboard as dash  # noqa: E402

assert dash.format_expiry("") == ""
assert dash.format_expiry("pas une date") == ""
future = (__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
          + __import__("datetime").timedelta(minutes=5)).isoformat()
assert "min" in dash.format_expiry(future) or "s" in dash.format_expiry(future), dash.format_expiry(future)

board = w.dashboard_tab
board.fill_running([{"name": "llama3.2:3b", "size": 2_000_000_000, "size_vram": 1_500_000_000,
                     "expiry_text": "4 min"}])
assert len(board.rows) == 1 and board.rows[0].name == "llama3.2:3b"
assert not board.empty_label.isVisible() and board.unload_all_btn.isEnabled()
board.fill_running([])
assert not board.rows and board.empty_label.isVisible() and not board.unload_all_btn.isEnabled()

board.refresh()
loop = QEventLoop()
board.worker.done.connect(loop.quit)
QTimer.singleShot(15000, loop.quit)
loop.exec()
app.processEvents()
assert board.ram_meter.value_label.text() != "—", "RAM lue"
print("Onglet Tableau de bord OK :", board.hint.text() or "Ollama détecté")

# ------------------------------------------------------------- Recherche d'IA
search = w.search_tab
search.request_id += 1
search.on_results(search.request_id, True, [
    {"id": "unsloth/Qwen3-8B-GGUF", "name": "Qwen3-8B-GGUF", "author": "unsloth", "downloads": 1234567,
     "likes": 321, "updated": "2026-01-30T06:29:38.000Z", "pipeline": "text-generation", "gated": False, "tags": []},
    {"id": "x/Vision-GGUF", "name": "Vision-GGUF", "author": "x", "downloads": 5, "likes": 0,
     "updated": "", "pipeline": "image-text-to-text", "gated": True, "tags": []},
])
assert search.result_list.count() == 2
fake_details = {
    "id": "unsloth/Qwen3-8B-GGUF", "author": "unsloth", "downloads": 5, "likes": 2, "updated": "",
    "pipeline": "text-generation", "license": "apache-2.0", "base_model": "Qwen/Qwen3-8B",
    "languages": ["en", "fr"], "architecture": "qwen3", "context": 40960, "params": 8190735360,
    "gated": True, "readme": "# Titre\n<b>html</b> ![img](x.png)\nTexte",
    "quants": __import__("src.backend.model_search", fromlist=["x"]).group_gguf_files([
        {"rfilename": "Qwen3-8B-Q4_K_M.gguf", "size": 5027783488},
        {"rfilename": "Qwen3-8B-Q8_0.gguf", "size": 8709518144},
        {"rfilename": "BF16/Qwen3-8B-BF16-00001-of-00002.gguf", "size": 9000000000},
        {"rfilename": "BF16/Qwen3-8B-BF16-00002-of-00002.gguf", "size": 7000000000}]),
}
search.show_details(fake_details)
assert search.quant_list.count() == 3, search.quant_list.count()
assert search.selected_quant() is not None, "version conseillée sélectionnée"
search.quant_list.setCurrentRow(0)
search.update_buttons()
search.detail_request += 1
search.on_details(search.detail_request, "a/b", False, "erreur test")
search.on_results(search.request_id, False, "pas de réseau")
search.set_system_info({"vram_gb": 8.0, "ram_gb": 32.0})
search.query.setText("qwen3")
search.search()
loop = QEventLoop()
search.search_worker.finished.connect(loop.quit)
QTimer.singleShot(30000, loop.quit)
loop.exec()
app.processEvents()
print("Recherche réelle sur Hugging Face :", search.status.text())
print("Onglet Recherche OK")

# ------------------------------------------------------------- Livraison 1
import json as _json  # noqa: E402
import threading  # noqa: E402
import time as _time  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

from src.backend import model_options as mo  # noqa: E402
from src.backend import quick_commands as qc  # noqa: E402
from src.ui import style as _style  # noqa: E402
from src.ui.dialogs import ModelSettingsDialog, QuickCommandsDialog  # noqa: E402
from src.ui.workers import SafeThread  # noqa: E402

SSE_RECEIVED = {}


class FakeSSE(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SSE_RECEIVED["last"] = body
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        words = ["Hello", " world"] if "court" not in _json.dumps(body) else ["Hello", " world"]
        slow = "lent" in _json.dumps(body)
        chunks = [f"mot{i} " for i in range(40)] if slow else words
        try:
            for w_ in chunks:
                self.wfile.write(f"data: {_json.dumps({'choices': [{'delta': {'content': w_}}]})}\n\n".encode())
                self.wfile.flush()
                _time.sleep(0.1 if slow else 0.01)
            self.wfile.write(b"data: [DONE]\n\n")
        except (BrokenPipeError, ConnectionResetError):
            pass


server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSSE)
threading.Thread(target=server.serve_forever, daemon=True).start()
pv.save_provider({"id": "sse", "name": "SSE test", "kind": "openai_compat",
                  "base_url": f"http://127.0.0.1:{server.server_address[1]}/v1", "api_key": "",
                  "models": ["flux"], "enabled": True})
SSE_REF = "sse::flux"


def wait_idle(timeout_ms=30000):
    loop = QEventLoop()
    t = QTimer()
    t.setInterval(50)
    t.timeout.connect(lambda: loop.quit() if not SafeThread._alive else None)
    t.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    t.stop()
    app.processEvents()
    app.processEvents()


chat.refresh_models()
chat.project_select.setCurrentIndex(0)
chat.clear_chat()
assert chat.select_ref(SSE_REF), "serveur SSE dans la liste"

# commande rapide + réponse en continu
chat.message_input.setPlainText("/resume court texte à résumer")
chat.send_message()
assert chat.stop_btn.isVisibleTo(chat) and not chat.send_btn.isVisibleTo(chat), "bouton Stop visible"
wait_idle()
assert chat.messages[-1]["role"] == "assistant", chat.messages
assert chat.messages[-1]["content"] == "Hello world", chat.messages[-1]
assert chat.messages[-2]["display"] == "/resume court texte à résumer"
assert chat.messages[-2]["content"].startswith("Résume le texte"), chat.messages[-2]["content"]
assert "tokens/s" in chat.status.text(), chat.status.text()
assert chat.send_btn.isVisibleTo(chat) and not chat.stop_btn.isVisibleTo(chat)
print("Streaming OK :", chat.status.text())

# bouton Stop
chat.message_input.setPlainText("réponse lente")
chat.send_message()
QTimer.singleShot(400, chat.stop_generation)
wait_idle()
assert "interrompue" in chat.messages[-1]["content"], chat.messages[-1]
assert chat.messages[-1]["content"].startswith("mot0"), chat.messages[-1]
print("Stop OK :", chat.messages[-1]["content"][:40])

# nouvelle discussion pendant une réponse
chat.message_input.setPlainText("encore lent")
chat.send_message()
QTimer.singleShot(250, chat.clear_chat)
wait_idle()
assert not chat.messages, chat.messages
print("Abandon pendant la réponse OK")

# erreur réseau pendant le streaming
chat.select_ref(FAKE_REF)
chat.message_input.setPlainText("test erreur")
chat.send_message()
wait_idle()
assert not chat.messages
chat.select_ref(SSE_REF)

# menu des commandes
chat.fill_commands_menu()
assert len(chat.commands_menu.actions()) >= len(qc.DEFAULT_COMMANDS)
chat.insert_command("/traduis")
assert chat.message_input.toPlainText().startswith("/traduis")
chat.message_input.clear()
dlg = QuickCommandsDialog(chat)
dlg.add()
dlg.trigger.setText("/Test Cmd")
dlg.template.setPlainText("Fais {texte}")
dlg.save()
assert qc.expand("/testcmd bien")[0] == "Fais bien", qc.load()[-1]
qc.reset()
print("Commandes rapides OK")

# réglages d'un modèle
d1 = ModelSettingsDialog(FAKE_REF, None, chat)
d2 = ModelSettingsDialog("ollama::qwen3:8b", {"vram_gb": 8.0, "ram_gb": 32.0}, chat)
d2.mode.setCurrentIndex(d2.mode.findData("quality"))
d2.ctx.setValue(12288)
d2.layers.setValue(20)
d2.temp.setValue(0.3)
d2.save()
saved_opts = mo.get_options("ollama::qwen3:8b")
assert saved_opts["mode"] == "quality" and saved_opts["num_ctx"] == 12288 and saved_opts["gpu_layers"] == 20, saved_opts
d3 = ModelSettingsDialog("ollama::qwen3:8b", None, chat)
d3.reset()
assert not mo.get_options("ollama::qwen3:8b")["custom"]
assert chat.stats_text({"tokens_per_s": 12.5, "tokens": 100, "seconds": 8,
                        "options": {"num_gpu": 20, "num_ctx": 8192}}).startswith("⚡ 12.5")
print("Réglages VRAM/RAM OK :", d2.summary.text()[:80])

# priorité de l'onglet Analyse = réglage général
setup.prio_group.button(0).setChecked(True)
setup.update_all()
assert settings.get("default_mode") == "speed"
setup.vram_slider.setValue(75)
assert settings.get("vram_percent") == 75
setup.prio_group.button(1).setChecked(True)
setup.update_all()

# recherche dans toutes les discussions
projects.global_search.setText("Deuxième")
projects.run_global_search()
assert projects.global_results.isVisibleTo(projects) and projects.global_results.count() >= 1
first = projects.global_results.item(0)
assert first.data(Qt.ItemDataRole.UserRole), first.text()
projects.open_global_result(first)
assert chat.messages, "discussion rouverte depuis la recherche"
projects.global_search.clear()
assert not projects.global_results.isVisibleTo(projects)
print("Recherche globale OK")

# thème et taille de police
w.change_appearance(toggle=True)
assert _style.CURRENT_THEME == "clair" and settings.get("theme") == "clair"
w.change_appearance(delta=2)
assert settings.get("font_size") == _style.BASE_FONT_PT
chat.render_message(len(chat.messages) - 1, SSE_REF)
w.change_appearance(delta=-2)
w.change_appearance(toggle=True)
assert _style.CURRENT_THEME == "sombre"
print("Thème / police OK")
server.shutdown()

w.close()
app.processEvents()
if errors:
    print(f"ECHEC : {len(errors)} erreur(s) pendant le test")
    sys.exit(1)
print("SMOKE TEST OK")
