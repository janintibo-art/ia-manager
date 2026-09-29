"""Extension v135 : assistant intelligent de fusion MergeKit."""
import json
import re
import shutil
from pathlib import Path
from types import MethodType

from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from src.backend.system_analyzer import SystemAnalyzer
from src.backend import storage


def _gb(n):
    return float(n) / (1024 ** 3)


def _human_gb(value):
    return f"{value:.1f} Go"


def _folder_size(path):
    total = 0
    try:
        for p in Path(path).rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _read_local_config(value):
    try:
        path = Path(value).expanduser()
    except Exception:
        return None
    if not path.is_dir():
        return None
    config = path / "config.json"
    if not config.is_file():
        return {"path": str(path), "size_gb": _gb(_folder_size(path))}
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return {
        "path": str(path),
        "size_gb": _gb(_folder_size(path)),
        "model_type": str(data.get("model_type") or ""),
        "architectures": [str(x) for x in (data.get("architectures") or [])],
        "hidden_size": data.get("hidden_size"),
        "num_hidden_layers": data.get("num_hidden_layers"),
        "vocab_size": data.get("vocab_size"),
    }


def _params_from_name(value):
    text = (value or "").lower()
    hits = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*b(?![a-z])", text)
    if not hits:
        return None
    try:
        return float(hits[-1])
    except ValueError:
        return None


def _estimated_fp16_size(value):
    params_b = _params_from_name(value)
    if params_b is None:
        return None
    # Environ 2 octets/paramètre, hors tokenizer et métadonnées.
    return params_b * 2.0


def _describe_model(value):
    local = _read_local_config(value)
    if local:
        family = local.get("model_type") or (
            local.get("architectures", [""])[0] if local.get("architectures") else ""
        )
        return {
            "kind": "local",
            "size_gb": local.get("size_gb", 0.0),
            "family": family,
            "hidden_size": local.get("hidden_size"),
            "layers": local.get("num_hidden_layers"),
            "vocab": local.get("vocab_size"),
            "exact_size": True,
            "raw": local,
        }
    size = _estimated_fp16_size(value)
    family = ""
    low = (value or "").lower()
    for key in ("llama", "mistral", "qwen", "gemma", "phi", "deepseek"):
        if key in low:
            family = key
            break
    return {
        "kind": "remote",
        "size_gb": size,
        "family": family,
        "hidden_size": None,
        "layers": None,
        "vocab": None,
        "exact_size": False,
        "raw": None,
    }


def _compatible(a, b):
    # Si les deux configs locales sont disponibles, on peut être plus strict.
    if a["kind"] == "local" and b["kind"] == "local":
        af = (a.get("family") or "").lower()
        bf = (b.get("family") or "").lower()
        if af and bf and af != bf:
            return False, f"architectures différentes : {af} ≠ {bf}"
        for key, label in (
            ("hidden_size", "hidden size"),
            ("layers", "nombre de couches"),
        ):
            av, bv = a.get(key), b.get(key)
            if av and bv and av != bv:
                return False, f"{label} différent : {av} ≠ {bv}"
        return True, "configurations locales compatibles sur les principaux champs vérifiés"

    if a.get("family") and b.get("family"):
        if a["family"] != b["family"]:
            return None, (
                f"familles détectées différentes ({a['family']} / {b['family']}) ; "
                "compatibilité à confirmer par MergeKit"
            )
        return None, f"même famille apparente ({a['family']}) ; validation finale par MergeKit"

    return None, "compatibilité inconnue avant lecture des configs Hugging Face"


def _recommend_method(a, b):
    compatible, _ = _compatible(a, b)
    if compatible is False:
        return "linear", 0.5, 0.5, 0.5, (
            "Aucune méthode ne peut être recommandée tant que les architectures ne sont pas compatibles."
        )

    # Pour deux modèles seulement, SLERP est un choix conservateur si les familles semblent proches.
    if a.get("family") and a.get("family") == b.get("family"):
        return "slerp", 0.5, 0.5, 0.5, (
            "SLERP proposé : interpolation progressive entre deux checkpoints de même famille."
        )
    return "linear", 0.5, 0.5, 0.5, (
        "Linear proposé par défaut : méthode simple et lisible quand la relation exacte entre modèles est inconnue."
    )


def _estimate_workspace(a, b):
    sa, sb = a.get("size_gb"), b.get("size_gb")
    if not sa or not sb:
        return None
    # Entrées + sortie approximative + marge temporaire.
    out = max(sa, sb)
    return sa + sb + out * 1.35


