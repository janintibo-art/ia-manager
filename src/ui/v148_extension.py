"""Extension v148 : identité visuelle commune et mode compact des outils Chirurgie IA."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)


COMMON_STYLE = """
QFrame#SurgeryToolBar {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 13px;
}
QLabel#SurgeryToolName {
    font-size: 15px;
    font-weight: 700;
}
QLabel#SurgeryToolHint {
    opacity: 0.82;
}
QGroupBox {
    margin-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    font-weight: 600;
}
QPlainTextEdit#SurgeryLog {
    border-radius: 10px;
}
"""


class ToolPolisher:
    def __init__(self, window, tab, name, icon, advanced_titles):
        self.window = window
        self.tab = tab
        self.name = name
        self.icon = icon
        self.advanced_titles = tuple(advanced_titles)
        self.advanced_boxes = []
        self.logs = []
        self.toolbar = None
        self.advanced_btn = None
        self.log_btn = None

    def install(self):
        if getattr(self.tab, "_v148_polished", False):
            return

        self.tab.setStyleSheet(self.tab.styleSheet() + COMMON_STYLE)

        layout = self.tab.layout()
        if layout is not None:
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(11)

        self.collect_widgets()
        self.create_toolbar()

        for box in self.advanced_boxes:
            box.setVisible(False)

        for log in self.logs:
            log.setObjectName("SurgeryLog")
            log.setMinimumHeight(150)
            log.setMaximumHeight(240)
            log.setVisible(False)

        self.tab._v148_polished = True

    def collect_widgets(self):
        for box in self.tab.findChildren(QGroupBox):
            title = box.title().lower()
            if any(token.lower() in title for token in self.advanced_titles):
                self.advanced_boxes.append(box)

        for log in self.tab.findChildren(QPlainTextEdit):
            if log.isReadOnly():
                self.logs.append(log)

    def create_toolbar(self):
        root = self.tab.layout()
        if root is None:
            return

        bar = QFrame()
        bar.setObjectName("SurgeryToolBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        label = QLabel(f"{self.icon} {self.name}")
        label.setObjectName("SurgeryToolName")
        lay.addWidget(label)

        hint = QLabel("Mode guidé")
        hint.setObjectName("SurgeryToolHint")
        lay.addWidget(hint)
        lay.addStretch()

        back = QPushButton("← Chirurgie IA")
        back.setToolTip("Retourner au tableau de bord Chirurgie IA")
        back.clicked.connect(self.open_dashboard)
        lay.addWidget(back)

        self.advanced_btn = QPushButton("⚙ Options avancées")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setChecked(False)
        self.advanced_btn.toggled.connect(self.toggle_advanced)
        lay.addWidget(self.advanced_btn)

        self.log_btn = QPushButton("📜 Journal")
        self.log_btn.setCheckable(True)
        self.log_btn.setChecked(False)
        self.log_btn.toggled.connect(self.toggle_logs)
        lay.addWidget(self.log_btn)

        bench = QPushButton("📊 Benchmark")
        bench.clicked.connect(self.open_benchmark)
        lay.addWidget(bench)

        root.insertWidget(0, bar)
        self.toolbar = bar

    def toggle_advanced(self, visible):
        for box in self.advanced_boxes:
            box.setVisible(visible)
        self.advanced_btn.setText(
            "⚙ Masquer options" if visible else "⚙ Options avancées"
        )

    def toggle_logs(self, visible):
        for log in self.logs:
            log.setVisible(visible)
        self.log_btn.setText("📜 Masquer journal" if visible else "📜 Journal")

    def open_dashboard(self):
        tab = getattr(self.window, "surgery_dashboard_tab", None)
        if tab is not None:
            try:
                tab.refresh_status()
            except Exception:
                pass
            self.window.tabs.setCurrentWidget(tab)

    def open_benchmark(self):
        tab = getattr(self.window, "benchmark_tab", None)
        if tab is not None:
            self.window.tabs.setCurrentWidget(tab)


def _polish_heretic(window):
    tab = getattr(window, "heretic_tab", None)
    if tab is None:
        return
    ToolPolisher(
        window,
        tab,
        "Heretic",
        "🔥",
        (
            "Recherche Heretic",
            "Comparateur Original",
        ),
    ).install()

    # Les réglages restent visibles : ce sont les contrôles principaux de Heretic.
    # Les zones v143 de recherche et de comparaison deviennent optionnelles.


def _polish_abliteration(window):
    tab = getattr(window, "abliteration_lab_tab", None)
    if tab is None:
        return
    ToolPolisher(
        window,
        tab,
        "Abliteration Lab",
        "🧬",
        (
            "Couches ciblées",
        ),
    ).install()


def _polish_erisforge(window):
    tab = getattr(window, "erisforge_tab", None)
    if tab is None:
        return
    ToolPolisher(
        window,
        tab,
        "ErisForge",
        "⚒️",
        (
            "Transformation",
        ),
    ).install()


def _polish_dashboard(window):
    tab = getattr(window, "surgery_dashboard_tab", None)
    if tab is None:
        return

    # Évite une table de check-up trop haute : le tableau reste lisible
    # sans pousser toutes les cartes hors de l’écran.
    checks = getattr(tab, "checks", None)
    if checks is not None:
        checks.setMinimumHeight(150)
        checks.setMaximumHeight(220)

    # Les cartes restent équilibrées dans la grille.
    for card in getattr(tab, "cards", {}).values():
        card.setMinimumHeight(175)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )


def install_v148(window):
    if getattr(window, "_v148_surgery_visual_identity", False):
        return

    _polish_dashboard(window)
    _polish_heretic(window)
    _polish_abliteration(window)
    _polish_erisforge(window)

    window._v148_surgery_visual_identity = True
