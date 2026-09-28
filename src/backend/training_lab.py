"""Atelier externe : aucune dépendance ML chargée dans l'interface."""
import json
from pathlib import Path
from src.backend import storage, training_resources as resources


def lab_root():
    return (storage.root() or Path.home() / '.ia_manager') / 'Entrainement'


def read_dataset(path, minimum=10):
    path = Path(path)
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError('Jeu limité à 50 Mo pour cette première version.')
    rows, seen = [], set()
    for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            question, answer = item['instruction'], item['output']
            context = item.get('input', '')
            if not all(isinstance(x, str) for x in (question, answer, context)):
                raise ValueError()
            if not question.strip() or not answer.strip():
                raise ValueError()
            if len(question) + len(answer) + len(context) > 16000:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ValueError(f'Ligne {line_no} invalide : instruction et output non vides, input facultatif, 16000 caractères maximum.') from None
        row = dict(instruction=question.strip(), input=context.strip(), output=answer.strip())
        key = json.dumps(row, sort_keys=True)
        if key not in seen:
            seen.add(key)
            rows.append(row)
    if len(rows) < minimum:
        raise ValueError(f'Au moins {minimum} exemples distincts requis (davantage conseillé).')
    return rows


# Code écrit dans chaque tâche : fonctionne aussi dans l'EXE PyInstaller.
RUNNER = r'''
import json, sys, subprocess, shutil, os
from pathlib import Path

job = Path(sys.argv[1]).resolve()
cfg = json.loads((job / 'job.json').read_text(encoding='utf-8'))
def run(args):
    subprocess.run(args, check=True)

def resource_report(torch=None):
    import importlib.metadata as md
    report = {'python': sys.version, 'cuda': False, 'versions': {},
              'disk_free_gb': shutil.disk_usage(job).free / 2**30}
    for name in ('torch', 'unsloth', 'trl', 'mergekit'):
        try: report['versions'][name] = md.version(name)
        except md.PackageNotFoundError: report['versions'][name] = 'absent'
    try:
        import psutil
        mem = psutil.virtual_memory()
        report.update(ram_gb=mem.total/2**30, ram_available_gb=mem.available/2**30)
    except ImportError:
        report['ram_note'] = 'psutil absent du moteur : RAM libre non mesurée'
    if torch is not None and torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info(0)
        report.update(cuda=True, gpu=torch.cuda.get_device_name(0),
            vram_free_gb=free/2**30, vram_gb=total/2**30)
    (job/'hardware.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    req = cfg.get('requirements') or {}
    for key, measured in (('vram_gb','vram_free_gb'), ('ram_gb','ram_available_gb'), ('disk_gb','disk_free_gb')):
        if req.get(key) and measured in report and report[measured] < req[key]:
            print('ATTENTION :', measured, 'sous le budget indicatif', req[key], 'Go. Risque de manque de mémoire/espace.', flush=True)
    if report['disk_free_gb'] < 1 and cfg['action'] != 'diagnostic':
        raise RuntimeError('Moins de 1 Go libre sur le disque de sortie : libérez de la place.')
    return report

if cfg['action'] == 'diagnostic':
    try:
        import torch
    except ImportError:
        torch = None
    report = resource_report(torch)
    if not report['cuda']:
        print('Entraînement indisponible dans ce moteur. La fusion CPU reste possible avec MergeKit.', flush=True)

elif cfg['action'] in ('train', 'trial'):
    from unsloth import FastLanguageModel, is_bfloat16_supported
    import torch
    from datasets import Dataset
    from trl import SFTTrainer, SFTConfig
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA requis. Lancez le diagnostic de l’atelier.')
    resource_report(torch)
    tuning = cfg['tuning']
    trial = cfg['action'] == 'trial'
    torch.cuda.reset_peak_memory_stats()
    rows = [json.loads(x) for x in (job / 'dataset.jsonl').read_text(encoding='utf-8').splitlines()]
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg['model'], max_seq_length=tuning['context'], load_in_4bit=True,
        dtype=None, trust_remote_code=False, device_map={'': 0})
    model = FastLanguageModel.get_peft_model(model, r=tuning['rank'],
        target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],
        lora_alpha=tuning['rank']*2, lora_dropout=0, bias='none',
        use_gradient_checkpointing='unsloth', random_state=42)
    texts = []
    for row in rows:
        user = row['instruction'] + ('\n\n' + row['input'] if row['input'] else '')
        text = tokenizer.apply_chat_template([
            {'role':'user','content':user}, {'role':'assistant','content':row['output']}],
            tokenize=False, add_generation_prompt=False)
        if len(tokenizer(text, add_special_tokens=False)['input_ids']) > tuning['context']:
            raise ValueError('Un exemple dépasse le contexte choisi ('+str(tuning['context'])+' tokens). Raccourcir cet exemple ou augmenter le contexte.')
        texts.append({'text':text})
    data = Dataset.from_list(texts).train_test_split(test_size=0.2, seed=42)
    args = SFTConfig(output_dir=str(job/'checkpoints'), max_length=tuning['context'],
        dataset_text_field='text', per_device_train_batch_size=tuning['batch'],
        per_device_eval_batch_size=1, gradient_accumulation_steps=max(1, 8//tuning['batch']),
        num_train_epochs=cfg['epochs'], max_steps=2 if trial else -1, learning_rate=0.0001,
        warmup_ratio=0.05, logging_steps=1, save_strategy='no' if trial else 'epoch',
        eval_strategy='no' if trial else 'epoch', save_total_limit=2, report_to='none',
        optim='adamw_8bit', fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(), seed=42, dataset_num_proc=1,
        dataloader_num_workers=0, packing=False)
    trainer = SFTTrainer(model=model, processing_class=tokenizer, args=args,
        train_dataset=data['train'], eval_dataset=data['test'])
    if trial:
        trainer.train()
        result = {'status':'success', 'steps':2,
                  'peak_allocated_gb':torch.cuda.max_memory_allocated()/2**30,
                  'peak_reserved_gb':torch.cuda.max_memory_reserved()/2**30,
                  'tuning':tuning,
                  'note':'Essai limité à deux étapes ; export complet et totalité des exemples non validés.'}
        (job/'trial.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        (job/'SUCCESS').write_text('trial', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return
    before = trainer.evaluate()
    trainer.train()
    after = trainer.evaluate()
    model.save_pretrained(str(job/'adapter'))
    tokenizer.save_pretrained(str(job/'adapter'))
    (job/'evaluation.json').write_text(json.dumps({'before':before,'after':after}, indent=2), encoding='utf-8')
    print('Adaptateur sauvegardé. Export du modèle complet...', flush=True)
    model.save_pretrained_merged(str(job/'model'), tokenizer, save_method='merged_16bit')
    print('Modèle exporté ; comparer sa qualité avant de remplacer le modèle habituel.', flush=True)

elif cfg['action'] == 'merge':
    resource_report()
    from transformers import AutoConfig, AutoTokenizer
    a, b = cfg['model'], cfg['other']
    configs = [AutoConfig.from_pretrained(x, trust_remote_code=False).to_dict() for x in (a,b)]
    keys = ('model_type','architectures','hidden_size','intermediate_size',
        'num_hidden_layers','num_attention_heads','num_key_value_heads','vocab_size',
        'head_dim','rope_theta','rope_scaling','tie_word_embeddings')
    for key in keys:
        if configs[0].get(key) != configs[1].get(key):
            raise ValueError('Fusion refusée : configurations différentes pour ' + key)
    if any(c.get('quantization_config') for c in configs):
        raise ValueError('Utiliser deux modèles Safetensors non quantifiés, pas GGUF/AWQ/GPTQ/4-bit.')
    tokens = [AutoTokenizer.from_pretrained(x, trust_remote_code=False) for x in (a,b)]
    if tokens[0].get_vocab() != tokens[1].get_vocab() or tokens[0].special_tokens_map != tokens[1].special_tokens_map:
        raise ValueError('Fusion refusée : tokenizers différents.')
    recipe = {'merge_method':'linear', 'dtype':'float16',
        'models':[{'model':a,'parameters':{'weight':1-cfg['weight']}},
                  {'model':b,'parameters':{'weight':cfg['weight']}}],
        'parameters':{'normalize':True}, 'tokenizer_source':a}
    if cfg.get('merge_method') == 'slerp':
        recipe = {'merge_method':'slerp', 'dtype':'float16', 'base_model':a,
                  'models':[{'model':b}], 'parameters':{'t':cfg['weight']},
                  'tokenizer_source':a}
    (job/'merge.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
    exe = Path(sys.executable).parent / ('mergekit-yaml.exe' if os.name == 'nt' else 'mergekit-yaml')
    if not exe.is_file():
        raise RuntimeError('MergeKit absent de cet environnement Python.')
    run([str(exe), str(job/'merge.json'), str(job/'model'), '--copy-tokenizer'])

else:
    raise ValueError('Action inconnue')
(job/'SUCCESS').write_text(cfg['action'], encoding='utf-8')
print('Opération terminée.', flush=True)
'''


