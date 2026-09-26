"""Onglet GitHub - actions git/gh sur le PC et générateur de commandes Termux"""

import shutil
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from src.backend import github_tools as gt
from src.backend import settings
from src.ui import style
from src.ui.tabs.projects_tab import get_project_manager


class CommandRunner(QObject):
    """Lance une suite de commandes l'une après l'autre et renvoie leur sortie en direct"""

    output = pyqtSignal(str)
    done = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc: Optional[QProcess] = None
        self.steps: List[Dict] = []
        self.cwd = ""
        self.captured = ""
        self._capture = False
        self._buffer = ""

    def busy(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def run(self, steps: List[Dict], cwd: str = "") -> bool:
        if self.busy():
            self.output.emit("\n⏳ Une commande est déjà en cours. Attendez ou cliquez sur Arrêter.\n")
            return False
        self.steps = list(steps)
        self.cwd = cwd
        self.captured = ""
        self._next()
        return True

    def stop(self):
        self.steps.clear()
        if self.busy():
            self.proc.kill()
            self.output.emit("\n⏹ Commande arrêtée.\n")

    def _next(self):
        if not self.steps:
            self.proc = None
            self.done.emit(0)
            return
        step = self.steps.pop(0)
        args = list(step["args"])
        if any("{capture}" in a for a in args):
            if not self.captured or self.captured == "null":
                self.output.emit("Aucune compilation trouvée pour ce dépôt.\n")
                self.steps.clear()
                self.proc = None
                self.done.emit(1)
                return
            args = [a.replace("{capture}", self.captured) for a in args]

        program = step["program"]
        resolved = shutil.which(program) or program
        self._capture = bool(step.get("capture"))
        self._buffer = ""

        proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        env.insert("GH_PROMPT_DISABLED", "1")
        env.insert("GIT_TERMINAL_PROMPT", "0")
        env.insert("GH_PAGER", "")
        env.insert("PAGER", "")
        proc.setProcessEnvironment(env)
        if self.cwd:
            proc.setWorkingDirectory(self.cwd)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read)
        proc.finished.connect(self._finished)
        proc.errorOccurred.connect(self._error)
        self.proc = proc
        shown = " ".join(f'"{a}"' if " " in a else a for a in args)
        self.output.emit(f"\n$ {program} {shown}\n")
        proc.start(resolved, args)

    def _read(self):
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        data = gt.strip_ansi(data)
        if self._capture:
            self._buffer += data
        else:
            self.output.emit(data)

    def _finished(self, code: int, _status):
        if self._capture:
            lines = [ln.strip() for ln in self._buffer.strip().splitlines() if ln.strip()]
            self.captured = lines[-1] if lines else ""
            if self.captured:
                self.output.emit(f"→ n° {self.captured}\n")
        if code != 0:
            self.output.emit(f"\n❌ Terminé avec le code {code}.\n")
            self.steps.clear()
            self.proc = None
            self.done.emit(code)
            return
        self._next()

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.output.emit("\n❌ Impossible de lancer la commande. Le programme est-il installé ?\n")
            self.steps.clear()
            self.proc = None
            self.done.emit(-1)