def install_v135(window):
    tab = getattr(window, "mergekit_tab", None)
    if tab is None or getattr(window, "_v135_mergekit", False):
        return

    box = QGroupBox("Assistant intelligent de fusion")
    layout = QVBoxLayout(box)

    intro = QLabel(
        "Analyse le matériel et les deux modèles avant lancement. "
        "Les mesures locales sont exactes quand elles sont disponibles ; "
        "les besoins des modèles distants restent des estimations."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    row = QHBoxLayout()
    tab.v135_analyze = QPushButton("🧠 Analyser la fusion")
    tab.v135_analyze.setObjectName("Primary")
    row.addWidget(tab.v135_analyze)
    tab.v135_apply = QPushButton("✨ Appliquer les réglages conseillés")
    tab.v135_apply.setEnabled(False)
    row.addWidget(tab.v135_apply)
    row.addStretch()
    layout.addLayout(row)

    tab.v135_hardware = QLabel()
    tab.v135_hardware.setWordWrap(True)
    layout.addWidget(tab.v135_hardware)

    tab.v135_models = QLabel()
    tab.v135_models.setWordWrap(True)
    layout.addWidget(tab.v135_models)

    tab.v135_advice = QLabel("Renseignez les modèles A et B puis lancez l’analyse.")
    tab.v135_advice.setWordWrap(True)
    layout.addWidget(tab.v135_advice)

    # Inséré juste avant le bloc de préparation de fusion.
    tab.layout().insertWidget(2, box)

    tab.v135_recommendation = None

    def v135_analyze_merge(self):
        model_a = self.model_a.text().strip()
        model_b = self.model_b.text().strip()
        if not model_a or not model_b:
            self.v135_advice.setText("Renseignez d’abord les deux modèles à fusionner.")
            self.v135_apply.setEnabled(False)
            return

        try:
            hw = SystemAnalyzer.get_system_info(refresh=True)
        except Exception as exc:
            self.v135_advice.setText("Analyse du matériel impossible : " + str(exc))
            self.v135_apply.setEnabled(False)
            return

        a = _describe_model(model_a)
        b = _describe_model(model_b)
        compatibility, compat_text = _compatible(a, b)
        method, wa, wb, density, why = _recommend_method(a, b)

        vram = float(hw.get("vram_gb") or 0)
        ram = float(hw.get("ram_gb") or 0)
        free = _gb(shutil.disk_usage(storage.app_models()).free)
        workspace = _estimate_workspace(a, b)

        # MergeKit annonce pouvoir fonctionner sur CPU et avec aussi peu que 8 Go de VRAM,
        # mais la faisabilité exacte dépend de l'architecture et de la taille des checkpoints.
        if hw.get("gpu_vendor") == "NVIDIA" and vram >= 8:
            cuda = True
            execution = (
                f"CUDA plausible sur {hw.get('gpu_type')} ({vram:.1f} Go VRAM). "
                "MergeKit validera la faisabilité réelle au lancement."
            )
        else:
            cuda = False
            execution = (
                f"CPU conseillé avec {ram:.1f} Go de RAM ; CUDA non activé automatiquement."
            )

        def size_text(info):
            if info.get("size_gb") is None:
                return "taille inconnue"
            prefix = "" if info.get("exact_size") else "≈ "
            return prefix + _human_gb(info["size_gb"])

        self.v135_hardware.setText(
            f"🖥️ Matériel · {hw.get('cpu_count', '?')} threads CPU · "
            f"{ram:.1f} Go RAM · GPU {hw.get('gpu_type', 'inconnu')} · "
            f"{vram:.1f} Go VRAM · disque libre {free:.1f} Go."
        )
        self.v135_models.setText(
            f"📦 Modèle A : {size_text(a)}"
            + (f" · famille {a['family']}" if a.get("family") else "")
            + f"  |  Modèle B : {size_text(b)}"
            + (f" · famille {b['family']}" if b.get("family") else "")
            + f"\nCompatibilité : {compat_text}."
        )

        disk_text = (
            f"Espace de travail estimé : ≈ {workspace:.1f} Go."
            if workspace is not None
            else "Espace de travail : impossible à estimer sans connaître la taille des deux checkpoints."
        )
        disk_warning = ""
        if workspace is not None and free < workspace:
            disk_warning = (
                f" ⚠️ Espace libre insuffisant selon cette estimation ({free:.1f} Go disponibles)."
            )

        if compatibility is False:
            advice = (
                "⛔ Fusion déconseillée : " + compat_text + ". "
                "Choisissez deux checkpoints compatibles avant de continuer."
            )
            self.v135_apply.setEnabled(False)
        else:
            advice = (
                f"💡 Conseil · {why} {execution} {disk_text}{disk_warning}"
            )
            self.v135_apply.setEnabled(not (workspace is not None and free < workspace))

        self.v135_advice.setText(advice)
        self.v135_recommendation = {
            "method": method,
            "weight_a": wa,
            "weight_b": wb,
            "density": density,
            "cuda": cuda,
            "compatible": compatibility is not False,
        }

    def v135_apply_advice(self):
        rec = self.v135_recommendation or {}
        if not rec.get("compatible"):
            return
        idx = self.method.findData(rec.get("method"))
        if idx >= 0:
            self.method.setCurrentIndex(idx)
        self.weight_a.setValue(float(rec.get("weight_a", 0.5)))
        self.weight_b.setValue(float(rec.get("weight_b", 0.5)))
        self.density.setValue(float(rec.get("density", 0.5)))
        self.cuda.setChecked(bool(rec.get("cuda")))
        self.v135_advice.setText(
            "✅ Réglages appliqués. Vérifiez-les puis lancez la fusion quand vous êtes prêt."
        )

    tab.v135_analyze_merge = MethodType(v135_analyze_merge, tab)
    tab.v135_apply_advice = MethodType(v135_apply_advice, tab)
    tab.v135_analyze.clicked.connect(tab.v135_analyze_merge)
    tab.v135_apply.clicked.connect(tab.v135_apply_advice)

    window._v135_mergekit = True
