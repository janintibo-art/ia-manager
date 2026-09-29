from pathlib import Path
from types import MethodType
import json, os
from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl
from PyQt6.QtGui import QTextCursor, QDesktopServices
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout
from src.backend import local_jobs, storage
from src.ui import v132_extension as mk

def _script(name):
    root = mk._tool_root() / ".venv"
    return root / ("Scripts/" + name + ".exe" if os.name == "nt" else "bin/" + name)

def _advanced_root():
    p = Path.home() / ".ia_manager" / "mergekit" / "advanced"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _yaml(v):
    return json.dumps((v or "").strip(), ensure_ascii=False)

def _moe_config(base, expert1, expert2, prompt1, prompt2, gate):
    if not base or not expert1 or not expert2:
        raise ValueError("Renseignez le modèle de base et les deux experts.")
    lines = [f"base_model: {_yaml(base)}", f"gate_mode: {gate}", "dtype: bfloat16", "experts:", f"  - source_model: {_yaml(expert1)}"]
    if prompt1.strip():
        lines += ["    positive_prompts:", f"      - {_yaml(prompt1)}"]
    lines += [f"  - source_model: {_yaml(expert2)}"]
    if prompt2.strip():
        lines += ["    positive_prompts:", f"      - {_yaml(prompt2)}"]
    return "\n".join(lines) + "\n"

MULTI_TEMPLATE = """name: etape-1
merge_method: linear
models:
  - model: "MODELE_A"
    parameters:
      weight: 0.5
  - model: "MODELE_B"
    parameters:
      weight: 0.5
dtype: float16
tokenizer:
  source: "union"
---
merge_method: slerp
base_model: etape-1
models:
  - model: etape-1
  - model: "MODELE_C"
parameters:
  t: 0.5
dtype: float16
tokenizer:
  source: "union"
"""

