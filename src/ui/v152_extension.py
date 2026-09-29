"""v152 : petites barres de progression sur les opérations longues."""
import re
from types import MethodType

from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


BAR_STYLE = """
QProgressBar {
    min-height: 8px;
    max-height: 8px;
    border: 0px;
    border-radius: 4px;
    background: rgba(255,255,255,0.08);
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
}
"""


def _insert_near_status(tab, label, bar):
    layout = tab.layout()
    if layout is None:
        return
    status = getattr(tab, "status", None)
    index = layout.indexOf(status) if status is not None else -1
    if index < 0:
        layout.addWidget(label)
        layout.addWidget(bar)
    else:
        layout.insertWidget(index, label)
        layout.insertWidget(index + 1, bar)


def _new_bar(tab, attr, text=""):
    if hasattr(tab, attr):
        return getattr(tab, attr)
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setVisible(False)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(False)
    bar.setStyleSheet(BAR_STYLE)
    bar.setVisible(False)
    setattr(tab, attr, bar)
    setattr(tab, attr + "_label", label)
    _insert_near_status(tab, label, bar)
    return bar


def _show(tab, attr, text, determinate=False, value=0):
    bar = getattr(tab, attr)
    label = getattr(tab, attr + "_label")
    label.setText(text)
    label.setVisible(True)
    if determinate:
        bar.setRange(0, 100)
        bar.setValue(max(0, min(100, int(value))))
    else:
        bar.setRange(0, 0)
    bar.setVisible(True)


def _done(tab, attr, text="Terminé"):
    bar = getattr(tab, attr)
    label = getattr(tab, attr + "_label")
    bar.setRange(0, 100)
    bar.setValue(100)
    label.setText("✅ " + text)
    bar.setVisible(True)
    label.setVisible(True)
    QTimer.singleShot(1200, lambda: bar.setVisible(False))
    QTimer.singleShot(1200, lambda: label.setVisible(False))


def _hide(tab, attr):
    getattr(tab, attr).setVisible(False)
    getattr(tab, attr + "_label").setVisible(False)


def _patch_search(window):
    tab = getattr(window, "search_tab", None)
    if tab is None or getattr(tab, "_v152_progress", False):
        return

    # Le téléchargement possède déjà une vraie progression : on la rend plus lisible.
    if hasattr(tab, "progress"):
        tab.progress.setMinimumHeight(9)
        tab.progress.setMaximumHeight(9)
        tab.progress.setTextVisible(False)
        tab.progress.setStyleSheet(BAR_STYLE)

    # Barre séparée pour recherche / chargement de fiche.
    bar = QProgressBar()
    bar.setRange(0, 0)
    bar.setTextVisible(False)
    bar.setMaximumHeight(7)
    bar.setStyleSheet(BAR_STYLE)
    bar.setVisible(False)
    label = QLabel("Recherche…")
    label.setObjectName("Muted")
    label.setVisible(False)

    layout = tab.layout()
    status = getattr(tab, "status", None)
    idx = layout.indexOf(status) if status is not None else 2
    layout.insertWidget(idx + 1, label)
    layout.insertWidget(idx + 2, bar)
    tab.v152_search_progress = bar
    tab.v152_search_progress_label = label

    old_search = tab.search
    old_results = tab.on_results
    old_selected = tab.on_result_selected
    old_details = tab.on_details

    def search(self):
        label.setText("🔎 Recherche des modèles…")
        label.setVisible(True); bar.setVisible(True)
        old_search()

    def on_results(self, rid, ok, result):
        old_results(rid, ok, result)
        bar.setVisible(False); label.setVisible(False)

    def on_result_selected(self, current, prev):
        if current is not None:
            label.setText("📄 Chargement de la fiche…")
            label.setVisible(True); bar.setVisible(True)
        old_selected(current, prev)

    def on_details(self, rid, repo, ok, result):
        old_details(rid, repo, ok, result)
        bar.setVisible(False); label.setVisible(False)

    tab.search = MethodType(search, tab)
    tab.on_results = MethodType(on_results, tab)
    tab.on_result_selected = MethodType(on_result_selected, tab)
    tab.on_details = MethodType(on_details, tab)

    # Rebranche les signaux directs qui pointaient vers les anciennes méthodes.
    try:
        tab.search_btn.clicked.disconnect()
        tab.search_btn.clicked.connect(tab.search)
        tab.query.returnPressed.disconnect()
        tab.query.returnPressed.connect(tab.search)
        tab.result_list.currentItemChanged.disconnect()
        tab.result_list.currentItemChanged.connect(tab.on_result_selected)
    except Exception:
        pass

    tab._v152_progress = True


def _patch_creative(window):
    tab = getattr(window, "creative_tools_tab", None)
    if tab is None or getattr(tab, "_v152_progress", False):
        return
    _new_bar(tab, "v152_progress", "")

    old_begin = tab.begin
    old_finish = tab.finish
    old_fail = tab.fail_setup
    old_next = tab.next_step

    def begin(self, root, key, hardware, mode, steps, offline):
        labels = {
            "install": "Installation du moteur…",
            "diagnostic": "Diagnostic du moteur…",
            "run": "Démarrage du moteur…",
        }
        _show(self, "v152_progress", labels.get(mode, "Traitement…"))
        return old_begin(root, key, hardware, mode, steps, offline)

    def next_step(self):
        result = old_next()
        try:
            if self.active and self.steps:
                total = max(1, len(self.steps) + 1)
                getattr(self, "v152_progress_label").setText(
                    "⚙ " + (self.status.text() or "Installation en cours…")
                )
        except Exception:
            pass
        return result

    def finish(self, success, message=""):
        result = old_finish(success, message)
        if success:
            _done(self, "v152_progress", "Opération terminée")
        else:
            _hide(self, "v152_progress")
        return result

    def fail_setup(self, exc):
        _hide(self, "v152_progress")
        return old_fail(exc)

    tab.begin = MethodType(begin, tab)
    tab.next_step = MethodType(next_step, tab)
    tab.finish = MethodType(finish, tab)
    tab.fail_setup = MethodType(fail_setup, tab)
    tab._v152_progress = True


