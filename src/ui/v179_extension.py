"""v179 : page d'audit global des installations."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTreeWidget, QTreeWidgetItem,
)

from src.backend import installation_audit


LABELS = {
    "automatic": ("✅ Automatique", "Installation/lancement pris en charge dans IA Manager."),
    "partial": ("🟠 Partiel", "Le modèle est connu mais certaines étapes restent manuelles."),
    "todo": ("🔴 À intégrer", "Pas encore de parcours complet depuis IA Manager."),
}


class InstallationAuditTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window

        root = QVBoxLayout(self)
        title = QLabel("Audit global des installations")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Cette page montre ce qui peut réellement être installé depuis IA Manager, "
            "ce qui est seulement partiellement intégré et ce qu'il reste à automatiser."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        top.addWidget(self.summary_label, 1)

        self.filter = QComboBox()
        self.filter.addItem("Tous", "")
        self.filter.addItem("✅ Automatique", "automatic")
        self.filter.addItem("🟠 Partiel", "partial")
        self.filter.addItem("🔴 À intégrer", "todo")
        self.filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.filter)

        refresh = QPushButton("🔄 Actualiser")
        refresh.clicked.connect(self.refresh)
        top.addWidget(refresh)
        root.addLayout(top)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["État", "Modèle / outil", "Catégorie", "Moteur"])
        self.tree.setColumnWidth(0, 130)
        self.tree.setColumnWidth(1, 240)
        self.tree.setColumnWidth(2, 150)
        self.tree.setColumnWidth(3, 280)
        self.tree.currentItemChanged.connect(lambda *_: self.update_actions())
        root.addWidget(self.tree, 1)

        actions = QHBoxLayout()
        self.open = QPushButton("➡ Ouvrir la bonne section")
        self.open.setObjectName("Primary")
        self.open.clicked.connect(self.open_section)
        self.details = QLabel()
        self.details.setWordWrap(True)
        actions.addWidget(self.open)
        actions.addWidget(self.details, 1)
        root.addLayout(actions)

        self.refresh()

    def selected(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def refresh(self):
        selected_id = (self.selected() or {}).get("id")
        self.tree.clear()
        filt = self.filter.currentData()
        rows = installation_audit.next_targets()

        first = None
        for row in rows:
            if filt and row["level"] != filt:
                continue
            label, _desc = LABELS[row["level"]]
            item = QTreeWidgetItem([label, row["name"], row["category"], row["engine"]])
            item.setData(0, Qt.ItemDataRole.UserRole, row)
            self.tree.addTopLevelItem(item)
            if first is None:
                first = item
            if row["id"] == selected_id:
                self.tree.setCurrentItem(item)

        if self.tree.currentItem() is None and first is not None:
            self.tree.setCurrentItem(first)

        s = installation_audit.summary()
        self.summary_label.setText(
            f"✅ {s['automatic']} automatiques · "
            f"🟠 {s['partial']} partiels · "
            f"🔴 {s['todo']} à intégrer"
        )
        self.update_actions()

    def update_actions(self):
        row = self.selected()
        if not row:
            self.open.setEnabled(False)
            self.details.clear()
            return
        self.open.setEnabled(True)
        _label, desc = LABELS[row["level"]]
        self.details.setText(desc)

    def open_section(self):
        row = self.selected()
        if not row:
            return
        route = row["route"]

        if route == "models":
            self.window.tabs.setCurrentWidget(self.window.models_tab)
            # Le modèle Studio n'a pas toujours le même identifiant Ollama.
            # On ouvre donc le catalogue sans forcer une mauvaise sélection.
        elif route == "image":
            self.window.tabs.setCurrentWidget(self.window.image_studio_tab)
        elif route == "media":
            self.window.tabs.setCurrentWidget(self.window.media_studio_tab)
            # Essaie de sélectionner le modèle exact du catalogue média.
            tab = self.window.media_studio_tab
            for i in range(tab.models.count()):
                data = tab.models.item(i).data(Qt.ItemDataRole.UserRole) or {}
                if data.get("id") == row["id"] or (
                    row["id"] == "hunyuan3d2" and data.get("id") == "hunyuan3d"
                ):
                    tab.models.setCurrentRow(i)
                    break
        else:
            self.window.tabs.setCurrentWidget(self.window.search_tab)

def _add_navigation(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "SYSTÈME" and not any(e[0] == "installation_audit_tab" for e in entries):
                entries.insert(1, ("installation_audit_tab", "Audit installations", "Voir ce qui est automatique, partiel ou à intégrer."))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    for module_name in ("v165_extension", "v166_extension"):
        try:
            module = __import__("src.ui." + module_name, fromlist=[module_name])
            if hasattr(module, "SIMPLE_ATTRS"):
                module.SIMPLE_ATTRS.add("installation_audit_tab")
        except Exception:
            pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()

def install_v179(window):
    if getattr(window, "_v179_install_audit", False):
        return
    tab = InstallationAuditTab(window)
    window.installation_audit_tab = tab
    target = getattr(window, "installation_center_tab", None)
    idx = window.tabs.indexOf(target) if target is not None else -1
    window.tabs.insertTab(idx + 1 if idx >= 0 else window.tabs.count(), tab, "🧭 Audit installations")
    _add_navigation(window)
    window._v179_install_audit = True
