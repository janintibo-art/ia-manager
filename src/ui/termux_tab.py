"""Onglet Termux v108."""
from pathlib import Path
import shutil

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QPlainTextEdit, QSpinBox, QFileDialog, QMessageBox, QFormLayout,
    QTabWidget
)

from src.backend import settings
from src.backend import termux_center


class TermuxTab(QWidget):
    def __init__(self):
        super().__init__()
        self.proc = None
        root = QVBoxLayout(self)
        title = QLabel("Termux")
        title.setObjectName("Title")
        root.addWidget(title)
        subtitle = QLabel(
            "Préparez vos commandes Android, copiez-les en un clic ou connectez le PC à Termux par SSH. "
            "Aucune commande distante n'est exécutée sans votre action."
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.commands_page(), "Commandes")
        self.tabs.addTab(self.ssh_page(), "Connexion SSH")
        root.addWidget(self.tabs, 1)

    def commands_page(self):
        page = QWidget()
        root = QVBoxLayout(page)

        form = QFormLayout()
        self.owner = QLineEdit(str(settings.get("github_owner") or "janintibo-art"))
        self.local = QLineEdit("ia_manager")
        self.message = QLineEdit("mise à jour IA Manager")
        self.action = QComboBox()
        self.action.addItem("Mettre à jour : ZIP → commit → push", "update")
        self.action.addItem("Suivre la compilation", "watch")
        self.action.addItem("État du dépôt", "status")
        self.action.addItem("Récupérer les changements", "pull")
        form.addRow("Compte GitHub", self.owner)
        form.addRow("Dossier local Termux", self.local)
        form.addRow("Message commit", self.message)
        form.addRow("Action", self.action)
        root.addLayout(form)

        buttons = QHBoxLayout()
        generate = QPushButton("Générer")
        generate.clicked.connect(self.generate)
        copy_all = QPushButton("Copier toutes les commandes")
        copy_all.clicked.connect(self.copy_all)
        buttons.addWidget(generate); buttons.addWidget(copy_all); buttons.addStretch(1)
        root.addLayout(buttons)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output, 1)

        common = QLabel("Commandes utiles Termux")
        common.setObjectName("Subtitle")
        root.addWidget(common)
        for label, command in termux_center.COMMON:
            row = QHBoxLayout()
            text = QLineEdit(command)
            text.setReadOnly(True)
            copy = QPushButton("Copier")
            copy.clicked.connect(lambda _c=False, t=command: QApplication.clipboard().setText(t))
            row.addWidget(QLabel(label)); row.addWidget(text, 1); row.addWidget(copy)
            root.addLayout(row)

        self.generate()
        return page

    def generate(self):
        settings.set("github_owner", self.owner.text().strip())
        commands = termux_center.workflow_commands(
            self.local.text(), self.owner.text(), self.message.text(), self.action.currentData()
        )
        text = "\n\n".join(command for _label, command in commands)
        self.output.setPlainText(text)

    def copy_all(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def ssh_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        help_text = QLabel(
            "Dans Termux : installez OpenSSH, lancez `sshd`, puis récupérez votre utilisateur avec `whoami` "
            "et l'adresse Wi-Fi avec `ip addr show wlan0`. Le port Termux OpenSSH est généralement 8022."
        )
        help_text.setWordWrap(True)
        root.addWidget(help_text)

        form = QFormLayout()
        self.ssh_host = QLineEdit(str(settings.get("termux_ssh_host") or ""))
        self.ssh_user = QLineEdit(str(settings.get("termux_ssh_user") or ""))
        self.ssh_port = QSpinBox()
        self.ssh_port.setRange(1, 65535)
        self.ssh_port.setValue(int(settings.get("termux_ssh_port") or 8022))
        self.ssh_key = QLineEdit(str(settings.get("termux_ssh_key") or ""))
        keyrow = QHBoxLayout()
        keyrow.addWidget(self.ssh_key)
        choose = QPushButton("Clé…")
        choose.clicked.connect(self.choose_key)
        keyrow.addWidget(choose)
        form.addRow("Adresse téléphone", self.ssh_host)
        form.addRow("Utilisateur Termux", self.ssh_user)
        form.addRow("Port", self.ssh_port)
        form.addRow("Clé SSH facultative", keyrow)
        root.addLayout(form)

        self.remote_command = QLineEdit("pwd")
        root.addWidget(QLabel("Commande à exécuter sur Termux :"))
        root.addWidget(self.remote_command)

        buttons = QHBoxLayout()
        test = QPushButton("Tester la connexion")
        test.clicked.connect(lambda: self.run_ssh("pwd"))
        run = QPushButton("Exécuter la commande")
        run.clicked.connect(self.confirm_and_run)
        stop = QPushButton("Arrêter")
        stop.clicked.connect(self.stop)
        buttons.addWidget(test); buttons.addWidget(run); buttons.addWidget(stop); buttons.addStretch(1)
        root.addLayout(buttons)

        self.ssh_status = QLabel()
        self.ssh_status.setWordWrap(True)
        root.addWidget(self.ssh_status)
        self.ssh_log = QPlainTextEdit()
        self.ssh_log.setReadOnly(True)
        root.addWidget(self.ssh_log, 1)
        return page

    def choose_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une clé SSH privée", str(Path.home()))
        if path:
            self.ssh_key.setText(path)

    def save_ssh(self):
        settings.set("termux_ssh_host", self.ssh_host.text().strip())
        settings.set("termux_ssh_user", self.ssh_user.text().strip())
        settings.set("termux_ssh_port", self.ssh_port.value())
        settings.set("termux_ssh_key", self.ssh_key.text().strip())

    def confirm_and_run(self):
        command = self.remote_command.text().strip()
        if not command:
            return
        reply = QMessageBox.question(
            self, "Exécuter sur Termux",
            "Exécuter cette commande sur votre téléphone via SSH ?\n\n" + command,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.run_ssh(command)

    def run_ssh(self, command):
        if self.proc is not None:
            self.ssh_status.setText("Une commande SSH est déjà en cours.")
            return
        ssh = termux_center.ssh_program()
        if not ssh:
            self.ssh_status.setText("SSH n'est pas installé ou introuvable sur le PC.")
            return
        try:
            args = termux_center.ssh_args(
                self.ssh_host.text(), self.ssh_port.value(), self.ssh_user.text(),
                command, self.ssh_key.text()
            )
        except Exception as exc:
            self.ssh_status.setText(str(exc))
            return
        self.save_ssh()
        p = QProcess(self)
        self.proc = p
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_ssh)
        p.finished.connect(self.ssh_finished)
        p.errorOccurred.connect(lambda _e: self.ssh_status.setText("Erreur SSH : " + p.errorString()))
        self.ssh_log.appendPlainText("$ ssh " + " ".join(args[:-1]) + " " + command)
        self.ssh_status.setText("Connexion SSH…")
        p.start(ssh, args)

    def read_ssh(self):
        if self.proc:
            text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.ssh_log.insertPlainText(text)

    def ssh_finished(self, code, status):
        if not self.proc:
            return
        self.read_ssh()
        self.proc.deleteLater()
        self.proc = None
        self.ssh_status.setText("✅ Commande terminée." if code == 0 else f"❌ SSH terminé avec le code {code}.")

    def stop(self):
        if self.proc:
            self.proc.kill()

    def shutdown(self):
        if self.proc:
            self.proc.kill()
            self.proc.waitForFinished(1000)
            self.proc = None
        self.save_ssh()
