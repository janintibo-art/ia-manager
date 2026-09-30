"""Historique universel IA Manager."""
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock

ROOT = Path.home() / ".ia_manager"
FILE = ROOT / "universal_history.json"
_LOCK = RLock()


def _load():
    try:
        value = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save(rows):
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="history_", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(rows[:1000], stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, FILE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def list_events():
    with _LOCK:
        return list(_load())


def record(kind, title, detail="", status="info", path="", source="", event_id=""):
    """Ajoute ou met à jour un événement. event_id permet d'éviter les doublons d'import."""
    with _LOCK:
        rows = _load()
        eid = str(event_id or uuid.uuid4().hex)
        item = {
            "id": eid,
            "created": datetime.now().isoformat(timespec="seconds"),
            "kind": str(kind or "Autre"),
            "title": str(title or "Événement"),
            "detail": str(detail or ""),
            "status": str(status or "info"),
            "path": str(path or ""),
            "source": str(source or ""),
        }
        existing = next((i for i, row in enumerate(rows) if str(row.get("id")) == eid), None)
        if existing is None:
            rows.insert(0, item)
        else:
            created = rows[existing].get("created") or item["created"]
            item["created"] = created
            rows[existing] = item
        rows.sort(key=lambda x: str(x.get("created") or ""), reverse=True)
        _save(rows)
        return eid


def remove(event_id):
    with _LOCK:
        rows = [r for r in _load() if str(r.get("id")) != str(event_id)]
        _save(rows)


def clear():
    with _LOCK:
        _save([])


def import_existing():
    """Importe les historiques déjà présents sans les dupliquer."""
    imported = 0

    # Téléchargements historiques.
    try:
        from src.backend import download_history
        for row in download_history.list_entries():
            name = str(row.get("name") or "Modèle")
            source = str(row.get("source") or "Téléchargement")
            stamp = str(row.get("installed_at") or "")
            eid = "download:" + source + ":" + name + ":" + stamp
            path = str(row.get("path") or "")
            size = int(row.get("size") or 0)
            record(
                "Téléchargement",
                f"{name} téléchargé",
                f"Source : {source}" + (f" · {size / 2**30:.2f} Go" if size else ""),
                "success",
                path,
                source,
                eid,
            )
            imported += 1
    except Exception:
        pass

    # Benchmarks quantitatifs.
    try:
        root = Path.home() / ".ia_manager" / "benchmarks"
        for path in sorted(root.glob("benchmark-*.json"), reverse=True)[:200]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                models = ", ".join(data.get("models") or [])
                rows = len(data.get("rows") or [])
                created = str(data.get("created") or path.stem)
                record(
                    "Benchmark",
                    "Benchmark IA terminé",
                    f"{models or 'Modèle(s) inconnu(s)'} · {rows} test(s)",
                    "success",
                    str(path),
                    "Benchmark",
                    "bench:" + path.name,
                )
                imported += 1
            except Exception:
                pass

        qual = root / "qualitatif"
        for path in sorted(qual.glob("qualitatif-*.json"), reverse=True)[:200]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                before = str(data.get("before") or "")
                after = str(data.get("after") or "")
                summary = data.get("summary") or {}
                detail = f"{before} → {after}"
                if summary.get("scorable"):
                    detail += f" · {summary.get('scorable')} test(s) évaluables"
                record(
                    "Benchmark",
                    "Comparaison qualitative terminée",
                    detail,
                    "success",
                    str(path),
                    "Benchmark qualitatif",
                    "qual:" + path.name,
                )
                imported += 1
            except Exception:
                pass
    except Exception:
        pass

    # Historique entraînement / fusion.
    try:
        from src.backend import training_workspace
        for row in training_workspace.history(limit=300):
            cfg = row.get("config") or {}
            status = str(row.get("status") or "incomplete")
            action = str(cfg.get("action") or cfg.get("mode") or "Tâche ML")
            model = str(cfg.get("model") or cfg.get("model_a") or "")
            path = Path(row.get("path"))
            mapped = {
                "success": "success",
                "failed": "error",
                "cancelled": "warning",
                "running": "running",
                "incomplete": "warning",
            }.get(status, "info")
            record(
                "Entraînement",
                f"{action} · {status}",
                model or "Modèle non renseigné",
                mapped,
                str(path),
                "Atelier entraînement",
                "train:" + path.name,
            )
            imported += 1
    except Exception:
        pass

    # Journal d'erreurs : une entrée synthétique, pas chaque stacktrace.
    try:
        err = ROOT / "erreurs.log"
        if err.is_file() and err.stat().st_size:
            record(
                "Erreur",
                "Journal d'erreurs IA Manager",
                f"{err.stat().st_size / 1024:.0f} Ko enregistrés",
                "warning",
                str(err),
                "IA Manager",
                "error-log-summary",
            )
            imported += 1
    except Exception:
        pass

    return imported
