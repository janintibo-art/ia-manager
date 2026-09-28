"""Centre Termux v108 : générateur de commandes et SSH facultatif."""
from __future__ import annotations

import ipaddress
import re
import shutil
from typing import Dict, List, Tuple

from src.backend import github_tools


COMMON = (
    ("Préparer Termux", "pkg update && pkg install git gh openssh unzip"),
    ("Autoriser Téléchargements", "termux-setup-storage"),
    ("Démarrer SSH dans Termux", "sshd"),
    ("Voir mon utilisateur Termux", "whoami"),
    ("Voir l'adresse Wi-Fi", "ip addr show wlan0"),
    ("État GitHub CLI", "gh auth status"),
)


def validate_host(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError("Indiquez l'adresse du téléphone.")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        if re.fullmatch(r"[A-Za-z0-9.-]+", value):
            return value
    raise ValueError("Adresse du téléphone invalide.")


def validate_user(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("Utilisateur Termux invalide.")
    return value


def ssh_program() -> str:
    return shutil.which("ssh") or ""


def ssh_args(host: str, port: int, user: str, command: str, identity: str = "") -> List[str]:
    host = validate_host(host)
    user = validate_user(user)
    port = int(port)
    if not (1 <= port <= 65535):
        raise ValueError("Port SSH invalide.")
    args = [
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-p", str(port),
    ]
    identity = str(identity or "").strip()
    if identity:
        args += ["-i", identity]
    args += [f"{user}@{host}", str(command)]
    return args


def workflow_commands(local: str, owner: str, message: str, action: str = "update") -> List[Tuple[str, str]]:
    local = str(local or "").strip() or "ia_manager"
    owner = str(owner or "").strip()
    if action == "update":
        return github_tools.termux_commands(
            github_tools.TERMUX_ACTIONS[0], local, owner, message
        )
    if action == "watch":
        return github_tools.termux_commands(
            github_tools.TERMUX_ACTIONS[1], local, owner, message
        )
    if action == "status":
        return github_tools.termux_commands(
            github_tools.TERMUX_ACTIONS[6], local, owner, message
        )
    if action == "pull":
        return github_tools.termux_commands(
            github_tools.TERMUX_ACTIONS[5], local, owner, message
        )
    return []