def _patch_python_auto(window):
    tab = getattr(window, "creative_tools_tab", None)
    if tab is None or not hasattr(tab, "v151_process"):
        return
    _new_bar(tab, "v152_python_progress", "")

    proc = tab.v151_process
    proc.started.connect(
        lambda: _show(
            tab, "v152_python_progress",
            "⬇ Installation automatique de Python…"
        )
    )
    proc.finished.connect(
        lambda code, status:
        _done(tab, "v152_python_progress", "Python prêt")
        if code == 0 else _hide(tab, "v152_python_progress")
    )


def _patch_image(window):
    tab = getattr(window, "image_studio_tab", None)
    if tab is None or getattr(tab, "_v152_progress", False):
        return
    _new_bar(tab, "v152_progress", "")
    old_busy = tab.set_busy

    def set_busy(self, busy):
        old_busy(busy)
        if busy:
            text = self.status.text().strip() or "Traitement de l’image…"
            _show(self, "v152_progress", "🎨 " + text.replace("…", "").strip() + "…")
        else:
            if getattr(self, "v152_progress").isVisible():
                _done(self, "v152_progress", "Traitement terminé")

    tab.set_busy = MethodType(set_busy, tab)
    tab._v152_progress = True


def _patch_training(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(tab, "_v152_progress", False):
        return
    _new_bar(tab, "v152_progress", "")
    old_start = tab.start_process
    old_finished = tab.finished
    old_shutdown = tab.shutdown

    def start_process(self, program, args, job, importing=False):
        _show(
            self, "v152_progress",
            "🧠 Import Ollama en cours…" if importing else "🧠 Calcul / chargement du modèle en cours…"
        )
        return old_start(program, args, job, importing)

    def finished(self, code, status):
        success = code == 0 and status == QProcess.ExitStatus.NormalExit and not self.cancelled
        result = old_finished(code, status)
        if success:
            _done(self, "v152_progress", "Calcul terminé")
        else:
            _hide(self, "v152_progress")
        return result

    def shutdown(self):
        _hide(self, "v152_progress")
        return old_shutdown()

    tab.start_process = MethodType(start_process, tab)
    tab.finished = MethodType(finished, tab)
    tab.shutdown = MethodType(shutdown, tab)
    tab._v152_progress = True


def _patch_process_tab(tab, attr, default_text):
    if tab is None or getattr(tab, "_v152_generic_progress", False):
        return
    process = getattr(tab, "process", None)
    if process is None:
        return

    _new_bar(tab, attr, "")

    def started():
        text = default_text
        mode = str(getattr(tab, "mode", "") or "")
        if mode:
            pretty = {
                "install": "Installation…",
                "diag": "Diagnostic…",
                "run": "Traitement du modèle…",
                "measure": "Mesure des directions…",
                "ablate": "Intervention sur les poids…",
                "transform": "Transformation du modèle…",
            }.get(mode)
            if pretty:
                text = pretty
        _show(tab, attr, text)

    def finished(code, status):
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            _done(tab, attr, "Étape terminée")
        else:
            _hide(tab, attr)

    process.started.connect(started)
    process.finished.connect(finished)
    tab._v152_generic_progress = True


def _patch_mergekit(window):
    tab = getattr(window, "mergekit_tab", None)
    if tab is None or getattr(tab, "_v152_merge_progress", False):
        return

    # Plusieurs extensions MergeKit créent des QProcess ; on suit tous ceux déjà présents.
    processes = [
        p for p in tab.findChildren(QProcess)
        if p.parent() is tab or p.parent() is not None
    ]
    if not processes:
        return

    _new_bar(tab, "v152_progress", "")
    for proc in processes:
        proc.started.connect(
            lambda t=tab: _show(t, "v152_progress", "🧩 Fusion / conversion en cours…")
        )
        proc.finished.connect(
            lambda code, status, t=tab:
            _done(t, "v152_progress", "Opération MergeKit terminée")
            if code == 0 else _hide(t, "v152_progress")
        )
    tab._v152_merge_progress = True


def install_v152(window):
    if getattr(window, "_v152_progress_bars", False):
        return

    _patch_search(window)
    _patch_creative(window)
    _patch_python_auto(window)
    _patch_image(window)
    _patch_training(window)

    _patch_process_tab(
        getattr(window, "heretic_tab", None),
        "v152_progress",
        "🔥 Heretic travaille…",
    )
    _patch_process_tab(
        getattr(window, "abliteration_lab_tab", None),
        "v152_progress",
        "🧬 Abliteration Lab travaille…",
    )
    _patch_process_tab(
        getattr(window, "erisforge_tab", None),
        "v152_progress",
        "⚒️ ErisForge travaille…",
    )
    _patch_mergekit(window)

    window._v152_progress_bars = True
