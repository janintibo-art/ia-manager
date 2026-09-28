"""Page Poids & stockage v106."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox
)

from src.backend import settings, studio_advisor
from src.backend import weight_storage as ws


class WeightStoragePage(QWidget):
    def __init__(self, hub):
        super().__init__()
        self.hub = hub
        root = QVBoxLayout(self)

        intro = QLabel(
            "Centralisez les modèles et contrôlez l'espace disque avant les gros téléchargements. "
            "Cet écran n'efface jamais un modèle complet automatiquement."
        )
        intro.setWordWrap(True); root.addWidget(intro)

        storage_row = QHBoxLayout()
        self.storage_root = QLineEdit(str(settings.get("storage_root") or ""))
        self.storage_root.setPlaceholderText(r"Exemple : D:\IA Manager")
        browse = QPushButton("Parcourir…"); browse.clicked.connect(self.choose_storage)
        apply_btn = QPushButton("Utiliser ce dossier"); apply_btn.clicked.connect(self.apply_storage)
        storage_row.addWidget(QLabel("Stockage principal :"))
        storage_row.addWidget(self.storage_root, 1); storage_row.addWidget(browse); storage_row.addWidget(apply_btn)
        root.addLayout(storage_row)

        estimate_row = QHBoxLayout()
        self.pack = QComboBox()
        for p in studio_advisor.PACKS:
            self.pack.addItem(p["name"], p["id"])
        estimate = QPushButton("Vérifier l'espace pour ce pack"); estimate.clicked.connect(self.check_space)
        estimate_row.addWidget(QLabel("Prévision :")); estimate_row.addWidget(self.pack, 1); estimate_row.addWidget(estimate)
        root.addLayout(estimate_row)

        self.summary = QLabel(); self.summary.setWordWrap(True); root.addWidget(self.summary)

        actions = QHBoxLayout()
        refresh = QPushButton("Actualiser l'inventaire"); refresh.clicked.connect(self.refresh)
        self.only_partial = QCheckBox("Afficher seulement les téléchargements incomplets")
        self.only_partial.toggled.connect(self.refresh_inventory)
        clean = QPushButton("Nettoyer les fichiers incomplets…"); clean.clicked.connect(self.clean_partials)
        actions.addWidget(refresh); actions.addWidget(self.only_partial); actions.addWidget(clean); actions.addStretch(1)
        root.addLayout(actions)

        self.locations = QTableWidget(0, 4)
        self.locations.setHorizontalHeaderLabels(("Zone", "Dossier", "Occupé", "Libre sur le disque"))
        self.locations.verticalHeader().setVisible(False)
        self.locations.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.locations.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.locations, 1)

        self.files = QTableWidget(0, 5)
        self.files.setHorizontalHeaderLabels(("État", "Fichier", "Zone", "Taille", "Chemin"))
        self.files.verticalHeader().setVisible(False)
        self.files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.files, 2)

        self._inventory = []
        self.refresh()

    def choose_storage(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choisir le dossier principal de stockage",
            self.storage_root.text() or str(Path.home())
        )
        if path: self.storage_root.setText(path)

    def apply_storage(self):
        try:
            path = ws.validate_and_set_storage_root(self.storage_root.text().strip())
            self.storage_root.setText(path)
            self.summary.setText(
                "✅ Nouveau stockage principal enregistré. "
                "Les nouveaux téléchargements IA Manager utiliseront ce dossier. "
                "Les fichiers déjà présents ailleurs ne sont pas déplacés automatiquement."
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Stockage", str(exc))

    def check_space(self):
        target = self.storage_root.text().strip()
        if not target:
            QMessageBox.information(self, "Espace disque", "Choisissez d'abord un dossier de stockage principal.")
            return
        try:
            result = ws.preflight(self.pack.currentData(), target)
            names = ", ".join(m["name"] for m in result["models"])
            icon = "✅" if result["enough"] else "⚠️"
            self.summary.setText(
                f"{icon} Pack « {result['pack']['name']} » : modèles ~{result['raw_gb']:.1f} Go, "
                f"prévoir ~{result['recommended_gb']:.1f} Go avec marge. "
                f"Libre : {ws.human_size(result['free'])}. "
                f"Modèles : {names or 'aucun poids référencé'}."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Espace disque", str(exc))

    def refresh(self):
        report = ws.location_report()
        self.locations.setRowCount(len(report))
        total = 0
        for row, item in enumerate(report):
            total += item["size"]
            values = (
                item["name"], item["path"], ws.human_size(item["size"]),
                ws.human_size(item["free"]) if item["free"] else "inconnu"
            )
            for col, value in enumerate(values):
                self.locations.setItem(row, col, QTableWidgetItem(str(value)))
        self.summary.setText(
            f"Zones connues : {len(report)} · occupation inventoriée : {ws.human_size(total)}. "
            "Les caches externes non configurés ne sont pas parcourus."
        )
        self._inventory = ws.inventory()
        self.refresh_inventory()

    def refresh_inventory(self):
        values = self._inventory
        if self.only_partial.isChecked():
            values = [v for v in values if v["partial"]]
        self.files.setRowCount(len(values))
        for row, item in enumerate(values):
            state = "🟠 Incomplet" if item["partial"] else "✅ Poids"
            cols = (state, item["name"], item["location"], ws.human_size(item["size"]), item["path"])
            for col, value in enumerate(cols):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, item["path"])
                self.files.setItem(row, col, cell)
        self.files.resizeRowsToContents()

    def clean_partials(self):
        partials = [item for item in self._inventory if item["partial"]]
        if not partials:
            QMessageBox.information(self, "Nettoyage", "Aucun téléchargement incomplet détecté.")
            return
        total = sum(item["size"] for item in partials)
        reply = QMessageBox.question(
            self, "Nettoyer les téléchargements incomplets",
            f"Supprimer {len(partials)} fichier(s) temporaire(s) pour libérer environ {ws.human_size(total)} ?\n\n"
            "Seuls .part, .tmp et fichiers IA Manager incomplets seront supprimés. "
            "Aucun modèle complet ne sera touché.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = ws.clean_partials(item["path"] for item in partials)
        QMessageBox.information(
            self, "Nettoyage",
            f"{result['deleted']} fichier(s) supprimé(s) · {ws.human_size(result['freed'])} libérés."
        )
        self.refresh()
