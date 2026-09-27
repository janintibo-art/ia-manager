"""Start/stop the optional Android companion server."""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget)
from src.backend.mobile_server import MobileServer, lan_addresses


class MobileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.server = MobileServer()
        root = QVBoxLayout(self)
        intro = QLabel('Vos IA du PC, sur votre téléphone\n'
                       'Connectez les deux appareils au même réseau Wi-Fi. Le PC exécute les modèles ; '
                       'le téléphone affiche la conversation. Ollama et les serveurs locaux compatibles OpenAI sont pris en charge.')
        intro.setWordWrap(True)
        root.addWidget(intro)
        form = QFormLayout()
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
        help_text = QLabel('1. Lancez Ollama ou votre serveur local et installez un modèle sur le PC.\n'
            '2. Choisissez l’adresse Wi-Fi/Ethernet du PC et démarrez ce serveur.\n'
            '3. Dans IA Manager Mobile, saisissez l’adresse et le code, puis touchez Connecter.\n'
            '4. Choisissez un modèle et envoyez votre message.\n\n'
            'Si Windows le demande, autorisez IA Manager sur le réseau privé. En cas de blocage, '
            'vérifiez le pare-feu et évitez le Wi-Fi invité qui peut isoler les appareils.\n\n'
            'Cette première version utilise HTTP sur le réseau local : le code contrôle l’accès mais ne chiffre pas les échanges. '
            'Utilisez votre réseau de confiance, sans ouvrir ce port sur votre box. '
            'Le code change à chaque démarrage du serveur.\n\n'
            'Le PC et IA Manager doivent rester actifs. Les conversations Android restent sur le téléphone ; '
            'elles ne se synchronisent pas encore avec les projets du PC. Les outils de fichiers et de code du PC ne sont pas exposés.')
        help_text.setWordWrap(True)
        root.addWidget(help_text)
        root.addStretch()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(1000)

    def refresh_addresses(self):
        self.address.clear()
        self.address.addItems(lan_addresses())

    def start_server(self):
        try:
            host = self.address.currentText()
            if not host:
                raise ValueError('Aucune adresse locale : connectez le PC au réseau puis actualisez.')
            port = self.server.start(host, self.port.value())
            self.url.setText(f'http://{host}:{port}')
            self.token.setText(self.server.token)
            self.start.setEnabled(False)
            self.stop.setEnabled(True)
            self.address.setEnabled(False)
            self.port.setEnabled(False)
            self.refresh.setEnabled(False)
            self.refresh_status()
        except Exception as exc:
            self.status.setText('Démarrage impossible : ' + str(exc))

    def refresh_status(self):
        if self.server.server:
            self.status.setText('Serveur actif · ' + self.server.last_status)

    def shutdown(self):
        self.server.stop()
        self.token.clear()
        self.url.clear()
        self.start.setEnabled(True)
        self.stop.setEnabled(False)
        self.address.setEnabled(True)
        self.port.setEnabled(True)
        self.refresh.setEnabled(True)
        self.status.setText('Serveur arrêté · connexions mobiles fermées.')
