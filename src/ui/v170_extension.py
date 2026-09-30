"""v170 : centre de vérification et d'installation des composants téléchargeables."""
from PyQt6.QtCore import QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QMessageBox
)

from src.backend import installer_center as center, settings


class InstallationCenterTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.process = None
        self.current_id = None
        root = QVBoxLayout(self)
        title = QLabel("Centre d’installation")
        title.setObjectName("Title")
        root.addWidget(title)
        intro = QLabel(
            "Vérifie les composants nécessaires à IA Manager et installe directement ceux qui peuvent l’être. "
            "Le but est d’éviter d’ouvrir un site sans savoir quoi télécharger."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        buttons = QHBoxLayout()
        refresh = QPushButton("🔍 Vérifier toutes les installations")
        refresh.clicked.connect(self.refresh)
        self.install = QPushButton("⬇ Installer / réparer la sélection")
        self.install.setObjectName("Primary")
        self.install.clicked.connect(self.install_selected)
        self.open = QPushButton("🌐 Ouvrir la solution officielle")
        self.open.clicked.connect(self.open_selected)
        buttons.addWidget(refresh); buttons.addWidget(self.install); buttons.addWidget(self.open); buttons.addStretch()
        root.addLayout(buttons)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["État", "Composant", "Rôle", "Détection / chemin"])
        self.tree.setColumnWidth(0, 95); self.tree.setColumnWidth(1, 170); self.tree.setColumnWidth(2, 300)
        self.tree.currentItemChanged.connect(lambda *_: self.update_actions())
        root.addWidget(self.tree, 1)

        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(170)
        root.addWidget(self.log)
        self.refresh()

    def selected_record(self):
        item = self.tree.currentItem()
        return item.data(0, 0x0100) if item else None

    def refresh(self):
        self.tree.clear()
        rows = center.status_rows()
        ok = 0
        for row in rows:
            if row["installed"]: ok += 1
            state = "✅ OK" if row["installed"] else ("🛠 IA Manager" if row["kind"] == "internal" else "⬇ Manquant")
            path = row["path"] or ("Installation gérée dans Outils locaux" if row["kind"] == "internal" else "Non détecté")
            item = QTreeWidgetItem([state, row["name"], row["role"], path])
            item.setData(0, 0x0100, row)
            self.tree.addTopLevelItem(item)
        self.status.setText(f"{ok}/{len(rows)} composants détectés. Sélectionnez une ligne pour installer ou ouvrir la solution adaptée.")
        if self.tree.topLevelItemCount() and self.tree.currentItem() is None:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self.update_actions()

    def update_actions(self):
        row = self.selected_record()
        busy = self.process is not None
        direct = bool(row and row["kind"] in ("winget", "npm") and not row["installed"])
        internal = bool(row and row["kind"] == "internal" and not row["installed"])
        self.install.setEnabled(not busy and (direct or internal))
        if row and row["installed"]:
            self.install.setText("✅ Déjà installé")
        elif internal:
            self.install.setText("🛠 Ouvrir l’installation IA Manager")
        else:
            self.install.setText("⬇ Installer / réparer la sélection")
        self.open.setEnabled(not busy and bool(row and row.get("fallback")))

    def install_selected(self):
        row = self.selected_record()
        if not row or row["installed"]:
            return
        if row["kind"] == "internal":
            tab = getattr(self.window, "creative_tools_tab", None)
            if tab is not None:
                try:
                    idx = tab.choice.findData("comfyui")
                    if idx >= 0: tab.choice.setCurrentIndex(idx)
                except Exception:
                    pass
                self.window.tabs.setCurrentWidget(tab)
            return
        try:
            command = center.install_command(row["id"])
        except Exception as exc:
            QMessageBox.warning(self, "Installation", str(exc)); return
        reply = QMessageBox.question(self, "Installer " + row["name"],
                                     "IA Manager va lancer l'installation officielle sur ce PC. Continuer ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.current_id = row["id"]
        p = QProcess(self); self.process = p
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(lambda code, status: self.finished(p, code))
        p.errorOccurred.connect(lambda _e: self.status.setText("❌ Impossible de lancer l'installation : " + p.errorString()))
        self.log.clear(); self.status.setText("⏳ Installation de " + row["name"] + "…")
        self.update_actions()
        p.start(command["program"], command["args"])

    def read_output(self):
        if self.process:
            self.log.insertPlainText(bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace"))

    def finished(self, process, code):
        if self.process is not process:
            return
        self.read_output(); self.process = None; process.deleteLater()
        self.status.setText("✅ Installation terminée." if code == 0 else f"❌ Installation terminée avec le code {code}.")
        self.refresh()

    def open_selected(self):
        row = self.selected_record()
        if row and row.get("fallback"):
            QDesktopServices.openUrl(QUrl(row["fallback"]))


def _add_navigation(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "SYSTÈME" and not any(e[0] == "installation_center_tab" for e in entries):
                entries.insert(0, ("installation_center_tab", "Installations", "Vérifiez et installez les composants nécessaires."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    for module_name in ("v165_extension", "v166_extension"):
        try:
            module = __import__("src.ui." + module_name, fromlist=[module_name])
            if hasattr(module, "SIMPLE_ATTRS"):
                module.SIMPLE_ATTRS.add("installation_center_tab")
        except Exception:
            pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v170(window):
    if getattr(window, "_v170_install_center", False):
        return
    tab = InstallationCenterTab(window)
    window.installation_center_tab = tab
    tutorial = getattr(window, "tutorial_tab", None)
    idx = window.tabs.indexOf(tutorial)
    window.tabs.insertTab(idx if idx >= 0 else window.tabs.count(), tab, "⬇ Installations")
    _add_navigation(window)
    window._v170_install_center = True
