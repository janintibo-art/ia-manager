"""Outils GitHub : commandes Termux prêtes à copier et actions git/gh pour le PC.

Convention : dossier local avec tiret bas (mon_projet), dépôt GitHub avec tiret simple (mon-projet).
"""

import platform
import re
import shutil
from typing import Dict, List, Optional, Tuple


def repo_from_local(local_name: str) -> str:
    return local_name.strip().replace("_", "-")


def local_from_repo(repo: str) -> str:
    return repo.strip().split("/")[-1].replace("-", "_")


def full_repo(owner: str, repo: str) -> str:
    repo = repo.strip()
    if "/" in repo:
        return repo
    return f"{owner.strip()}/{repo}" if owner.strip() else repo


def quote(text: str) -> str:
    """Guillemets doubles pour bash, sans caractères qui cassent la commande"""
    text = text.replace("\\", "").replace('"', "'").replace("`", "'").replace("$", "")
    return f'"{text}"'


# ------------------------------------------------------------------ Termux
# Chaque action = liste de (explication, commande). UNE commande par bloc.
TERMUX_ACTIONS = [
    "Mettre à jour le projet (zip → commit → push)",
    "Suivre la compilation",
    "Voir l'erreur de compilation",
    "Créer le dépôt (première fois)",
    "Cloner un dépôt existant",
    "Récupérer les derniers changements",
    "État du dépôt",
    "Créer une version (tag)",
    "Télécharger la dernière Release",
    "Lister mes dépôts",
    "Se connecter à GitHub (une seule fois)",
]


def termux_commands(action: str, local: str, owner: str, message: str = "",
                    run_number: str = "", tag: str = "", script: str = "~/memo-depot/mise-a-jour.sh",
                    zip_version: str = "1") -> List[Tuple[str, str]]:
    local = local.strip() or "mon_projet"
    repo_name = repo_from_local(local)
    repo = full_repo(owner, repo_name)
    msg = quote(message.strip() or "Mise à jour")
    run = run_number.strip() or "NUMERO"
    tag = tag.strip() or "v1.0.0"

    if action == TERMUX_ACTIONS[0]:
        return [
            ("Décompresse la dernière archive, commite et pousse sur GitHub.",
             f"bash {script} {local} {msg}"),
            ("Suit la compilation en direct.",
             f"gh run watch -R {repo}"),
        ]
    if action == TERMUX_ACTIONS[1]:
        return [("Suit la compilation en direct.", f"gh run watch -R {repo}")]
    if action == TERMUX_ACTIONS[2]:
        return [
            ("Liste les dernières compilations pour trouver le NUMÉRO de celle en échec.",
             f"gh run list -R {repo} -L 5"),
            ("Affiche uniquement le journal de l'étape en erreur (remplacez NUMERO si besoin).",
             f"gh run view {run} -R {repo} --log-failed"),
        ]
    if action == TERMUX_ACTIONS[3]:
        return [
            ("Décompresse l'archive dans votre dossier personnel.",
             f"unzip -o ~/storage/downloads/{local}_v{zip_version}.zip -d ~/"),
            ("Initialise git dans le dossier du projet.", f"git -C ~/{local} init"),
            ("Ajoute tous les fichiers.", f"git -C ~/{local} add ."),
            ("Premier commit.", f"git -C ~/{local} commit -m {msg}"),
            ("Crée le dépôt public sur GitHub et envoie le code.",
             f"gh repo create {repo_name} --public --source=$HOME/{local} --remote=origin --push"),
        ]
    if action == TERMUX_ACTIONS[4]:
        return [("Copie le dépôt GitHub dans ~/" + local + ".", f"gh repo clone {repo} ~/{local}")]
    if action == TERMUX_ACTIONS[5]:
        return [("Récupère les changements faits ailleurs.", f"git -C ~/{local} pull")]
    if action == TERMUX_ACTIONS[6]:
        return [("Montre les fichiers modifiés et la branche.", f"git -C ~/{local} status -sb")]
    if action == TERMUX_ACTIONS[7]:
        return [
            ("Crée l'étiquette de version.", f"git -C ~/{local} tag {tag}"),
            ("Envoie l'étiquette sur GitHub.", f"git -C ~/{local} push origin {tag}"),
        ]
    if action == TERMUX_ACTIONS[8]:
        return [("Télécharge les fichiers de la dernière Release dans Téléchargements.",
                 f"gh release download -R {repo} -D ~/storage/downloads --clobber")]
    if action == TERMUX_ACTIONS[9]:
        target = owner.strip()
        return [("Liste vos dépôts GitHub.", f"gh repo list {target} -L 50".replace("  ", " "))]
    if action == TERMUX_ACTIONS[10]:
        return [("Connexion à GitHub (à faire une seule fois, suivez les instructions).",
                 "gh auth login")]
    return []


# ------------------------------------------------------------------ PC
def tool_status() -> Dict[str, Optional[str]]:
    """Chemin de git et gh s'ils sont installés"""
    return {"git": shutil.which("git"), "gh": shutil.which("gh")}


def is_windows() -> bool:
    return platform.system() == "Windows"


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\r")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def shell_command(command: str) -> Tuple[str, List[str]]:
    """Commande libre du terminal intégré"""
    if is_windows():
        return "cmd", ["/c", command]
    return "bash", ["-lc", command]


# Étapes d'une action PC : liste de dicts {program, args, capture?}
# « {capture} » dans args est remplacé par la sortie de l'étape précédente marquée capture=True.
def pc_steps(action: str, message: str = "", repo: str = "", dest: str = "") -> List[Dict]:
    if action == "status":
        return [{"program": "git", "args": ["status", "-sb"]}]
    if action == "pull":
        return [{"program": "git", "args": ["pull"]}]
    if action == "commit_push":
        msg = message.strip() or "Mise à jour"
        return [
            {"program": "git", "args": ["add", "-A"]},
            {"program": "git", "args": ["commit", "-m", msg]},
            {"program": "git", "args": ["push"]},
        ]
    if action == "runs":
        return [{"program": "gh", "args": ["run", "list", "-L", "8"]}]
    if action == "watch":
        return [
            {"program": "gh", "args": ["run", "list", "-L", "1", "--json", "databaseId",
                                       "-q", ".[0].databaseId"], "capture": True},
            {"program": "gh", "args": ["run", "watch", "{capture}", "--exit-status"]},
        ]
    if action == "failed_log":
        return [
            {"program": "gh", "args": ["run", "list", "--status", "failure", "-L", "1",
                                       "--json", "databaseId", "-q", ".[0].databaseId"], "capture": True},
            {"program": "gh", "args": ["run", "view", "{capture}", "--log-failed"]},
        ]
    if action == "release":
        return [{"program": "gh", "args": ["release", "download", "-D", dest or "releases", "--clobber"]}]
    if action == "browse":
        return [{"program": "gh", "args": ["browse"]}]
    if action == "clone":
        return [{"program": "gh", "args": ["repo", "clone", repo, dest]}]
    if action == "repos":
        return [{"program": "gh", "args": ["repo", "list", "-L", "50"]}]
    if action == "auth_status":
        return [{"program": "gh", "args": ["auth", "status"]}]
    return []
