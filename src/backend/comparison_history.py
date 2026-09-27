"""Historique local des comparaisons, écrit atomiquement."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

HISTORY_DIR = Path.home() / '.ia_manager' / 'comparisons'


def save(prompt, responses, root=None):
    root = Path(root) if root is not None else HISTORY_DIR
    root.mkdir(parents=True, exist_ok=True)
    record = {'id': uuid4().hex, 'created_at': datetime.now(timezone.utc).isoformat(),
              'prompt': prompt, 'responses': responses}
    destination = root / (record['id'] + '.json')
    fd, temporary = tempfile.mkstemp(prefix='comparison-', suffix='.tmp', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return record


def list_saved(root=None, limit=30):
    root = Path(root) if root is not None else HISTORY_DIR
    records = []
    for file in sorted(root.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            record = json.loads(file.read_text(encoding='utf-8'))
            if record.get('id') == file.stem and isinstance(record.get('responses'), list):
                records.append(record)
        except (OSError, ValueError, TypeError):
            continue
    return records


def remove(record_id, root=None):
    root = Path(root) if root is not None else HISTORY_DIR
    if len(record_id) != 32 or any(ch not in '0123456789abcdef' for ch in record_id):
        raise ValueError('Identifiant de comparaison incorrect.')
    (root / (record_id + '.json')).unlink()