def install_v134(window):
    tab = getattr(window, "mergekit_tab", None)
    if tab is None or getattr(window, "_v134_mergekit", False):
        return

    tab.v134_process = QProcess(tab)
    tab.v134_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    tab.v134_resource_token = None
    tab.v134_mode = ""
    tab.v134_last_output = ""

    moe = QGroupBox("4 · MergeKit MoE")
    ml = QVBoxLayout(moe)
    h = QLabel("Créez un Mixture of Experts à partir de modèles Llama ou Mistral de même taille.")
    h.setWordWrap(True); ml.addWidget(h)
    f = QFormLayout()
    tab.v134_moe_base = QLineEdit(); f.addRow("Base", tab.v134_moe_base)
    tab.v134_moe_e1 = QLineEdit(); f.addRow("Expert 1", tab.v134_moe_e1)
    tab.v134_moe_p1 = QLineEdit(); f.addRow("Prompt expert 1", tab.v134_moe_p1)
    tab.v134_moe_e2 = QLineEdit(); f.addRow("Expert 2", tab.v134_moe_e2)
    tab.v134_moe_p2 = QLineEdit(); f.addRow("Prompt expert 2", tab.v134_moe_p2)
    tab.v134_moe_gate = QComboBox()
    tab.v134_moe_gate.addItem("Hidden · meilleure qualité","hidden")
    tab.v134_moe_gate.addItem("Cheap embed · plus léger","cheap_embed")
    tab.v134_moe_gate.addItem("Random · entraînement ultérieur","random")
    f.addRow("Routage", tab.v134_moe_gate)
    tab.v134_moe_name = QLineEdit("fusion-moe"); f.addRow("Nom de sortie", tab.v134_moe_name)
    tab.v134_moe_4bit = QCheckBox("Charger le routeur en 4 bits"); f.addRow(tab.v134_moe_4bit)
    ml.addLayout(f)
    r = QHBoxLayout()
    tab.v134_moe_preview = QPushButton("👁 Voir le YAML MoE"); r.addWidget(tab.v134_moe_preview)
    tab.v134_moe_run = QPushButton("▶ Créer le MoE"); tab.v134_moe_run.setObjectName("Primary"); r.addWidget(tab.v134_moe_run)
    r.addStretch(); ml.addLayout(r)
    tab.v134_moe_status = QLabel("Prêt."); ml.addWidget(tab.v134_moe_status)

    lora = QGroupBox("5 · Extraire un LoRA")
    ll = QVBoxLayout(lora)
    h = QLabel("Extrait un LoRA des différences entre un modèle fine-tuné et son modèle de base.")
    h.setWordWrap(True); ll.addWidget(h)
    f = QFormLayout()
    tab.v134_lora_model = QLineEdit(); f.addRow("Modèle fine-tuné", tab.v134_lora_model)
    tab.v134_lora_base = QLineEdit(); f.addRow("Modèle de base", tab.v134_lora_base)
    tab.v134_lora_name = QLineEdit("lora-extrait"); f.addRow("Nom de sortie", tab.v134_lora_name)
    tab.v134_lora_rank = QSpinBox(); tab.v134_lora_rank.setRange(1,512); tab.v134_lora_rank.setValue(64); f.addRow("Rang max", tab.v134_lora_rank)
    tab.v134_lora_cuda = QCheckBox("Utiliser CUDA"); f.addRow(tab.v134_lora_cuda)
    ll.addLayout(f)
    r = QHBoxLayout()
    tab.v134_lora_run = QPushButton("▶ Extraire le LoRA"); tab.v134_lora_run.setObjectName("Primary"); r.addWidget(tab.v134_lora_run)
    r.addStretch(); ll.addLayout(r)
    tab.v134_lora_status = QLabel("Prêt."); ll.addWidget(tab.v134_lora_status)

    multi = QGroupBox("6 · Fusion multi-étapes")
    m = QVBoxLayout(multi)
    h = QLabel("Chaînez plusieurs fusions. Les étapes nommées peuvent être réutilisées dans les suivantes.")
    h.setWordWrap(True); m.addWidget(h)
    tab.v134_multi_yaml = QPlainTextEdit(); tab.v134_multi_yaml.setPlainText(MULTI_TEMPLATE); tab.v134_multi_yaml.setMinimumHeight(260); m.addWidget(tab.v134_multi_yaml)
    r = QHBoxLayout()
    tab.v134_multi_name = QLineEdit("fusion-multi"); r.addWidget(QLabel("Nom final")); r.addWidget(tab.v134_multi_name,1)
    tab.v134_multi_cuda = QCheckBox("CUDA"); r.addWidget(tab.v134_multi_cuda)
    tab.v134_multi_run = QPushButton("▶ Lancer les étapes"); tab.v134_multi_run.setObjectName("Primary"); r.addWidget(tab.v134_multi_run)
    m.addLayout(r)
    tab.v134_multi_status = QLabel("Prêt."); m.addWidget(tab.v134_multi_status)

    controls = QHBoxLayout()
    tab.v134_stop = QPushButton("■ Arrêter l’outil avancé"); tab.v134_stop.setObjectName("Danger"); controls.addWidget(tab.v134_stop)
    tab.v134_open = QPushButton("📁 Ouvrir la dernière sortie avancée"); controls.addWidget(tab.v134_open)
    controls.addStretch()

    root = tab.layout()
    insert_at = max(0, root.count()-2)
    root.insertWidget(insert_at, moe); root.insertWidget(insert_at+1, lora); root.insertWidget(insert_at+2, multi); root.insertLayout(insert_at+3, controls)

    def busy(self):
        return self.v134_process.state() != QProcess.ProcessState.NotRunning

    def set_busy(self, b):
        for w in (self.v134_moe_run,self.v134_moe_preview,self.v134_lora_run,self.v134_multi_run,self.v134_moe_base,self.v134_moe_e1,self.v134_moe_e2,self.v134_moe_p1,self.v134_moe_p2,self.v134_moe_gate,self.v134_moe_name,self.v134_moe_4bit,self.v134_lora_model,self.v134_lora_base,self.v134_lora_name,self.v134_lora_rank,self.v134_lora_cuda,self.v134_multi_yaml,self.v134_multi_name,self.v134_multi_cuda):
            w.setEnabled(not b)
        self.v134_stop.setEnabled(b)
        self.v134_open.setEnabled((not b) and bool(self.v134_last_output) and Path(self.v134_last_output).exists())

    def start(self, program, args, mode, output):
        if self.v134_busy(): return
        if not Path(program).exists():
            getattr(self, f"v134_{mode}_status").setText("Commande MergeKit introuvable. Réinstallez MergeKit.")
            return
        if local_jobs.enabled():
            self.v134_resource_token = local_jobs.reserve("MergeKit "+mode)
            if self.v134_resource_token is None:
                getattr(self, f"v134_{mode}_status").setText("Un autre travail local utilise déjà les ressources.")
                return
        self.v134_mode = mode; self.v134_last_output = str(output); self.log.clear(); self.v134_set_busy(True)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED","1"); env.insert("PYTHONIOENCODING","utf-8"); env.insert("HF_HUB_DISABLE_TELEMETRY","1"); env.insert("TOKENIZERS_PARALLELISM","false")
        self.v134_process.setProcessEnvironment(env); self.v134_process.setWorkingDirectory(str(mk._tool_root()))
        self.v134_process.start(str(program), list(args))

    def moe_yaml(self):
        return _moe_config(self.v134_moe_base.text(),self.v134_moe_e1.text(),self.v134_moe_e2.text(),self.v134_moe_p1.text(),self.v134_moe_p2.text(),self.v134_moe_gate.currentData())

    def preview_moe(self):
        try:
            self.log.setPlainText(self.v134_moe_yaml()); self.v134_moe_status.setText("YAML MoE généré.")
        except Exception as e: self.v134_moe_status.setText(str(e))

    def run_moe(self):
        try: y = self.v134_moe_yaml()
        except Exception as e: self.v134_moe_status.setText(str(e)); return
        name = mk._safe_name(self.v134_moe_name.text()); out = storage.app_models()/ "Fusionnes"/name
        if out.exists() and any(out.iterdir()): self.v134_moe_status.setText("Le dossier de sortie existe déjà."); return
        out.mkdir(parents=True, exist_ok=True)
        cfg = _advanced_root()/f"{name}-moe.yml"; cfg.write_text(y,encoding="utf-8")
        args=[str(cfg),str(out)]
        if self.v134_moe_4bit.isChecked(): args.append("--load-in-4bit")
        self.v134_moe_status.setText("Création du MoE en cours…"); self.v134_start(_script("mergekit-moe"),args,"moe",out)

    def run_lora(self):
        model=self.v134_lora_model.text().strip(); base=self.v134_lora_base.text().strip()
        if not model or not base: self.v134_lora_status.setText("Renseignez le modèle et sa base."); return
        name=mk._safe_name(self.v134_lora_name.text()); out=storage.app_models()/ "LoRA"/name
        if out.exists() and any(out.iterdir()): self.v134_lora_status.setText("Le dossier LoRA existe déjà."); return
        out.mkdir(parents=True, exist_ok=True)
        args=["--model",model,"--base-model",base,"--out-path",str(out),f"--max-rank={self.v134_lora_rank.value()}"]
        if self.v134_lora_cuda.isChecked(): args.append("--cuda")
        self.v134_lora_status.setText("Extraction LoRA en cours…"); self.v134_start(_script("mergekit-extract-lora"),args,"lora",out)

    def run_multi(self):
        txt=self.v134_multi_yaml.toPlainText().strip()
        if not txt: self.v134_multi_status.setText("Le YAML est vide."); return
        name=mk._safe_name(self.v134_multi_name.text()); base=storage.app_models()/ "Fusionnes"; out=base/name; inter=base/(name+"-intermediaires")
        if out.exists() and any(out.iterdir()): self.v134_multi_status.setText("Le dossier final existe déjà."); return
        out.mkdir(parents=True, exist_ok=True); inter.mkdir(parents=True, exist_ok=True)
        cfg=_advanced_root()/f"{name}-multi.yml"; cfg.write_text(txt+"\n",encoding="utf-8")
        args=[str(cfg),"--intermediate-dir",str(inter),"--out-path",str(out)]
        if self.v134_multi_cuda.isChecked(): args.append("--cuda")
        self.v134_multi_status.setText("Fusion multi-étapes en cours…"); self.v134_start(_script("mergekit-multi"),args,"multi",out)

    def read_output(self):
        t=bytes(self.v134_process.readAllStandardOutput()).decode("utf-8",errors="replace")
        if t: self.log.moveCursor(QTextCursor.MoveOperation.End); self.log.insertPlainText(t)

    def finished(self,code,status):
        self.v134_read_output(); local_jobs.release(self.v134_resource_token); self.v134_resource_token=None
        ok=code==0 and status==QProcess.ExitStatus.NormalExit; mode=self.v134_mode; self.v134_mode=""
        st=getattr(self,f"v134_{mode}_status")
        if ok:
            st.setText("✅ Terminé · sortie : "+self.v134_last_output)
            if mode in {"moe","multi"} and hasattr(self,"v133_source"):
                self.v133_source.setText(self.v134_last_output); self.v133_name.setText(mk._safe_name(Path(self.v134_last_output).name.lower())); self.v133_status.setText("✅ Sortie avancée prête pour conversion GGUF / Ollama.")
        else:
            st.setText(f"❌ Échec MergeKit avancé (code {code}). Consultez le journal.")
        self.v134_set_busy(False)

    def failed(self,_):
        local_jobs.release(self.v134_resource_token); self.v134_resource_token=None
        mode=self.v134_mode; self.v134_mode=""
        getattr(self,f"v134_{mode}_status").setText("Démarrage impossible : "+self.v134_process.errorString()); self.v134_set_busy(False)

    def stop(self):
        if self.v134_busy(): self.v134_process.terminate()

    def open_out(self):
        if self.v134_last_output and Path(self.v134_last_output).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.v134_last_output))

    tab.v134_busy=MethodType(busy,tab); tab.v134_set_busy=MethodType(set_busy,tab); tab.v134_start=MethodType(start,tab)
    tab.v134_moe_yaml=MethodType(moe_yaml,tab); tab.v134_preview_moe=MethodType(preview_moe,tab); tab.v134_run_moe=MethodType(run_moe,tab)
    tab.v134_run_lora=MethodType(run_lora,tab); tab.v134_run_multi=MethodType(run_multi,tab); tab.v134_read_output=MethodType(read_output,tab)
    tab.v134_finished=MethodType(finished,tab); tab.v134_failed=MethodType(failed,tab); tab.v134_stop_run=MethodType(stop,tab); tab.v134_open_output=MethodType(open_out,tab)

    tab.v134_process.readyReadStandardOutput.connect(tab.v134_read_output); tab.v134_process.finished.connect(tab.v134_finished); tab.v134_process.errorOccurred.connect(tab.v134_failed)
    tab.v134_moe_preview.clicked.connect(tab.v134_preview_moe); tab.v134_moe_run.clicked.connect(tab.v134_run_moe); tab.v134_lora_run.clicked.connect(tab.v134_run_lora); tab.v134_multi_run.clicked.connect(tab.v134_run_multi); tab.v134_stop.clicked.connect(tab.v134_stop_run); tab.v134_open.clicked.connect(tab.v134_open_output)

    old_shutdown=tab.shutdown
    def shutdown(self):
        local_jobs.release(self.v134_resource_token); self.v134_resource_token=None
        if self.v134_process.state()!=QProcess.ProcessState.NotRunning:
            self.v134_process.terminate()
            if not self.v134_process.waitForFinished(1500): self.v134_process.kill(); self.v134_process.waitForFinished(1500)
        old_shutdown()
    tab.shutdown=MethodType(shutdown,tab)
    tab.v134_set_busy(False); window._v134_mergekit=True
