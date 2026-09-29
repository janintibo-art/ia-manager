"""Extension v130 : presets et réglages avancés Obliteratus."""
from types import MethodType

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QSpinBox, QVBoxLayout,
)

from src.backend import local_jobs
from src.backend import obliteratus as ob


PRESETS = {
    "auto": {
        "label": "🧠 Informed automatique",
        "method": "informed",
        "n_directions": None,
        "passes": None,
        "layers": None,
        "verify": 30,
        "description": (
            "Laisse Obliteratus analyser le modèle et choisir automatiquement "
            "une stratégie adaptée."
        ),
    },
    "quick": {
        "label": "⚡ Rapide",
        "method": "basic",
        "n_directions": 1,
        "passes": 1,
        "layers": "knee",
        "verify": 12,
        "description": (
            "Traitement court pour essais. Peu de directions et une seule passe."
        ),
    },
    "balanced": {
        "label": "⚖️ Équilibré",
        "method": "advanced",
        "n_directions": 2,
        "passes": 2,
        "layers": "knee_cosmic",
        "verify": 30,
        "description": (
            "Bon compromis pour un usage général : analyse ciblée, deux directions "
            "et deux passes."
        ),
    },
    "precise": {
        "label": "🎯 Précis",
        "method": "surgical",
        "n_directions": 3,
        "passes": 3,
        "layers": "knee_cosmic",
        "verify": 50,
        "description": (
            "Intervention plus fine avec davantage de vérifications. Plus lent."
        ),
    },
    "aggressive": {
        "label": "🔥 Agressif",
        "method": "aggressive",
        "n_directions": 4,
        "passes": 3,
        "layers": "all_except_first",
        "verify": 40,
        "description": (
            "Intervention plus large. À comparer soigneusement avec le modèle original."
        ),
    },
    "preserve": {
        "label": "🛡️ Préservation maximale",
        "method": "surgical",
        "n_directions": 1,
        "passes": 1,
        "layers": "knee_cosmic",
        "verify": 80,
        "description": (
            "Modification limitée et davantage de vérifications pour privilégier "
            "la conservation du comportement général."
        ),
    },
    "custom": {
        "label": "🛠️ Personnalisé",
        "method": "advanced",
        "n_directions": 2,
        "passes": 2,
        "layers": "knee_cosmic",
        "verify": 30,
        "description": "Réglez manuellement les paramètres ci-dessous.",
    },
}

LAYER_LABELS = [
    ("COSMIC / genou", "knee_cosmic"),
    ("Genou", "knee"),
    ("Toutes", "all"),
    ("Toutes sauf première", "all_except_first"),
    ("60 % centrales", "middle60"),
    ("Top K", "top_k"),
]


def _command(tab):
    source = tab.v126_source.text().strip()
    if not source:
        raise ValueError("Choisissez un modèle Hugging Face ou un checkpoint local.")

    method = tab.v126_method.currentData()
    python = ob.environment_python()
    if not python.is_file():
        raise ValueError("Installez Obliteratus avant d'utiliser le mode intégré.")

    args = ["-u", "-m", "obliteratus", "obliterate", source, "--method", method]

    n_dir = tab.v130_directions.value()
    passes = tab.v130_passes.value()
    verify = tab.v130_verify.value()
    layers = tab.v130_layers.currentData()

    if n_dir > 0:
        args += ["--n-directions", str(n_dir)]
    if passes > 0:
        args += ["--refinement-passes", str(passes)]
    if layers:
        args += ["--layer-selection", str(layers)]
    if verify > 0:
        args += ["--verify-sample-size", str(verify)]

    # Valeur 0 = laisser Obliteratus décider.
    regularization = tab.v130_regularization.value()
    if regularization > 0:
        args += ["--regularization", f"{regularization:.2f}"]

    return str(python), args