class GithubTab(QWidget):
    """GitHub facile : boutons pour le PC, commandes prêtes à copier pour Termux"""

    def __init__(self):
        super().__init__()
        self.runner = CommandRunner(self)
        self.runner.output.connect(self.append_output)
        self.runner.done.connect(self.on_done)
        self.command_blocks: List[QWidget] = []
        self.init_ui()
        self.refresh_projects()
        self.refresh_tools()
        self.update_termux()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(10)

        title = QLabel("GitHub")
        title.setObjectName("Title")
        root.addWidget(title)

        top = QHBoxLayout()
        top.addWidget(QLabel("Compte GitHub :"))
        self.owner_edit = QLineEdit(settings.get("github_owner") or "")
        self.owner_edit.setPlaceholderText("votre-pseudo")
        self.owner_edit.setMaximumWidth(260)
        self.owner_edit.editingFinished.connect(self.save_owner)
        self.owner_edit.textChanged.connect(lambda _t: self.update_termux())
        top.addWidget(self.owner_edit)
        top.addSpacing(20)
        top.addWidget(QLabel("Remplir depuis un projet :"))
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(260)
        self.project_combo.activated.connect(self.fill_from_project)
        top.addWidget(self.project_combo, 1)
        root.addLayout(top)

        self.sub = QTabWidget()
        self.sub.setObjectName("SubTabs")
        self.sub.addTab(self.build_pc_tab(), "🖥️  Sur ce PC")
        self.sub.addTab(self.build_termux_tab(), "📱  Termux (téléphone)")
        root.addWidget(self.sub, 1)

    # ---------------------------------------------------------------- PC
    def build_pc_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        tools = QFrame()
        tools.setObjectName("Card")
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(14, 10, 14, 10)
        self.tools_label = QLabel()
        self.tools_label.setWordWrap(True)
        tl.addWidget(self.tools_label, 1)
        self.install_git_btn = QPushButton("Installer Git")
        self.install_git_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://git-scm.com/download/win")))
        tl.addWidget(self.install_git_btn)
        self.install_gh_btn = QPushButton("Installer GitHub CLI")
        self.install_gh_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://cli.github.com")))
        tl.addWidget(self.install_gh_btn)
        login_btn = QPushButton("🔑 Se connecter")
        login_btn.setToolTip("Ouvre une fenêtre de commande pour « gh auth login » (une seule fois)")
        login_btn.clicked.connect(self.login)
        tl.addWidget(login_btn)
        check_btn = QPushButton("🔄")
        check_btn.setToolTip("Vérifier les outils et la connexion")
        check_btn.clicked.connect(self.check_login)
        tl.addWidget(check_btn)
        lay.addWidget(tools)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Dossier du dépôt :"))
        self.folder_edit = QLineEdit(settings.get("github_folder") or "")
        self.folder_edit.setPlaceholderText("Dossier local qui contient le dépôt git")
        self.folder_edit.editingFinished.connect(lambda: settings.set("github_folder", self.folder_edit.text()))
        folder_row.addWidget(self.folder_edit, 1)
        browse = QPushButton("Parcourir")
        browse.clicked.connect(self.browse_folder)
        folder_row.addWidget(browse)
        open_btn = QPushButton("Ouvrir")
        open_btn.clicked.connect(self.open_folder)
        folder_row.addWidget(open_btn)
        lay.addLayout(folder_row)

        grid = QGridLayout()
        grid.setSpacing(8)
        actions = [
            ("📋 État", "status", "Fichiers modifiés et branche"),
            ("⬇️ Récupérer", "pull", "git pull : récupère les changements de GitHub"),
            ("🏗️ Compilations", "runs", "Liste des dernières compilations GitHub Actions"),
            ("👀 Suivre la compilation", "watch", "Suit en direct la dernière compilation"),
            ("🐞 Voir l'erreur", "failed_log", "Journal de la dernière compilation en échec"),
            ("📦 Télécharger la Release", "release", "Télécharge la dernière Release dans le dossier releases/"),
            ("🌐 Ouvrir sur GitHub", "browse", "Ouvre le dépôt dans le navigateur"),
            ("📚 Mes dépôts", "repos", "Liste vos dépôts GitHub"),
        ]
        for i, (label, action, tip) in enumerate(actions):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c, a=action: self.run_action(a))
            grid.addWidget(b, i // 4, i % 4)
        lay.addLayout(grid)

        commit_row = QHBoxLayout()
        self.commit_edit = QLineEdit()
        self.commit_edit.setPlaceholderText("Message de commit (ce qui a changé)")
        self.commit_edit.returnPressed.connect(lambda: self.run_action("commit_push"))
        commit_row.addWidget(self.commit_edit, 1)
        push_btn = QPushButton("⬆️ Commit + Push")
        push_btn.setObjectName("Primary")
        push_btn.clicked.connect(lambda: self.run_action("commit_push"))
        commit_row.addWidget(push_btn)
        lay.addLayout(commit_row)

        clone_row = QHBoxLayout()
        self.clone_edit = QLineEdit()
        self.clone_edit.setPlaceholderText("Dépôt à cloner : propriétaire/depot")
        clone_row.addWidget(self.clone_edit, 1)
        clone_btn = QPushButton("📥 Cloner dans…")
        clone_btn.clicked.connect(self.clone_repo)
        clone_row.addWidget(clone_btn)
        lay.addLayout(clone_row)

        self.console = QPlainTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(5000)
        self.console.setPlaceholderText("Le résultat des commandes s'affiche ici.")
        lay.addWidget(self.console, 1)

        cmd_row = QHBoxLayout()
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("Terminal : tapez une commande (ex. git log --oneline -5) puis Entrée")
        self.cmd_edit.returnPressed.connect(self.run_free_command)
        cmd_row.addWidget(self.cmd_edit, 1)
        run_btn = QPushButton("▶ Exécuter")
        run_btn.clicked.connect(self.run_free_command)
        cmd_row.addWidget(run_btn)
        stop_btn = QPushButton("⏹ Arrêter")
        stop_btn.setObjectName("Danger")
        stop_btn.clicked.connect(self.runner.stop)
        cmd_row.addWidget(stop_btn)
        clear_btn = QPushButton("Effacer")
        clear_btn.clicked.connect(self.console.clear)
        cmd_row.addWidget(clear_btn)
        lay.addLayout(cmd_row)
        return w

    # ------------------------------------------------------------ Termux
    def build_termux_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        hint = QLabel("Choisissez une action : les commandes sont prêtes, une par bloc. "
                      "Copiez-les une par une dans Termux, dans l'ordre.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        form.setVerticalSpacing(8)
        self.t_local = QLineEdit()
        self.t_local.setPlaceholderText("mon_projet")
        form.addRow("Dossier (tiret bas) :", self.t_local)
        self.t_repo_label = QLabel()
        self.t_repo_label.setObjectName("Muted")
        form.addRow("Dépôt GitHub :", self.t_repo_label)
        self.t_message = QLineEdit()
        self.t_message.setPlaceholderText("Message de commit")
        form.addRow("Message :", self.t_message)
        self.t_run = QLineEdit()
        self.t_run.setPlaceholderText("NUMERO")
        form.addRow("N° compilation :", self.t_run)
        self.t_tag = QLineEdit()
        self.t_tag.setPlaceholderText("v1.0.0")
        form.addRow("Version (tag) :", self.t_tag)
        self.t_zip = QLineEdit("1")
        form.addRow("N° de l'archive :", self.t_zip)
        self.t_script = QLineEdit(settings.get("termux_script") or "~/memo-depot/mise-a-jour.sh")
        self.t_script.editingFinished.connect(lambda: settings.set("termux_script", self.t_script.text()))
        form.addRow("Script de mise à jour :", self.t_script)
        left_lay.addLayout(form)
        for field in (self.t_local, self.t_message, self.t_run, self.t_tag, self.t_zip, self.t_script):
            field.textChanged.connect(lambda _t: self.update_termux())

        self.t_actions = QListWidget()
        self.t_actions.addItems(gt.TERMUX_ACTIONS)
        self.t_actions.setCurrentRow(0)
        self.t_actions.currentRowChanged.connect(lambda _r: self.update_termux())
        left_lay.addWidget(self.t_actions, 1)
        splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("Card")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(16, 14, 16, 14)
        self.t_title = QLabel()
        self.t_title.setObjectName("CardTitle")
        right_lay.addWidget(self.t_title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.t_blocks_host = QWidget()
        self.t_blocks = QVBoxLayout(self.t_blocks_host)
        self.t_blocks.setSpacing(12)
        self.t_blocks.addStretch()
        scroll.setWidget(self.t_blocks_host)
        right_lay.addWidget(scroll, 1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([460, 700])
        lay.addWidget(splitter, 1)
        return w

    # ------------------------------------------------------------ données
    def save_owner(self):
        settings.set("github_owner", self.owner_edit.text().strip())

    def refresh_projects(self):
        pm = get_project_manager()
        self.project_combo.clear()
        self.project_combo.addItem("—", "")
        for p in pm.list_projects():
            self.project_combo.addItem(p["name"], p["id"])

    def fill_from_project(self, _index: int):
        pid = self.project_combo.currentData()
        if not pid:
            return
        meta = get_project_manager().get(pid) or {}
        repo = meta.get("github_repo", "")
        local = meta.get("local_name", "") or (gt.local_from_repo(repo) if repo else "")
        if "/" in repo and not self.owner_edit.text().strip():
            self.owner_edit.setText(repo.split("/")[0])
            self.save_owner()
        if local:
            self.t_local.setText(local)
        if repo:
            self.clone_edit.setText(gt.full_repo(self.owner_edit.text(), repo))
        if meta.get("pc_folder"):
            self.folder_edit.setText(meta["pc_folder"])
            settings.set("github_folder", meta["pc_folder"])
        self.update_termux()

    def refresh_tools(self):
        st = gt.tool_status()
        ok, ko = "✅", "❌"
        self.tools_label.setText(
            f"Git {ok if st['git'] else ko}   ·   GitHub CLI (gh) {ok if st['gh'] else ko}"
            + ("" if st["git"] and st["gh"] else
               "   —   installez les outils manquants, puis relancez IA Manager.")
        )
        self.install_git_btn.setVisible(not st["git"])
        self.install_gh_btn.setVisible(not st["gh"])

    def check_login(self):
        self.refresh_tools()
        self.runner.run(gt.pc_steps("auth_status"))

    def login(self):
        if not gt.tool_status()["gh"]:
            QMessageBox.information(self, "GitHub CLI manquant",
                                    "Installez d'abord GitHub CLI (bouton « Installer GitHub CLI »).")
            return
        if gt.is_windows():
            QProcess.startDetached("cmd", ["/c", "start", "cmd", "/k",
                                           "gh auth login && gh auth setup-git"])
            self.append_output("\n🔑 Une fenêtre s'est ouverte : suivez les instructions pour vous "
                               "connecter, puis cliquez sur 🔄.\n")
        else:
            self.append_output("\n🔑 Ouvrez un terminal et tapez : gh auth login && gh auth setup-git\n")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier du dépôt", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            settings.set("github_folder", folder)

    def open_folder(self):
        if self.folder_edit.text().strip():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder_edit.text().strip()))

    # ------------------------------------------------------------ actions PC
    def append_output(self, text: str):
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        self.console.insertPlainText(text)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def on_done(self, code: int):
        if code == 0:
            self.append_output("\n✅ Terminé.\n")

    def run_action(self, action: str):
        folder = self.folder_edit.text().strip()
        if action not in ("repos",) and not folder:
            QMessageBox.information(self, "Dossier manquant",
                                    "Choisissez d'abord le dossier du dépôt (bouton Parcourir).")
            return
        dest = ""
        if action == "release":
            dest = "releases"
        if action == "commit_push" and not self.commit_edit.text().strip():
            QMessageBox.information(self, "Message manquant", "Écrivez un message de commit.")
            return
        steps = gt.pc_steps(action, message=self.commit_edit.text(), dest=dest)
        if self.runner.run(steps, folder) and action == "commit_push":
            self.commit_edit.clear()

    def clone_repo(self):
        repo = gt.full_repo(self.owner_edit.text(), self.clone_edit.text().strip())
        if not repo:
            QMessageBox.information(self, "Dépôt manquant", "Indiquez le dépôt : propriétaire/depot.")
            return
        parent = QFileDialog.getExistingDirectory(self, "Cloner dans quel dossier ?")
        if not parent:
            return
        target = f"{parent}/{gt.local_from_repo(repo)}"
        if self.runner.run(gt.pc_steps("clone", repo=repo, dest=target), parent):
            self.folder_edit.setText(target)
            settings.set("github_folder", target)

    def run_free_command(self):
        command = self.cmd_edit.text().strip()
        if not command:
            return
        program, args = gt.shell_command(command)
        if self.runner.run([{"program": program, "args": args}], self.folder_edit.text().strip()):
            self.cmd_edit.clear()

    # ------------------------------------------------------------ Termux
    def update_termux(self):
        if not hasattr(self, "t_actions"):
            return
        local = self.t_local.text().strip() or "mon_projet"
        owner = self.owner_edit.text().strip()
        self.t_repo_label.setText(gt.full_repo(owner, gt.repo_from_local(local)))
        item = self.t_actions.currentItem()
        action = item.text() if item else gt.TERMUX_ACTIONS[0]
        self.t_title.setText(action)

        for wdg in self.command_blocks:
            self.t_blocks.removeWidget(wdg)
            wdg.deleteLater()
        self.command_blocks = []

        commands = gt.termux_commands(
            action, local, owner, self.t_message.text(), self.t_run.text(),
            self.t_tag.text(), self.t_script.text().strip() or "~/memo-depot/mise-a-jour.sh",
            self.t_zip.text().strip() or "1",
        )
        for i, (explanation, cmd) in enumerate(commands, 1):
            block = QWidget()
            bl = QVBoxLayout(block)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(4)
            exp = QLabel(f"{i}. {explanation}")
            exp.setObjectName("Muted")
            exp.setWordWrap(True)
            bl.addWidget(exp)
            row = QHBoxLayout()
            cmd_label = QLabel(cmd)
            cmd_label.setObjectName("Command")
            cmd_label.setWordWrap(True)
            cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(cmd_label, 1)
            copy_btn = QPushButton("📋 Copier")
            copy_btn.clicked.connect(lambda _c, c=cmd, b=copy_btn: self.copy_command(c, b))
            row.addWidget(copy_btn)
            bl.addLayout(row)
            self.t_blocks.insertWidget(self.t_blocks.count() - 1, block)
            self.command_blocks.append(block)

        if not owner and any("-R " in c or "clone " in c for _e, c in commands):
            warn = QLabel(f"<span style='color:{style.ORANGE}'>⚠️ Indiquez votre compte GitHub en haut "
                          "pour compléter les commandes.</span>")
            warn.setWordWrap(True)
            self.t_blocks.insertWidget(self.t_blocks.count() - 1, warn)
            self.command_blocks.append(warn)

    def copy_command(self, command: str, button: QPushButton):
        QApplication.clipboard().setText(command)
        button.setText("✔ Copié")

        def restore():
            try:
                button.setText("📋 Copier")
            except RuntimeError:
                pass  # le bloc a été reconstruit entre-temps

        QTimer.singleShot(1500, restore)
