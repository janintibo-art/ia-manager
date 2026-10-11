"""Skills : consignes prêtes à l'emploi, regroupées en plugins, activables dans le Chat.

Le catalogue intégré est dans skills_catalog.py. Les skills de l'utilisateur et les skills activées
sont enregistrées dans les réglages ("skills_user", "skills_enabled").
"""

import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.backend import settings
from src.backend.skills_catalog import PLUGINS

USER_PLUGIN = "mes-skills"
USER_PLUGIN_NAME = "Mes skills"
MAX_PROMPT_CHARS = 8000       # taille maximale d'une skill
MAX_ACTIVE_CHARS = 6000       # au-delà, les skills actives sont tronquées (protège les petits modèles)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower().replace("é", "e").replace("è", "e")
               .replace("ê", "e").replace("à", "a").replace("ç", "c").replace("ù", "u")
               .replace("î", "i").replace("ô", "o")).strip("-")
    return s[:40] or "skill"


# ------------------------------------------------------------------ lecture du catalogue
def builtin_skills() -> List[Dict]:
    out = []
    for p in PLUGINS:
        for sid, name, desc, prompt in p["skills"]:
            out.append({"id": sid, "name": name, "desc": desc, "prompt": prompt,
                        "plugin": p["id"], "builtin": True})
    return out


def user_skills() -> List[Dict]:
    out = []
    for s in settings.get("skills_user") or []:
        if isinstance(s, dict) and s.get("id") and s.get("prompt"):
            out.append({"id": s["id"], "name": s.get("name") or s["id"], "desc": s.get("desc", ""),
                        "prompt": s["prompt"], "plugin": USER_PLUGIN, "builtin": False})
    return out


def all_skills() -> List[Dict]:
    return builtin_skills() + user_skills()


def plugins() -> List[Dict]:
    """Plugins avec le nombre de skills et le nombre de skills actives"""
    enabled = enabled_ids()
    result = []
    for p in PLUGINS:
        ids = [s[0] for s in p["skills"]]
        result.append({"id": p["id"], "name": p["name"], "icon": p["icon"], "desc": p["desc"],
                       "count": len(ids), "active": sum(1 for i in ids if i in enabled)})
    mine = user_skills()
    result.append({"id": USER_PLUGIN, "name": USER_PLUGIN_NAME, "icon": "⭐",
                   "desc": "Vos propres skills, créées ou importées.", "count": len(mine),
                   "active": sum(1 for s in mine if s["id"] in enabled)})
    return result


def get_skill(sid: str) -> Optional[Dict]:
    return next((s for s in all_skills() if s["id"] == sid), None)


def search(skills: List[Dict], query: str) -> List[Dict]:
    words = [w for w in (query or "").lower().split() if w]
    if not words:
        return skills
    return [s for s in skills
            if all(w in f"{s['name']} {s['desc']} {s['prompt']}".lower() for w in words)]


# ------------------------------------------------------------------ activation
def enabled_ids() -> set:
    return set(settings.get("skills_enabled") or [])


def set_enabled(sid: str, on: bool) -> None:
    ids = enabled_ids()
    (ids.add if on else ids.discard)(sid)
    settings.set("skills_enabled", sorted(ids))


def set_plugin_enabled(plugin_id: str, on: bool) -> int:
    """Installe (active tout) ou retire (désactive tout) un plugin. Renvoie le nombre de skills touchées."""
    ids = enabled_ids()
    targets = [s["id"] for s in all_skills() if s["plugin"] == plugin_id]
    for sid in targets:
        (ids.add if on else ids.discard)(sid)
    settings.set("skills_enabled", sorted(ids))
    return len(targets)


def active_skills() -> List[Dict]:
    ids = enabled_ids()
    return [s for s in all_skills() if s["id"] in ids]


def active_instructions() -> str:
    """Texte ajouté aux instructions de l'IA ('' si aucune skill active)"""
    act = active_skills()
    if not act:
        return ""
    parts = ["Skills activées par l'utilisateur — applique celles qui correspondent à sa demande, "
             "ignore les autres :"]
    total = 0
    for s in act:
        block = f"### {s['name']}\n{s['prompt'].strip()}"
        if total + len(block) > MAX_ACTIVE_CHARS:
            parts.append("(d'autres skills actives ont été omises : trop de skills pour ce modèle)")
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def active_summary() -> Tuple[int, int]:
    """(nombre de skills actives, nombre de caractères réellement envoyés)"""
    text = active_instructions()
    return len(active_skills()), len(text)


