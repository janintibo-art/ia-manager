"""Serveur mobile local ou accès privé HTTPS par Tailscale Serve."""
import json
import re
import shutil
from pathlib import Path

from PyQt6.QtCore import QProcess, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget)
from src.backend.mobile_server import MobileServer, lan_addresses


class MobileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.server = MobileServer()
        self.tail_process = QProcess(self)
        self.tail_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.tail_process.readyReadStandardOutput.connect(self.read_tail_output)
        self.tail_process.finished.connect(self.tail_finished)
        self.tail_process.errorOccurred.connect(self.tail_failed)
        self.tail_status = QProcess(self)
        self.tail_status.finished.connect(self.tail_status_finished)
        self.tail_log = ""
        self.remote_owned = False
        self.remote_attempted = False
        root = QVBoxLayout(self)
        intro = QLabel('Vos IA du PC, sur votre téléphone\n'
                       'Sur le même réseau ou à distance : le PC exécute les modèles ; '
                       'le téléphone affiche la conversation. Ollama et les serveurs locaux compatibles OpenAI sont pris en charge.')
        intro.setWordWrap(True)
        root.addWidget(intro)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(['À la maison · réseau local', 'Partout · accès privé Tailscale'])
        self.mode.currentIndexChanged.connect(self.mode_changed)
        form.addRow('Mode de connexion', self.mode)
        self.address = QComboBox()
        self.refresh_addresses()
        form.addRow('Adresse réseau du PC', self.address)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(8765)
        form.addRow('Port', self.port)
        self.url = QLineEdit()
        self.url.setReadOnly(True)
        form.addRow('Adresse à saisir sur Android', self.url)
        self.token = QLineEdit()
        self.token.setReadOnly(True)
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Code d’accès', self.token)
        root.addLayout(form)
        actions = QHBoxLayout()
        self.start = QPushButton('Démarrer le serveur')
        self.start.clicked.connect(self.start_server)
        self.stop = QPushButton('Arrêter le serveur')
        self.stop.clicked.connect(self.shutdown)
        self.stop.setEnabled(False)
        self.refresh = QPushButton('Actualiser les adresses')
        self.refresh.clicked.connect(self.refresh_addresses)
        for b in (self.start, self.stop, self.refresh):
            actions.addWidget(b)
        root.addLayout(actions)
        copies = QHBoxLayout()
        copy_address = QPushButton('Copier l’adresse du PC')
        copy_address.clicked.connect(lambda: QApplication.clipboard().setText(self.url.text()))
        copies.addWidget(copy_address)
        show = QPushButton('Afficher / masquer le code')
        show.clicked.connect(lambda: self.token.setEchoMode(QLineEdit.EchoMode.Normal if self.token.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password))
        copy = QPushButton('Copier le code')
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.token.text()))
        copies.addWidget(show)
        copies.addWidget(copy)
        root.addLayout(copies)
        self.status = QLabel('Serveur arrêté · aucune connexion mobile ouverte.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.remote_help = QLabel(
            'Pour vous connecter hors de chez vous : installez Tailscale sur le PC et le téléphone, '
            'connectez-les au même compte, puis choisissez « Partout » et démarrez le serveur. '
            'Le PC affichera une adresse HTTPS à recopier dans Android. '
            'Gardez le PC, IA Manager et Tailscale démarrés. Aucun port à ouvrir sur la box. '
            'Sur Android, un autre VPN actif peut empêcher Tailscale de fonctionner.')
        self.remote_help.setWordWrap(True)
        self.remote_help.setVisible(False)
        root.addWidget(self.remote_help)
        remote_actions = QHBoxLayout()
        install_tail = QPushButton('Installer Tailscale sur PC et Android')
        install_tail.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://tailscale.com/download')))
        remote_actions.addWidget(install_tail)
        self.remote_actions = QWidget()
        self.remote_actions.setLayout(remote_actions)
        self.remote_actions.setVisible(False)
        root.addWidget(self.remote_actions)
        self.remote_log = QPlainTextEdit()
        self.remote_log.setReadOnly(True)
        self.remote_log.setMaximumHeight(105)
        self.remote_log.setPlaceholderText('Informations de connexion Tailscale…')
        self.remote_log.setVisible(False)
        root.addWidget(self.remote_log)
        help_text = QLabel('1. Lancez Ollama ou votre serveur local et installez un modèle sur le PC.\n'
            '2. Chez vous, choisissez l’adresse Wi-Fi/Ethernet du PC ; à distance, choisissez Tailscale.\n'
            '3. Dans IA Manager Mobile, saisissez l’adresse et le code, puis touchez Connecter.\n'
            '4. Choisissez un modèle et envoyez votre message.\n\n'
            'Si Windows le demande, autorisez IA Manager sur le réseau privé. En cas de blocage, '
            'vérifiez le pare-feu et évitez le Wi-Fi invité qui peut isoler les appareils.\n\n'
            'Le réseau local utilise HTTP : restez sur un réseau de confiance. À distance, Tailscale Serve fournit HTTPS. '
            'N’ouvrez pas le port de cette application sur votre box. '
            'Le code change à chaque démarrage du serveur.\n\n'
            'Le PC et IA Manager doivent rester actifs. Les conversations Android restent sur le téléphone ; '
            'elles ne se synchronisent pas encore avec les projets du PC. Les outils de fichiers et de code du PC ne sont pas exposés.')
        help_text.setWordWrap(True)
        root.addWidget(help_text)
        root.addStretch()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(1000)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def mode_changed(self):
        remote = self.mode.currentIndex() == 1
        self.address.setVisible(not remote)
        self.remote_help.setVisible(remote)
        self.remote_actions.setVisible(remote)
        self.remote_log.setVisible(remote)
        if remote and not self.server.server:
            self.url.setText('')

    @staticmethod
    def tailscale_executable():
        path = shutil.which('tailscale')
        if path:
            return path
        from os import environ
        for key in ('ProgramFiles', 'ProgramFiles(x86)'):
            base = environ.get(key)
            if base:
                candidate = Path(base) / 'Tailscale' / 'tailscale.exe'
                if candidate.is_file():
                    return str(candidate)
        return ''

    def refresh_addresses(self):
        self.address.clear()
        self.address.addItems(lan_addresses())

    def start_server(self):
        try:
            remote = self.mode.currentIndex() == 1
            host = '127.0.0.1' if remote else self.address.currentText()
            if not host:
                raise ValueError('Aucune adresse locale : connectez le PC au réseau puis actualisez.')
            executable = self.tailscale_executable() if remote else ''
            if remote and not executable:
                raise ValueError('Installez Tailscale sur le PC, connectez-vous, puis réessayez.')
            port = self.server.start(host, self.port.value())
            self.url.setText('Configuration Tailscale…' if remote else f'http://{host}:{port}')
            self.token.setText(self.server.token)
            self.start.setEnabled(False)
            self.stop.setEnabled(True)
            self.address.setEnabled(False)
            self.port.setEnabled(False)
            self.refresh.setEnabled(False)
            self.mode.setEnabled(False)
            if remote:
                self.remote_attempted = True
                self.tail_log = ''
                self.remote_log.clear()
                self.tail_process.start(executable, ['serve', '--bg', '--https=8443', f'127.0.0.1:{port}'])
            self.refresh_status()
        except Exception as exc:
            self.status.setText('Démarrage impossible : ' + str(exc))

    def read_tail_output(self):
        data = bytes(self.tail_process.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.tail_log = (self.tail_log + data)[-9000:]
        self.remote_log.setPlainText(self.tail_log)
        found = re.search(r'https://[a-z0-9.-]+\.ts\.net(?::8443)?', self.tail_log, re.I)
        if found:
            url = found.group(0).rstrip('/')
            if ':8443' not in url:
                url += ':8443'
            self.url.setText(url)

    def tail_finished(self, code, _status):
        self.read_tail_output()
        if code == 0 and self.server.server:
            self.remote_owned = True
            if not self.url.text().startswith('https://'):
                executable = self.tailscale_executable()
                if executable:
                    self.tail_status.start(executable, ['status', '--json'])
        elif self.server.server:
            self.remote_attempted = False
            self.server.stop()
            self.unlock('Tailscale non configuré : consultez le journal, puis réessayez. '
                        'Activez HTTPS si Tailscale le demande.')

    def tail_status_finished(self, code, _status):
        if code != 0 or not self.server.server or self.mode.currentIndex() != 1:
            return
        try:
            status = json.loads(bytes(self.tail_status.readAllStandardOutput()).decode('utf-8'))
            name = status['Self']['DNSName'].rstrip('.').lower()
            if not re.fullmatch(r'[a-z0-9-]+\.[a-z0-9-]+\.ts\.net', name):
                raise ValueError('Adresse Tailscale invalide')
            self.url.setText(f'https://{name}:8443')
            self.status.setText('Accès privé prêt · copiez l’adresse HTTPS et le code dans Android.')
        except (ValueError, KeyError, TypeError):
            self.status.setText('Impossible de lire l’adresse Tailscale. Vérifiez le journal et la connexion PC.')

    def tail_failed(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.server.server:
            self.remote_attempted = False
            self.server.stop()
            self.unlock('Impossible de lancer Tailscale. Vérifiez sa connexion sur le PC.')

    def unlock(self, message):
        self.token.clear()
        self.url.clear()
        self.start.setEnabled(True)
        self.stop.setEnabled(False)
        self.address.setEnabled(True)
        self.mode.setEnabled(True)
        self.port.setEnabled(True)
        self.refresh.setEnabled(True)
        self.status.setText(message)

    def refresh_status(self):
        if self.server.server:
            if self.mode.currentIndex() == 1 and not self.url.text().startswith('https://'):
                self.status.setText('Configuration de l’accès privé · consultez le journal Tailscale.')
            else:
                self.status.setText('Serveur actif · ' + self.server.last_status)

    def shutdown(self):
        if self.tail_process.state() != QProcess.ProcessState.NotRunning:
            self.tail_process.kill()
        if self.remote_attempted:
            executable = self.tailscale_executable()
            if executable:
                QProcess.startDetached(executable, ['serve', '--https=8443', 'off'])
            self.remote_owned = False
            self.remote_attempted = False
        self.server.stop()
        self.unlock('Serveur arrêté · connexions mobiles fermées.')

    def closeEvent(self, event):
        if self.server.server or self.remote_attempted:
            self.shutdown()
        super().closeEvent(event)
