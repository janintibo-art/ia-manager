"""Extension v137 : réglages avancés LoRA / QLoRA et profils GPU."""
import json
from types import MethodType

from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from src.backend import training_lab as lab


PROFILES = {
    "eco": {
        "label": "🪶 Économe",
        "mode": "qlora",
        "lr": 0.0001,
        "ga": 16,
        "warmup": 0.03,
        "optim": "adamw_8bit",
        "save": 1,
    },
    "balanced": {
        "label": "⚖️ Équilibré",
        "mode": "qlora",
        "lr": 0.0001,
        "ga": 8,
        "warmup": 0.05,
        "optim": "adamw_8bit",
        "save": 2,
    },
    "quality": {
        "label": "🎯 Qualité",
        "mode": "lora",
        "lr": 0.00005,
        "ga": 8,
        "warmup": 0.08,
        "optim": "adamw_torch",
        "save": 3,
    },
    "custom": {
        "label": "🛠️ Personnalisé",
        "mode": "qlora",
        "lr": 0.0001,
        "ga": 8,
        "warmup": 0.05,
        "optim": "adamw_8bit",
        "save": 2,
    },
}


def _patch_runner():
    runner = lab.RUNNER

    old = "model_name=cfg['model'], max_seq_length=tuning['context'], load_in_4bit=True,"
    new = (
        "model_name=cfg['model'], max_seq_length=tuning['context'], "
        "load_in_4bit=(tuning.get('mode', 'qlora') == 'qlora'),"
    )
    runner = runner.replace(old, new)

    old = "use_gradient_checkpointing='unsloth', random_state=42)"
    new = "use_gradient_checkpointing='unsloth', random_state=tuning.get('seed', 42))"
    runner = runner.replace(old, new)

    old = "data = Dataset.from_list(texts).train_test_split(test_size=0.2, seed=42)"
    new = (
        "data = Dataset.from_list(texts).train_test_split("
        "test_size=0.2, seed=tuning.get('seed', 42))"
    )
    runner = runner.replace(old, new)

    old = "gradient_accumulation_steps=max(1, 8//tuning['batch']),"
    new = (
        "gradient_accumulation_steps=tuning.get("
        "'gradient_accumulation', max(1, 8//tuning['batch'])),"
    )
    runner = runner.replace(old, new)

    runner = runner.replace(
        "num_train_epochs=cfg['epochs'], max_steps=2 if trial else -1, learning_rate=0.0001,",
        "num_train_epochs=cfg['epochs'], max_steps=2 if trial else -1, "
        "learning_rate=tuning.get('learning_rate', 0.0001),"
    )

    runner = runner.replace(
        "warmup_ratio=0.05, logging_steps=1, save_strategy='no' if trial else 'epoch',",
        "warmup_ratio=tuning.get('warmup_ratio', 0.05), logging_steps=1, "
        "save_strategy='no' if trial or tuning.get('save_limit', 2) == 0 else 'epoch',"
    )

    runner = runner.replace(
        "eval_strategy='no' if trial else 'epoch', save_total_limit=2, report_to='none',",
        "eval_strategy='no' if trial else 'epoch', "
        "save_total_limit=max(1, tuning.get('save_limit', 2)), report_to='none',"
    )

    runner = runner.replace(
        "optim='adamw_8bit', fp16=not is_bfloat16_supported(),",
        "optim=tuning.get('optimizer', 'adamw_8bit'), "
        "fp16=not is_bfloat16_supported(),"
    )

    runner = runner.replace(
        "bf16=is_bfloat16_supported(), seed=42, dataset_num_proc=1,",
        "bf16=is_bfloat16_supported(), seed=tuning.get('seed', 42), dataset_num_proc=1,"
    )

    lab.RUNNER = runner