# ------------------------------------------------------------------ skills personnelles
def _save_user(items: List[Dict]) -> None:
    settings.set("skills_user", [{"id": s["id"], "name": s["name"], "desc": s["desc"],
                                  "prompt": s["prompt"]} for s in items])


def save_user_skill(name: str, desc: str, prompt: str, sid: str = "") -> Dict:
    name, desc, prompt = name.strip(), desc.strip(), prompt.strip()
    if not name:
        raise ValueError("Donnez un nom à la skill.")
    if not prompt:
        raise ValueError("La consigne de la skill est vide.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"Consigne trop longue ({len(prompt)} caractères, maximum {MAX_PROMPT_CHARS}).")
    items = user_skills()
    if sid and any(s["id"] == sid for s in items):
        for s in items:
            if s["id"] == sid:
                s.update(name=name, desc=desc, prompt=prompt)
    else:
        base = "user-" + slugify(name)
        sid, n = base, 2
        taken = {s["id"] for s in all_skills()}
        while sid in taken:
            sid, n = f"{base}-{n}", n + 1
        items.append({"id": sid, "name": name, "desc": desc, "prompt": prompt})
    _save_user(items)
    return next(s for s in user_skills() if s["id"] == sid)


def delete_user_skill(sid: str) -> bool:
    items = user_skills()
    keep = [s for s in items if s["id"] != sid]
    if len(keep) == len(items):
        return False
    _save_user(keep)
    set_enabled(sid, False)
    return True


# ------------------------------------------------------------------ import
def parse_skill_text(text: str, fallback_name: str = "") -> Dict:
    """Lit une skill au format SKILL.md (en-tête '---' avec name/description, puis la consigne)
    ou un simple texte."""
    name, desc, body = fallback_name, "", text.strip()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", body, re.S)
    if m:
        for line in m.group(1).splitlines():
            key, _, value = line.partition(":")
            value = value.strip().strip("'\"")
            if key.strip().lower() == "name" and value:
                name = value
            elif key.strip().lower() == "description" and value:
                desc = value
        body = m.group(2).strip()
    if not m:
        h = re.match(r"^#\s+(.+)\n", body)
        if h:
            name = h.group(1).strip()
    return {"name": name or "Skill importée", "desc": desc[:200], "prompt": body}


def import_files(paths: List[str]) -> Tuple[int, List[str]]:
    """Importe des .md / .txt / .zip (contenant des .md). Renvoie (nombre importé, erreurs)."""
    done, errors = 0, []

    def add(text: str, label: str):
        nonlocal done
        info = parse_skill_text(text, label)
        try:
            save_user_skill(info["name"], info["desc"], info["prompt"])
            done += 1
        except ValueError as e:
            errors.append(f"{label} : {e}")

    for path in paths:
        p = Path(path)
        try:
            if p.suffix.lower() == ".zip":
                with zipfile.ZipFile(p) as z:
                    names = [n for n in z.namelist() if n.lower().endswith((".md", ".txt"))
                             and not n.endswith("/")]
                    if not names:
                        errors.append(f"{p.name} : aucun fichier .md dans l'archive")
                    for n in names[:200]:
                        stem = Path(n).parent.name if Path(n).name.lower() == "skill.md" else Path(n).stem
                        add(z.read(n).decode("utf-8", errors="replace"), stem or p.stem)
            elif p.suffix.lower() in (".md", ".txt"):
                stem = p.parent.name if p.name.lower() == "skill.md" else p.stem
                add(p.read_text(encoding="utf-8", errors="replace"), stem)
            else:
                errors.append(f"{p.name} : format non pris en charge (.md, .txt ou .zip)")
        except (OSError, zipfile.BadZipFile) as e:
            errors.append(f"{p.name} : {e}")
    return done, errors


def export_skill_text(s: Dict) -> str:
    return f"---\nname: {s['name']}\ndescription: {s['desc']}\n---\n\n{s['prompt']}\n"
