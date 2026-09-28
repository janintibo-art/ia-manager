"""Habillage de navigation, indépendant du fonctionnement des onglets."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget,
)

from src.ui import style
from src.ui.branding import asset

# Indices conservés pour les raccourcis et les liens entre écrans existants.
SECTIONS = (
    ("CRÉER", ((4, "Chat", "Échangez avec vos modèles et donnez forme à vos idées."),
                (16, "Création d’images", "Choisissez un modèle et créez vos images avec ComfyUI."),
                (17, "Audio · Vidéo · 3D", "Découvrez les modèles et retrouvez vos outils de création."),
                (3, "Projets", "Retrouvez vos consignes, fichiers et conversations."),
                (15, "Entraîner / Fusionner", "Spécialisez vos modèles et fusionnez des variantes compatibles."),
                (12, "Espace de travail", "Préparez vos documents, profils et essais."))),
    ("EXPLORER", ((1, "Modèles", "Organisez les modèles disponibles sur votre machine."),
                   (2, "Recherche", "Découvrez et téléchargez de nouveaux modèles."),
                   (5, "Comparateur", "Confrontez les réponses de plusieurs modèles."),
                   (7, "Test de vitesse", "Mesurez les performances de votre configuration."))),
    ("PILOTER", ((0, "Analyse", "Faites le point sur votre matériel et votre installation."),
                  (6, "Tableau de bord", "Gardez une vue d’ensemble de votre atelier."),
                  (8, "Tâches", "Organisez vos générations et leurs résultats."),
                  (18, "Outils locaux", "Installez et démarrez vos moteurs de création sur ce PC."),
                  (9, "Connexions", "Configurez vos moteurs locaux et vos services API."),
                  (10, "GitHub", "Retrouvez les outils de gestion de vos dépôts."),
                  (11, "Obliteratus", "Accédez à votre atelier spécialisé et à son journal."),
                  (14, "Téléphone", "Connectez Android aux IA locales de votre PC."))),
    ("APPRENDRE", ((13, "Tuto", "Des explications et des conseils pour avancer à votre rythme."),)),
)


class StudioShell(QWidget):
    def __init__(self, tabs, appearance, parent=None):
        super().__init__(parent)
        self.tabs = tabs
        self.entries = {}
        self.setObjectName("StudioShell")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 16, 12)
        outer.setSpacing(18)
        rail = QFrame()
        rail.setObjectName("NavigationRail")
        rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        left = QVBoxLayout(rail)
        left.setContentsMargins(12, 18, 12, 12)
        self.brand = QLabel("IA Manager")
        self.brand.setObjectName("Brand")
        self.brand.setFixedHeight(62)
        self.brand.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        left.addWidget(self.brand)
        self.update_brand()
        caption = QLabel("VOTRE ATELIER IA")
        caption.setObjectName("NavigationCaption")
        left.addWidget(caption)
        left.addSpacing(16)
        self.navigation = QListWidget()
        self.navigation.setObjectName("StudioNavigation")
        self.navigation.setAccessibleName("Navigation principale")
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for section, entries in SECTIONS:
            heading = QListWidgetItem(section)
            heading.setFlags(Qt.ItemFlag.NoItemFlags)
            self.navigation.addItem(heading)
            for index, title, subtitle in entries:
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, index)
                item.setToolTip(subtitle)
                self.navigation.addItem(item)
                self.entries[index] = (item, title, subtitle, section)
        left.addWidget(self.navigation, 1)
        left.addWidget(appearance)
        outer.addWidget(rail)
        body = QVBoxLayout()
        body.setSpacing(12)
        header = QFrame()
        header.setObjectName("StudioHeader")
        head = QVBoxLayout(header)
        head.setContentsMargins(20, 16, 20, 16)
        for panel, blur, offset in ((rail, 26, 8), (header, 20, 5)):
            shadow = QGraphicsDropShadowEffect(panel)
            shadow.setBlurRadius(blur)
            shadow.setOffset(0, offset)
            shadow.setColor(QColor(0, 0, 0, 78))
            panel.setGraphicsEffect(shadow)
        self.section = QLabel()
        self.section.setObjectName("NavigationCaption")
        self.title = QLabel()
        self.title.setObjectName("Title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")
        self.subtitle.setWordWrap(True)
        for label in (self.section, self.title, self.subtitle):
            head.addWidget(label)
        body.addWidget(header)
        tabs.tabBar().hide()
        body.addWidget(tabs, 1)
        outer.addLayout(body, 1)
        self.navigation.currentItemChanged.connect(self._navigate)
        tabs.currentChanged.connect(self._sync)
        self._sync(tabs.currentIndex())

    def update_brand(self):
        """Le logo clair est réservé au fond sombre ; le texte suit le thème clair."""
        if style.CURRENT_THEME == "sombre":
            pix = QPixmap(str(asset("ia_manager_logo.png")))
            if not pix.isNull():
                self.brand.setPixmap(pix.scaled(192, 62, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
                return
        self.brand.setPixmap(QPixmap())
        self.brand.setText("IA Manager")

    def _navigate(self, item, previous):
        if item is not None:
            index = item.data(Qt.ItemDataRole.UserRole)
            if index is not None:
                self.tabs.setCurrentIndex(index)

    def _sync(self, index):
        entry = self.entries.get(index)
        if entry is None:
            return
        item, title, subtitle, section = entry
        self.navigation.blockSignals(True)
        self.navigation.setCurrentItem(item)
        self.navigation.scrollToItem(item)
        self.navigation.blockSignals(False)
        self.section.setText(section)
        self.title.setText(title)
        self.subtitle.setText(subtitle)
