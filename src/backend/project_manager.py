"""Projets : consignes, sauvegardes de discussions, classement.

Chaque projet est un dossier lisible à la main :

    <Projets>/<nom_du_projet>/
        projet.json        nom, catégorie, étiquettes, favori, modèle, liens GitHub
        consignes.md       consignes données à l'IA pour ce projet
        sauvegardes/       une discussion = un fichier .json
        fichiers/          vos documents libres pour ce projet
"""

import json
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_CATEGORIES = ["Général", "Développement", "Écriture", "Recherche", "Études", "Personnel"]

INSTRUCTION_TEMPLATES: Dict[str, str] = {
    "Assistant développeur":
        "Tu es un développeur expérimenté. Réponds en français.\n"
        "- Donne du code complet et prêt à l'emploi.\n"
        "- Explique brièvement ce qui change et pourquoi.\n"
        "- Signale les risques et les cas limites.",
    "Correcteur de français":
        "Tu corriges l'orthographe, la grammaire et la ponctuation des textes que je t'envoie.\n"
        "- Renvoie d'abord le texte corrigé.\n"
        "- Puis liste les corrections importantes, une par ligne.\n"
        "- Ne change pas le style ni le sens.",
    "Traducteur":
        "Tu es traducteur professionnel. Traduis fidèlement le texte que je t'envoie.\n"
        "- Si le texte est en français, traduis-le en anglais ; sinon traduis-le en français.\n"
        "- Garde la mise en forme.\n"
        "- Ne rajoute aucun commentaire.",
    "Professeur patient":
        "Tu es un professeur patient et bienveillant. Explique simplement, étape par étape, "
        "avec des exemples concrets. Vérifie que j'ai compris en posant une question à la fin.",
    "Rédacteur":
        "Tu m'aides à rédiger des textes clairs et agréables à lire en français.\n"
        "- Phrases courtes, vocabulaire simple.\n"
        "- Propose un titre.\n"
        "- Adapte le ton à la cible que je t'indique.",
    "Résumé de documents":
        "Tu résumes les documents que je te donne.\n"
        "- Un résumé en 5 lignes maximum.\n"
        "- Puis les points clés sous forme de liste.\n"
        "- Puis les chiffres et dates importants.",
}

META_FILE = "projet.json"
INSTRUCTIONS_FILE = "consignes.md"
SAVES_DIR = "sauvegardes"
FILES_DIR = "fichiers"
TRASH_DIR = ".corbeille"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text or "projet"