def _patch_create_job():
    if getattr(lab, "_v137_create_job_patched", False):
        return

    original = lab.create_job

    def create_job(action, model='', other='', dataset='', epochs=1, weight=.5,
                   tuning=None, hardware=None, merge_method="linear"):
        full = dict(tuning or {})
        basic = {
            "context": int(full.get("context", 1024)),
            "rank": int(full.get("rank", 8)),
            "batch": int(full.get("batch", 1)),
        }
        job = original(
            action, model, other, dataset, epochs, weight,
            tuning=basic, hardware=hardware, merge_method=merge_method
        )
        if action in ("train", "trial"):
            config_path = job / "job.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["tuning"].update({
                "mode": full.get("mode", "qlora"),
                "learning_rate": float(full.get("learning_rate", 0.0001)),
                "gradient_accumulation": int(full.get(
                    "gradient_accumulation", max(1, 8 // basic["batch"])
                )),
                "warmup_ratio": float(full.get("warmup_ratio", 0.05)),
                "optimizer": full.get("optimizer", "adamw_8bit"),
                "save_limit": int(full.get("save_limit", 2)),
                "seed": int(full.get("seed", 42)),
            })
            config_path.write_text(
                json.dumps(config, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            (job / "runner.py").write_text(lab.RUNNER, encoding="utf-8")
        return job

    lab.create_job = create_job
    lab._v137_create_job_patched = True


def install_v137(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(window, "_v137_training", False):
        return

    _patch_runner()
    _patch_create_job()

    box = QGroupBox("Réglages avancés Unsloth")
    layout = QVBoxLayout(box)

    intro = QLabel(
        "QLoRA charge le modèle de base en 4 bits et économise fortement la VRAM. "
        "LoRA garde le modèle en précision normale et demande davantage de mémoire."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    form = QFormLayout()

    tab.v137_profile = QComboBox()
    tab.v137_profile.addItem("🧠 Automatique selon le GPU", "auto")
    for key, spec in PROFILES.items():
        tab.v137_profile.addItem(spec["label"], key)
    form.addRow("Profil", tab.v137_profile)

    tab.v137_mode = QComboBox()
    tab.v137_mode.addItem("QLoRA · 4 bits · mémoire réduite", "qlora")
    tab.v137_mode.addItem("LoRA · précision normale · plus de VRAM", "lora")
    form.addRow("Mode", tab.v137_mode)

    tab.v137_lr = QDoubleSpinBox()
    tab.v137_lr.setDecimals(6)
    tab.v137_lr.setRange(0.000001, 0.01)
    tab.v137_lr.setSingleStep(0.00001)
    tab.v137_lr.setValue(0.0001)
    form.addRow("Learning rate", tab.v137_lr)

    tab.v137_ga = QComboBox()
    for value in (1, 2, 4, 8, 16, 32, 64):
        tab.v137_ga.addItem(str(value), value)
    tab.v137_ga.setCurrentIndex(tab.v137_ga.findData(8))
    form.addRow("Accumulation gradient", tab.v137_ga)

    tab.v137_warmup = QDoubleSpinBox()
    tab.v137_warmup.setDecimals(2)
    tab.v137_warmup.setRange(0.0, 0.5)
    tab.v137_warmup.setSingleStep(0.01)
    tab.v137_warmup.setValue(0.05)
    form.addRow("Warmup ratio", tab.v137_warmup)

    tab.v137_optimizer = QComboBox()
    tab.v137_optimizer.addItem("AdamW 8-bit", "adamw_8bit")
    tab.v137_optimizer.addItem("AdamW PyTorch", "adamw_torch")
    tab.v137_optimizer.addItem("Paged AdamW 8-bit", "paged_adamw_8bit")
    form.addRow("Optimiseur", tab.v137_optimizer)

    tab.v137_save = QSpinBox()
    tab.v137_save.setRange(0, 10)
    tab.v137_save.setValue(2)
    tab.v137_save.setSpecialValueText("Aucune")
    form.addRow("Sauvegardes conservées", tab.v137_save)

    tab.v137_seed = QSpinBox()
    tab.v137_seed.setRange(0, 2147483647)
    tab.v137_seed.setValue(42)
    form.addRow("Seed", tab.v137_seed)

    layout.addLayout(form)

    row = QHBoxLayout()
    tab.v137_apply = QPushButton("✨ Appliquer le profil")
    row.addWidget(tab.v137_apply)
    row.addStretch()
    layout.addLayout(row)

    tab.v137_summary = QLabel()
    tab.v137_summary.setWordWrap(True)
    layout.addWidget(tab.v137_summary)

    root = tab.layout()
    insert_at = 6 if root.count() >= 6 else max(0, root.count() - 2)
    root.insertWidget(insert_at, box)

    old_tuning = tab.tuning
    old_set_system_info = tab.set_system_info

    def v137_auto_profile(self):
        info = self.system_info or {}
        vram = float(info.get("vram_gb") or 0)
        exact = bool(info.get("vram_exact"))
        if not exact:
            return "balanced"
        if vram >= 20:
            return "quality"
        if vram >= 10:
            return "balanced"
        return "eco"

    def v137_apply_profile(self):
        key = self.v137_profile.currentData()
        if key == "auto":
            key = self.v137_auto_profile()
        spec = PROFILES.get(key, PROFILES["balanced"])
        self.v137_mode.setCurrentIndex(
            max(0, self.v137_mode.findData(spec["mode"]))
        )
        self.v137_lr.setValue(spec["lr"])
        self.v137_ga.setCurrentIndex(
            max(0, self.v137_ga.findData(spec["ga"]))
        )
        self.v137_warmup.setValue(spec["warmup"])
        self.v137_optimizer.setCurrentIndex(
            max(0, self.v137_optimizer.findData(spec["optim"]))
        )
        self.v137_save.setValue(spec["save"])
        self.v137_refresh_summary()

    def v137_refresh_summary(self):
        mode = self.v137_mode.currentData()
        info = self.system_info or {}
        vram = float(info.get("vram_gb") or 0)
        warning = ""
        if mode == "lora" and vram and vram < 16:
            warning = (
                " ⚠️ LoRA peut être trop gourmand pour la VRAM détectée ; "
                "QLoRA est plus prudent."
            )
        self.v137_summary.setText(
            f"Réglages actifs · {mode.upper()} · LR {self.v137_lr.value():.6f} · "
            f"accumulation {self.v137_ga.currentData()} · "
            f"warmup {self.v137_warmup.value():.2f} · "
            f"{self.v137_optimizer.currentText()} · "
            f"sauvegardes {self.v137_save.value()} · seed {self.v137_seed.value()}."
            + warning
        )

    def tuning(self):
        data = old_tuning()
        data.update(
            mode=self.v137_mode.currentData(),
            learning_rate=float(self.v137_lr.value()),
            gradient_accumulation=int(self.v137_ga.currentData()),
            warmup_ratio=float(self.v137_warmup.value()),
            optimizer=self.v137_optimizer.currentData(),
            save_limit=int(self.v137_save.value()),
            seed=int(self.v137_seed.value()),
        )
        return data

    def set_system_info(self, info):
        old_set_system_info(info)
        if self.v137_profile.currentData() == "auto":
            self.v137_apply_profile()
        else:
            self.v137_refresh_summary()

    tab.v137_auto_profile = MethodType(v137_auto_profile, tab)
    tab.v137_apply_profile = MethodType(v137_apply_profile, tab)
    tab.v137_refresh_summary = MethodType(v137_refresh_summary, tab)
    tab.tuning = MethodType(tuning, tab)
    tab.set_system_info = MethodType(set_system_info, tab)

    tab.v137_apply.clicked.connect(tab.v137_apply_profile)
    tab.v137_profile.currentIndexChanged.connect(tab.v137_apply_profile)

    for widget in (tab.v137_mode, tab.v137_ga, tab.v137_optimizer):
        widget.currentIndexChanged.connect(tab.v137_refresh_summary)
    for widget in (tab.v137_lr, tab.v137_warmup, tab.v137_save, tab.v137_seed):
        widget.valueChanged.connect(tab.v137_refresh_summary)

    tab.v137_apply_profile()
    window._v137_training = True