def install_v130(window):
    tab = getattr(window, "obliteratus_tab", None)
    if tab is None or not hasattr(tab, "v126_source") or getattr(window, "_v130_obliteratus", False):
        return

    group = QGroupBox("Preset de traitement")
    layout = QVBoxLayout(group)

    top = QHBoxLayout()
    top.addWidget(QLabel("Profil"))
    tab.v130_preset = QComboBox()
    for key, spec in PRESETS.items():
        tab.v130_preset.addItem(spec["label"], key)
    top.addWidget(tab.v130_preset, 1)
    layout.addLayout(top)

    tab.v130_description = QLabel()
    tab.v130_description.setWordWrap(True)
    layout.addWidget(tab.v130_description)

    form = QFormLayout()

    tab.v130_directions = QSpinBox()
    tab.v130_directions.setRange(0, 16)
    tab.v130_directions.setSpecialValueText("Auto")
    form.addRow("Directions", tab.v130_directions)

    tab.v130_passes = QSpinBox()
    tab.v130_passes.setRange(0, 10)
    tab.v130_passes.setSpecialValueText("Auto")
    form.addRow("Passes de raffinement", tab.v130_passes)

    tab.v130_layers = QComboBox()
    tab.v130_layers.addItem("Auto / méthode par défaut", "")
    for label, value in LAYER_LABELS:
        tab.v130_layers.addItem(label, value)
    form.addRow("Couches", tab.v130_layers)

    tab.v130_verify = QSpinBox()
    tab.v130_verify.setRange(0, 500)
    tab.v130_verify.setSpecialValueText("Auto")
    form.addRow("Prompts de vérification", tab.v130_verify)

    tab.v130_regularization = QDoubleSpinBox()
    tab.v130_regularization.setRange(0.0, 1.0)
    tab.v130_regularization.setSingleStep(0.05)
    tab.v130_regularization.setDecimals(2)
    tab.v130_regularization.setSpecialValueText("Auto")
    tab.v130_regularization.setToolTip(
        "0 = laisser Obliteratus choisir. Sinon transmet --regularization."
    )
    form.addRow("Régularisation", tab.v130_regularization)

    layout.addLayout(form)

    tab.v130_summary = QLabel()
    tab.v130_summary.setWordWrap(True)
    layout.addWidget(tab.v130_summary)

    # Le bloc v126 est au début de l'onglet : ajouter le preset juste après lui.
    tab.layout().insertWidget(3, group)

    def v130_apply_preset(self):
        key = self.v130_preset.currentData()
        spec = PRESETS.get(key, PRESETS["balanced"])

        # Synchronise le sélecteur de méthode déjà présent depuis v126.
        idx = self.v126_method.findData(spec["method"])
        if idx >= 0:
            self.v126_method.setCurrentIndex(idx)

        self.v130_directions.setValue(spec["n_directions"] or 0)
        self.v130_passes.setValue(spec["passes"] or 0)
        self.v130_verify.setValue(spec["verify"] or 0)

        layer_index = self.v130_layers.findData(spec["layers"] or "")
        if layer_index >= 0:
            self.v130_layers.setCurrentIndex(layer_index)

        self.v130_regularization.setValue(0.0)
        self.v130_description.setText(spec["description"])
        self.v130_refresh_summary()

    def v130_mark_custom(self):
        if self.v130_preset.currentData() != "custom":
            idx = self.v130_preset.findData("custom")
            if idx >= 0:
                self.v130_preset.blockSignals(True)
                self.v130_preset.setCurrentIndex(idx)
                self.v130_preset.blockSignals(False)
                self.v130_description.setText(PRESETS["custom"]["description"])
        self.v130_refresh_summary()

    def v130_refresh_summary(self):
        method = self.v126_method.currentData() or "advanced"
        dirs = self.v130_directions.value()
        passes = self.v130_passes.value()
        verify = self.v130_verify.value()
        layers = self.v130_layers.currentText()
        reg = self.v130_regularization.value()
        self.v130_summary.setText(
            "Réglages actifs · "
            f"méthode {method} · "
            f"directions {'auto' if dirs == 0 else dirs} · "
            f"passes {'auto' if passes == 0 else passes} · "
            f"couches {layers} · "
            f"vérification {'auto' if verify == 0 else verify} · "
            f"régularisation {'auto' if reg == 0 else f'{reg:.2f}'}"
        )

    def v130_start(self):
        if self.v126_process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.mode or self.detecting:
            self.v126_status.setText(
                "Une autre opération Obliteratus est déjà active. Attendez sa fin."
            )
            return
        if hasattr(self, "v127_process") and self.v127_process.state() != QProcess.ProcessState.NotRunning:
            self.v126_status.setText(
                "La préparation de la source Hugging Face est encore en cours."
            )
            return

        try:
            program, args = _command(self)
        except Exception as exc:
            self.v126_status.setText(str(exc))
            return

        if local_jobs.enabled():
            self.v126_resource_token = local_jobs.reserve("Obliteratus intégré")
            if self.v126_resource_token is None:
                self.v126_status.setText(
                    "Un autre travail local utilise déjà les ressources. Attendez sa fin."
                )
                return

        self.log.clear()
        self.v126_status.setText(
            f"Traitement Obliteratus en cours · preset {self.v130_preset.currentText()}."
        )
        self.v126_set_busy(True)

        env = QProcessEnvironment.systemEnvironment()
        for key, value in {
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "OBLITERATUS_TELEMETRY": "0",
            "GRADIO_ANALYTICS_ENABLED": "False",
        }.items():
            env.insert(key, value)
        self.v126_process.setProcessEnvironment(env)
        ob.tools_dir().mkdir(parents=True, exist_ok=True)
        self.v126_process.setWorkingDirectory(str(ob.tools_dir()))
        self.v126_process.start(program, args)

    tab.v130_apply_preset = MethodType(v130_apply_preset, tab)
    tab.v130_mark_custom = MethodType(v130_mark_custom, tab)
    tab.v130_refresh_summary = MethodType(v130_refresh_summary, tab)
    tab.v130_start = MethodType(v130_start, tab)

    tab.v130_preset.currentIndexChanged.connect(tab.v130_apply_preset)

    for widget in (
        tab.v130_directions,
        tab.v130_passes,
        tab.v130_layers,
        tab.v130_verify,
        tab.v130_regularization,
        tab.v126_method,
    ):
        if isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(tab.v130_mark_custom)
        else:
            widget.valueChanged.connect(tab.v130_mark_custom)

    # Remplace uniquement l'action du bouton de lancement v126.
    try:
        tab.v126_run.clicked.disconnect()
    except (TypeError, RuntimeError):
        pass
    tab.v126_run.clicked.connect(tab.v130_start)

    # Le preset équilibré devient le choix de départ.
    idx = tab.v130_preset.findData("balanced")
    if idx >= 0:
        tab.v130_preset.setCurrentIndex(idx)
    tab.v130_apply_preset()

    window._v130_obliteratus = True
