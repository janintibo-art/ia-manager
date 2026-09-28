"""Jeux d'exemples et historique local de l'atelier."""
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone
import uuid
from src.backend import training_lab as lab


def normalize_examples(rows):
    clean, seen = [], set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Exemple {i} invalide.')
        values = [row.get(k, '') for k in ('instruction', 'input', 'output')]
        if not all(isinstance(v, str) for v in values):
            raise ValueError(f'Exemple {i} : texte attendu.')
        values = [v.strip() for v in values]
        if not values[0] or not values[2]:
            raise ValueError(f'Exemple {i} : question et réponse requises.')
        if sum(map(len, values)) > 16000:
            raise ValueError(f'Exemple {i} : maximum 16000 caractères.')
        key = tuple(values)
        if key not in seen:
            seen.add(key)
            clean.append(dict(zip(('instruction','input','output'), values)))
    if not clean: raise ValueError('Ajoutez au moins un exemple.')
    return clean


def save_examples(rows):
    rows = normalize_examples(rows)
    root = lab.lab_root()/'Exemples'
    root.mkdir(parents=True, exist_ok=True)
    path = root/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.jsonl')
    text = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows)
    if len(text.encode('utf-8')) > 50*1024*1024:
        raise ValueError('Jeu limité à 50 Mo.')
    with path.open('x', encoding='utf-8') as stream: stream.write(text)
    return path, len(rows)


def record_state(job, status, exit_code=None):
    if status not in ('running','success','failed','cancelled'):
        raise ValueError('Statut invalide')
    path = Path(job)/'state.json'
    temp = path.with_name('state-'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(json.dumps(dict(status=status, exit_code=exit_code,
            updated_at=datetime.now(timezone.utc).isoformat()), indent=2), encoding='utf-8')
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)


def read_object(path):
    try:
        if path.stat().st_size > 1024*1024: return {}
        value=json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError): return {}


def history(active=None, limit=200):
    root=lab.lab_root()
    if not root.exists(): return []
    result=[]
    paths=sorted((p for p in root.iterdir() if p.is_dir() and (p/'job.json').is_file()), reverse=True)
    for path in paths[:limit]:
        cfg=read_object(path/'job.json')
        if not cfg: continue
        state=read_object(path/'state.json').get('status','incomplete')
        if active and path.resolve()==Path(active).resolve(): state='running'
        elif state=='running': state='incomplete'
        elif (path/'SUCCESS').is_file() and state not in ('failed','cancelled'): state='success'
        evaluation=read_object(path/'evaluation.json')
        trial=read_object(path/'trial.json')
        result.append(dict(path=path, config=cfg, status=state, evaluation=evaluation, trial=trial,
            model_ready=state=='success' and (path/'model'/'config.json').is_file()
                and any((path/'model').glob('*.safetensors'))))
    return result


def metric(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
        return f'{value:.4f}'
    return '—'
