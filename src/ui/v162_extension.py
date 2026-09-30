"""v162 : profils matériels évolutifs."""
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from src.backend import hardware_profiles as hp


class HardwareProfilesTab(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.items = []
        self.loading = False
        self.build_ui()
        hp.ensure_detected()
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🖥️ Profils matériels")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Enregistrez plusieurs configurations de PC ou de GPU. Le profil actif sert aux "
            "recommandations IA Manager ; le matériel réellement détecté reste affiché séparément dans Analyse."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        detect = QPushButton("🔍 Ajouter le PC détecté")
        detect.setObjectName("Primary")
        detect.clicked.connect(self.add_detected)
        top.addWidget(detect)

        duplicate = QPushButton("📄 Dupliquer le profil")
        duplicate.clicked.connect(self.duplicate_current)
        top.addWidget(duplicate)

        delete = QPushButton("🗑 Supprimer")
        delete.clicked.connect(self.delete_current)
        top.addWidget(delete)

        apply = QPushButton("✅ Utiliser ce profil")
        apply.clicked.connect(self.activate_current)
        top.addWidget(apply)
        top.addStretch()
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)

        self.list = QListWidget()
        self.list.setMinimumWidth(280)
        self.list.currentItemChanged.connect(lambda *_: self.load_current())
        split.addWidget(self.list)

        editor = QFrame()
        editor.setObjectName("Card")
        el = QVBoxLayout(editor)
        form = QFormLayout()

        self.name = QLineEdit()
        form.addRow("Nom", self.name)

        self.cpu = QLineEdit()
        form.addRow("CPU", self.cpu)

        self.cpu_count = QSpinBox()
        self.cpu_count.setRange(1, 512)
        form.addRow("Cœurs / threads vus", self.cpu_count)

        self.gpu = QLineEdit()
        form.addRow("GPU", self.gpu)

        self.vendor = QComboBox()
        self.vendor.addItems(["NVIDIA", "AMD", "Intel", "Autre", "Aucun"])
        form.addRow("Constructeur GPU", self.vendor)

        self.vram = QDoubleSpinBox()
        self.vram.setRange(0, 256)
        self.vram.setDecimals(1)
        self.vram.setSuffix(" Go")
        form.addRow("VRAM", self.vram)

        self.ram = QDoubleSpinBox()
        self.ram.setRange(1, 1024)
        self.ram.setDecimals(1)
        self.ram.setSuffix(" Go")
        form.addRow("RAM", self.ram)

        self.exact = QCheckBox("VRAM connue précisément")
        form.addRow("", self.exact)

        el.addLayout(form)

        save = QPushButton("💾 Enregistrer les modifications")
        save.clicked.connect(self.save_current)
        el.addWidget(save)

        self.active = QLabel("")
        self.active.setWordWrap(True)
        el.addWidget(self.active)

        self.reco = QLabel("")
        self.reco.setWordWrap(True)
        self.reco.setTextFormat(Qt.TextFormat.RichText)
        el.addWidget(self.reco)

        hint = QLabel(
            "Les profils manuels servent à simuler une future configuration ou un autre PC. "
            "Ils ne modifient ni les pilotes, ni CUDA, ni le matériel réel."
        )
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        el.addWidget(hint)
        el.addStretch()

        split.addWidget(editor)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        root.addWidget(split, 1)

        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh(self, keep=""):
        self.items = hp.list_profiles()
        active = hp.active_id()
        self.list.blockSignals(True)
        self.list.clear()
        select = 0
        for i, profile in enumerate(self.items):
            mark = "✅ " if str(profile.get("id")) == active else ""
            origin = " · détecté" if profile.get("detected") else " · manuel"
            item = QListWidgetItem(
                f"{mark}{profile.get('name','Profil')}\n"
                f"    {profile.get('gpu_type','GPU')} · {float(profile.get('vram_gb') or 0):.1f} Go VRAM"
                f" · {float(profile.get('ram_gb') or 0):.0f} Go RAM{origin}"
            )
            item.setData(Qt.ItemDataRole.UserRole, str(profile.get("id")))
            self.list.addItem(item)
            if keep and str(profile.get("id")) == keep:
                select = i
        if self.list.count():
            self.list.setCurrentRow(select)
        self.list.blockSignals(False)
        self.load_current()

    def current(self):
        item = self.list.currentItem()
        if not item:
            return None
        pid = item.data(Qt.ItemDataRole.UserRole)
        return next((p for p in self.items if str(p.get("id")) == str(pid)), None)

    def load_current(self):
        p = self.current()
        if not p:
            return
        self.loading = True
        self.name.setText(str(p.get("name") or ""))
        self.cpu.setText(str(p.get("cpu") or ""))
        self.cpu_count.setValue(int(p.get("cpu_count") or 1))
        self.gpu.setText(str(p.get("gpu_type") or ""))
        idx = self.vendor.findText(str(p.get("gpu_vendor") or "Autre"))
        self.vendor.setCurrentIndex(idx if idx >= 0 else self.vendor.findText("Autre"))
        self.vram.setValue(float(p.get("vram_gb") or 0))
        self.ram.setValue(max(1.0, float(p.get("ram_gb") or 1)))
        self.exact.setChecked(bool(p.get("vram_exact", True)))
        active = str(p.get("id")) == hp.active_id()
        self.active.setText("✅ Profil actif pour les recommandations." if active else "Profil enregistré mais non actif.")
        r = hp.recommendations(p)
        self.reco.setText(
            "<b>Conseils pour ce profil</b><br>"
            f"💬 Texte : {r.get('text','—')}<br>"
            f"🎨 Image : {r.get('image','—')}<br>"
            f"🎬 Vidéo : {r.get('video','—')}<br>"
            f"🧠 Entraînement : {r.get('training','—')}"
        )
        self.loading = False

    def add_detected(self):
        p = hp.detect_profile(f"PC détecté {datetime.now():%Y-%m-%d}")
        items = hp.list_profiles()
        items.append(p)
        hp.save_profiles(items)
        self.refresh(p["id"])
        self.status.setText("✅ Configuration réellement détectée ajoutée.")

    def duplicate_current(self):
        p = self.current()
        if not p:
            return
        q = dict(p)
        q["id"] = datetime.now().isoformat(timespec="microseconds").replace(":", "").replace("-", "")
        q["name"] = str(p.get("name") or "Profil") + " — copie"
        q["detected"] = False
        q["created"] = datetime.now().isoformat(timespec="seconds")
        items = hp.list_profiles()
        items.append(q)
        hp.save_profiles(items)
        self.refresh(q["id"])
        self.status.setText("Copie créée. Vous pouvez simuler une future carte graphique ou davantage de RAM.")

    def save_current(self):
        p = self.current()
        if not p:
            return
        pid = str(p.get("id"))
        items = hp.list_profiles()
        for item in items:
            if str(item.get("id")) == pid:
                item.update({
                    "name": self.name.text().strip() or "Profil matériel",
                    "cpu": self.cpu.text().strip(),
                    "cpu_count": self.cpu_count.value(),
                    "gpu_type": self.gpu.text().strip(),
                    "gpu_vendor": self.vendor.currentText(),
                    "vram_gb": self.vram.value(),
                    "ram_gb": self.ram.value(),
                    "ram_available_gb": self.ram.value(),
                    "vram_exact": self.exact.isChecked(),
                    "detected": False if self._values_changed_from_detected(item) else item.get("detected", False),
                })
                break
        hp.save_profiles(items)
        self.refresh(pid)
        if pid == hp.active_id():
            self.apply_active()
        self.status.setText("✅ Profil enregistré.")

    def _values_changed_from_detected(self, old):
        if not old.get("detected"):
            return False
        return (
            self.cpu.text().strip() != str(old.get("cpu") or "")
            or self.gpu.text().strip() != str(old.get("gpu_type") or "")
            or abs(self.vram.value() - float(old.get("vram_gb") or 0)) > 0.05
            or abs(self.ram.value() - float(old.get("ram_gb") or 0)) > 0.05
        )

    def delete_current(self):
        p = self.current()
        if not p:
            return
        if len(self.items) <= 1:
            self.status.setText("Conservez au moins un profil matériel.")
            return
        if QMessageBox.question(
            self, "Supprimer le profil", f"Supprimer « {p.get('name')} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        pid = str(p.get("id"))
        items = [x for x in hp.list_profiles() if str(x.get("id")) != pid]
        hp.save_profiles(items)
        if hp.active_id() == pid and items:
            hp.set_active(items[0]["id"])
        self.refresh()
        self.apply_active()
        self.status.setText("Profil supprimé.")

    def activate_current(self):
        p = self.current()
        if not p:
            return
        hp.set_active(p["id"])
        self.refresh(str(p["id"]))
        self.apply_active()
        self.status.setText("✅ Profil actif appliqué aux recommandations.")

    def apply_active(self):
        profile = hp.active_profile()
        info = hp.to_system_info(profile)
        if not info:
            return

        models = getattr(self.window, "models_tab", None)
        if models is not None:
            try:
                models.set_system_info(info)
            except Exception:
                pass

        smart = getattr(self.window, "smart_library_tab", None)
        if smart is not None:
            try:
                smart.info = dict(info)
                smart.refresh()
            except Exception:
                pass

        training = getattr(self.window, "training_tab", None)
        if training is not None:
            try:
                training.set_system_info(info)
                training.hardware_label.setText(
                    "Profil de recommandation : " + str(profile.get("name")) + " · " + training.hardware_label.text()
                )
            except Exception:
                pass

        image = getattr(self.window, "image_studio_tab", None)
        if image is not None:
            try:
                vram = float(profile.get("vram_gb") or 0)
                target = 1024 if vram >= 12 else 768 if vram >= 8 else 512
                idx = image.size.findData(target)
                if idx >= 0:
                    image.size.setCurrentIndex(idx)
                image.status.setText(
                    f"Profil matériel « {profile.get('name')} » : résolution de départ proposée {target}×{target}. "
                    "Vous pouvez la modifier avant la génération."
                )
            except Exception:
                pass

        media = getattr(self.window, "media_studio_tab", None)
        if media is not None:
            try:
                r = hp.recommendations(profile)
                media.status.setText(
                    f"Profil matériel « {profile.get('name')} » · vidéo : {r.get('video','réglages à vérifier')}."
                )
            except Exception:
                pass


def _add_nav(window):
    try:
        from src.ui import v149_extension as nav
        groups = []
        for section, entries in nav.GROUPS:
            entries = list(entries)
            if section == "SYSTÈME":
                if not any(e[0] == "hardware_profiles_tab" for e in entries):
                    entries.insert(0, (
                        "hardware_profiles_tab",
                        "Profils matériels",
                        "Enregistrez plusieurs PC/GPU et adaptez les recommandations."
                    ))
            groups.append((section, tuple(entries)))
        nav.GROUPS = tuple(groups)
    except Exception:
        pass
    shell = getattr(window, "studio_shell", None)
    if shell is not None and hasattr(shell, "refresh_navigation"):
        shell.refresh_navigation()


def install_v162(window):
    if getattr(window, "_v162_hardware_profiles", False):
        return

    hp.ensure_detected()
    tab = HardwareProfilesTab(window)
    window.hardware_profiles_tab = tab

    storage_tab = getattr(window, "storage_tab", None)
    idx = window.tabs.indexOf(storage_tab)
    window.tabs.insertTab(idx if idx >= 0 else window.tabs.count(), tab, "🖥️ Profils matériels")

    _add_nav(window)

    # Applique le profil actif sans modifier l'onglet Analyse, qui reste la vérité du PC réel.
    tab.apply_active()

    window._v162_hardware_profiles = True