class ProjectManager:
    """Lecture et écriture des projets sur le disque"""

    def __init__(self, root: str):
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------- projets
    def _dir(self, pid: str) -> Path:
        return self.root / pid

    def list_projects(self) -> List[Dict]:
        projects = []
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and (d / META_FILE).exists():
                meta = self.get(d.name)
                if meta:
                    projects.append(meta)
        return projects

    def get(self, pid: str) -> Optional[Dict]:
        try:
            meta = json.loads((self._dir(pid) / META_FILE).read_text(encoding="utf-8"))
        except Exception:
            return None
        meta["id"] = pid
        meta.setdefault("name", pid)
        meta.setdefault("category", "Général")
        meta.setdefault("tags", [])
        meta.setdefault("favorite", False)
        meta.setdefault("default_model", "")
        meta.setdefault("github_repo", "")
        meta.setdefault("local_name", "")
        meta.setdefault("pc_folder", "")
        meta.setdefault("created", "")
        meta.setdefault("updated", meta.get("created", ""))
        saves = self._dir(pid) / SAVES_DIR
        meta["conversation_count"] = len(list(saves.glob("*.json"))) if saves.exists() else 0
        return meta

    def create_project(self, name: str, category: str = "Général") -> str:
        name = name.strip() or "Nouveau projet"
        base = slugify(name)
        pid, n = base, 2
        while self._dir(pid).exists():
            pid = f"{base}_{n}"
            n += 1
        d = self._dir(pid)
        (d / SAVES_DIR).mkdir(parents=True)
        (d / FILES_DIR).mkdir()
        (d / INSTRUCTIONS_FILE).write_text("", encoding="utf-8")
        meta = {"name": name, "category": category, "tags": [], "favorite": False,
                "default_model": "", "github_repo": "", "local_name": "", "pc_folder": "",
                "created": now_iso(), "updated": now_iso()}
        (d / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return pid

    def save_meta(self, pid: str, changes: Dict) -> None:
        meta = self.get(pid)
        if meta is None:
            raise FileNotFoundError(pid)
        for key in ("id", "conversation_count"):
            meta.pop(key, None)
        for key in ("name", "category", "tags", "favorite", "default_model",
                    "github_repo", "local_name", "pc_folder"):
            if key in changes:
                meta[key] = changes[key]
        meta["updated"] = now_iso()
        (self._dir(pid) / META_FILE).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete_project(self, pid: str) -> Path:
        """Déplace le projet dans la corbeille (récupérable à la main)"""
        trash = self.root / TRASH_DIR
        trash.mkdir(exist_ok=True)
        dest = trash / f"{pid}_{datetime.now():%Y%m%d_%H%M%S}"
        shutil.move(str(self._dir(pid)), str(dest))
        return dest

    def export_project(self, pid: str, dest_folder: str) -> Path:
        """Sauvegarde complète du projet dans un fichier .zip"""
        dest = Path(dest_folder) / f"{pid}_sauvegarde_{datetime.now():%Y%m%d_%H%M}"
        archive = shutil.make_archive(str(dest), "zip", root_dir=str(self.root), base_dir=pid)
        return Path(archive)

    def project_folder(self, pid: str) -> Path:
        return self._dir(pid)

    def files_folder(self, pid: str) -> Path:
        d = self._dir(pid) / FILES_DIR
        d.mkdir(exist_ok=True)
        return d

    def categories(self) -> List[str]:
        cats = list(DEFAULT_CATEGORIES)
        for p in self.list_projects():
            if p["category"] and p["category"] not in cats:
                cats.append(p["category"])
        return cats

    def all_tags(self) -> List[str]:
        tags = set()
        for p in self.list_projects():
            tags.update(p["tags"])
        return sorted(tags, key=str.lower)

    # -------------------------------------------------------- consignes
    def get_instructions(self, pid: str) -> str:
        f = self._dir(pid) / INSTRUCTIONS_FILE
        return f.read_text(encoding="utf-8") if f.exists() else ""

    def set_instructions(self, pid: str, text: str) -> None:
        (self._dir(pid) / INSTRUCTIONS_FILE).write_text(text, encoding="utf-8")
        self.save_meta(pid, {})

    # ----------------------------------------------------- sauvegardes
    def _saves(self, pid: str) -> Path:
        d = self._dir(pid) / SAVES_DIR
        d.mkdir(exist_ok=True)
        return d

    def list_conversations(self, pid: str) -> List[Dict]:
        convs = []
        for f in self._saves(pid).glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            convs.append({
                "id": f.stem,
                "title": data.get("title", f.stem),
                "model": data.get("model", ""),
                "created": data.get("created", ""),
                "updated": data.get("updated", ""),
                "count": len(data.get("messages", [])),
            })
        convs.sort(key=lambda c: c["updated"], reverse=True)
        return convs

    def save_conversation(self, pid: str, conv: Dict) -> str:
        """Crée ou met à jour une discussion ; renvoie son identifiant"""
        cid = conv.get("id") or f"{datetime.now():%Y%m%d_%H%M%S}"
        data = {
            "title": conv.get("title") or "Discussion",
            "model": conv.get("model", ""),
            "created": conv.get("created") or now_iso(),
            "updated": now_iso(),
            "messages": conv.get("messages", []),
        }
        (self._saves(pid) / f"{cid}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.save_meta(pid, {})
        return cid

    def load_conversation(self, pid: str, cid: str) -> Dict:
        data = json.loads((self._saves(pid) / f"{cid}.json").read_text(encoding="utf-8"))
        data["id"] = cid
        return data

    def rename_conversation(self, pid: str, cid: str, title: str) -> None:
        data = self.load_conversation(pid, cid)
        data["title"] = title
        self.save_conversation(pid, data)

    def delete_conversation(self, pid: str, cid: str) -> None:
        f = self._saves(pid) / f"{cid}.json"
        if f.exists():
            f.unlink()

    def export_conversation_markdown(self, pid: str, cid: str) -> Path:
        """Exporte une discussion en texte lisible (.md) dans le dossier fichiers/"""
        data = self.load_conversation(pid, cid)
        lines = [f"# {data.get('title', 'Discussion')}", "",
                 f"Modèle : {data.get('model', '')} — {data.get('updated', '')}", ""]
        for m in data.get("messages", []):
            who = "Vous" if m.get("role") == "user" else "IA"
            lines += [f"## {who}", "", m.get("content", ""), ""]
        out = self.files_folder(pid) / f"{slugify(data.get('title', cid))}_{cid}.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        return out


def sort_projects(projects: List[Dict], mode: str) -> List[Dict]:
    """Classement : favoris d'abord, puis selon le mode choisi"""
    if mode == "Nom":
        key = lambda p: p["name"].lower()  # noqa: E731
        rev = False
    elif mode == "Catégorie":
        key = lambda p: (p["category"].lower(), p["name"].lower())  # noqa: E731
        rev = False
    elif mode == "Nombre de discussions":
        key = lambda p: p["conversation_count"]  # noqa: E731
        rev = True
    else:  # "Modifié récemment"
        key = lambda p: p["updated"]  # noqa: E731
        rev = True
    ordered = sorted(projects, key=key, reverse=rev)
    return [p for p in ordered if p["favorite"]] + [p for p in ordered if not p["favorite"]]


def filter_projects(projects: List[Dict], text: str = "", category: str = "", tag: str = "") -> List[Dict]:
    text = text.strip().lower()
    out = []
    for p in projects:
        if category and p["category"] != category:
            continue
        if tag and tag not in p["tags"]:
            continue
        if text and text not in (p["name"] + " " + " ".join(p["tags"]) + " " + p["category"]).lower():
            continue
        out.append(p)
    return out
