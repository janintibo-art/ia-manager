"""Tâches planifiées : une consigne envoyée à une IA à heure fixe.

Les tâches tournent tant qu'IA Manager est ouvert (la fenêtre peut être réduite
dans la zone de notification, près de l'horloge).
Enregistrées dans ~/.ia_manager/config/taches.json ; résultats dans ~/.ia_manager/taches/.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from src.backend import code_tools
from src.backend.project_manager import ProjectManager, now_iso, slugify

TASKS_FILE = Path.home() / ".ia_manager" / "config" / "taches.json"
RESULTS_DIR = Path.home() / ".ia_manager" / "taches"

SCHEDULES = {
    "once": "Une seule fois",
    "daily": "Chaque jour",
    "weekly": "Chaque semaine",
    "hours": "Toutes les N heures",
    "minutes": "Toutes les N minutes",
}
DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def new_task() -> Dict:
    return {
        "id": uuid.uuid4().hex[:10],
        "name": "Nouvelle tâche",
        "prompt": "",
        "model": "",
        "project": "",
        "schedule": "daily",
        "at": (datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0).isoformat(),
        "time": "08:00",
        "weekday": 0,
        "interval": 6,
        "enabled": True,
        "make_zip": False,
        "last_run": "",
        "last_status": "",
        "next_run": "",
    }


def _parse_time(text: str) -> tuple:
    try:
        h, m = text.split(":")[:2]
        return max(0, min(23, int(h))), max(0, min(59, int(m)))
    except Exception:
        return 8, 0


def compute_next_run(task: Dict, after: Optional[datetime] = None) -> Optional[datetime]:
    """Prochaine exécution strictement après `after` (None = plus jamais)"""
    after = (after or datetime.now()).replace(microsecond=0)
    kind = task.get("schedule", "daily")

    if kind == "once":
        try:
            at = datetime.fromisoformat(task.get("at", ""))
        except ValueError:
            return None
        if task.get("last_run"):
            return None
        return at

    if kind in ("hours", "minutes"):
        n = max(1, int(task.get("interval") or 1))
        if kind == "minutes":
            n = max(5, n)
        step = timedelta(hours=n) if kind == "hours" else timedelta(minutes=n)
        last = task.get("last_run")
        if last:
            try:
                nxt = datetime.fromisoformat(last) + step
                return nxt if nxt > after else after + timedelta(seconds=30)
            except ValueError:
                pass
        return after + step

    h, m = _parse_time(task.get("time", "08:00"))
    candidate = after.replace(hour=h, minute=m, second=0)
    if kind == "daily":
        if candidate <= after:
            candidate += timedelta(days=1)
        return candidate
    if kind == "weekly":
        wd = int(task.get("weekday", 0)) % 7
        days_ahead = (wd - after.weekday()) % 7
        candidate = candidate + timedelta(days=days_ahead)
        if candidate <= after:
            candidate += timedelta(days=7)
        return candidate
    return None


def describe(task: Dict) -> str:
    kind = task.get("schedule")
    if kind == "once":
        try:
            return "Le " + datetime.fromisoformat(task["at"]).strftime("%d/%m/%Y à %H:%M")
        except (KeyError, ValueError):
            return "Une fois"
    if kind == "daily":
        return f"Chaque jour à {task.get('time', '08:00')}"
    if kind == "weekly":
        return f"Chaque {DAYS[int(task.get('weekday', 0)) % 7].lower()} à {task.get('time', '08:00')}"
    if kind == "hours":
        return f"Toutes les {task.get('interval', 1)} h"
    if kind == "minutes":
        return f"Toutes les {max(5, int(task.get('interval', 5)))} min"
    return kind or ""


class TaskStore:
    def __init__(self, path: Path = TASKS_FILE):
        self.path = path

    def load(self) -> List[Dict]:
        try:
            tasks = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
        out = []
        for t in tasks:
            base = new_task()
            base.update(t)
            out.append(base)
        return out

    def save_all(self, tasks: List[Dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, task: Dict) -> None:
        tasks = [t for t in self.load() if t["id"] != task["id"]]
        nxt = compute_next_run(task)
        task["next_run"] = nxt.isoformat() if nxt and task.get("enabled") else ""
        tasks.append(task)
        self.save_all(tasks)

    def delete(self, tid: str) -> None:
        self.save_all([t for t in self.load() if t["id"] != tid])

    def due_tasks(self, now: Optional[datetime] = None) -> List[Dict]:
        now = now or datetime.now()
        due = []
        for t in self.load():
            if not t.get("enabled") or not t.get("next_run"):
                continue
            try:
                if datetime.fromisoformat(t["next_run"]) <= now:
                    due.append(t)
            except ValueError:
                continue
        return due

    def mark_done(self, tid: str, status: str, when: Optional[datetime] = None) -> None:
        when = when or datetime.now()
        tasks = self.load()
        for t in tasks:
            if t["id"] == tid:
                t["last_run"] = when.replace(microsecond=0).isoformat()
                t["last_status"] = status
                nxt = compute_next_run(t, when)
                t["next_run"] = nxt.isoformat() if nxt else ""
                if t["schedule"] == "once":
                    t["enabled"] = False
        self.save_all(tasks)


def save_result(task: Dict, answer: str, projects_root: str) -> Dict[str, str]:
    """Enregistre le résultat : fichier .md, discussion dans le projet, zip du code si demandé"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    md = RESULTS_DIR / f"{slugify(task['name'])}_{stamp}.md"
    md.write_text(f"# {task['name']}\n\n{datetime.now():%d/%m/%Y %H:%M} — {task['model']}\n\n"
                  f"## Consigne\n\n{task['prompt']}\n\n## Réponse\n\n{answer}\n", encoding="utf-8")
    out = {"markdown": str(md)}

    pm = None
    if task.get("project"):
        pm = ProjectManager(projects_root)
        if pm.get(task["project"]):
            pm.save_conversation(task["project"], {
                "title": f"⏰ {task['name']} — {datetime.now():%d/%m %H:%M}",
                "model": task["model"],
                "created": now_iso(),
                "messages": [{"role": "user", "content": task["prompt"]},
                             {"role": "assistant", "content": answer}],
            })
            out["project"] = task["project"]
        else:
            pm = None

    if task.get("make_zip"):
        blocks = code_tools.extract_code_blocks(answer)
        if blocks:
            folder = pm.files_folder(task["project"]) if pm else RESULTS_DIR
            z = code_tools.build_zip(blocks, str(folder / f"{slugify(task['name'])}_{stamp}.zip"),
                                     slugify(task["name"]))
            out["zip"] = str(z)
    return out


def list_results(limit: int = 50) -> List[Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