# Windows : les éventuels processus enfants ne relancent pas la tâche.
RUNNER = 'def main():\n' + '\n'.join('    ' + line for line in RUNNER.splitlines()) + '\n\nif __name__ == \"__main__\":\n    main()\n'


def create_job(action, model='', other='', dataset='', epochs=1, weight=.5, tuning=None, hardware=None, merge_method="linear"):
    from datetime import datetime
    import uuid
    if action not in ('train', 'trial', 'merge', 'diagnostic'):
        raise ValueError('Action inconnue')
    if action != 'diagnostic' and (not model.strip() or model.startswith('-')):
        raise ValueError('Indiquez un identifiant Hugging Face ou un dossier de modèle.')
    if action == 'merge' and (not other.strip() or other == model or other.startswith('-')):
        raise ValueError('Choisissez deux modèles différents issus de la même base.')
    if not 1 <= epochs <= 3 or not 0 < weight < 1:
        raise ValueError('Réglages hors limites')
    tuning = dict(tuning or {'context':1024, 'rank':8, 'batch':1})
    if set(tuning) != {'context', 'rank', 'batch'} or any(type(x) is not int for x in tuning.values()):
        raise ValueError('Réglages d’entraînement invalides')
    if tuning['context'] not in (512, 1024, 2048, 4096) or tuning['rank'] not in (4, 8, 16, 32) or tuning['batch'] not in (1, 2, 4):
        raise ValueError('Réglages d’entraînement hors limites')
    if merge_method not in ('linear','slerp'):
        raise ValueError('Méthode de fusion inconnue')
    rows = read_dataset(dataset) if action in ('train', 'trial') else None
    root = lab_root() / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    root.mkdir(parents=True)
    config = dict(action=action, model=model.strip(), other=other.strip(), epochs=epochs, weight=weight,
                  tuning=tuning, hardware_at_creation=hardware or {}, merge_method=merge_method,
                  requirements=resources.requirements(model, **tuning, action=action))
    (root/'job.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    (root/'runner.py').write_text(RUNNER, encoding='utf-8')
    if rows:
        (root/'dataset.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
    return root


def import_modelfile(folder, name):
    import re
    folder = Path(folder).resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,63}', name):
        raise ValueError('Nom : lettres minuscules, chiffres, tirets ou points (64 caractères maximum).')
    if not (folder/'config.json').is_file() or not list(folder.glob('*.safetensors')):
        raise ValueError('Choisissez le dossier model exporté, contenant config.json et des poids Safetensors.')
    target = lab_root()/'imports'
    target.mkdir(parents=True, exist_ok=True)
    import uuid
    path = target/(uuid.uuid4().hex + '.Modelfile')
    path.write_text('FROM '+json.dumps(folder.as_posix(), ensure_ascii=False)+'\nPARAMETER num_ctx 4096\n', encoding='utf-8')
    return path
