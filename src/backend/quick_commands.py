"""Commandes rapides du Chat : « /resume mon texte » devient une consigne complète.

{texte} dans le modèle est remplacé par ce qui suit la commande.
"""

import unicodedata
from typing import Dict, List, Optional, Tuple

from src.backend import settings

DEFAULT_COMMANDS: List[Dict] = [
    {"trigger": "/resume", "name": "Résumer",
     "template": "Résume le texte suivant en 5 lignes maximum, puis liste les points clés :\n\n{texte}"},
    {"trigger": "/traduis", "name": "Traduire",
     "template": "Traduis ce texte (en anglais s'il est en français, sinon en français). "
                 "Garde la mise en forme, sans commentaire :\n\n{texte}"},
    {"trigger": "/corrige", "name": "Corriger le français",
     "template": "Corrige l'orthographe, la grammaire et la ponctuation, sans changer le style. "
                 "Donne le texte corrigé puis la liste des corrections :\n\n{texte}"},
    {"trigger": "/explique", "name": "Expliquer simplement",
     "template": "Explique simplement, étape par étape, avec un exemple concret :\n\n{texte}"},
    {"trigger": "/code", "name": "Écrire du code",
     "template": "Écris le code complet pour : {texte}\n\nMets chaque fichier dans son propre bloc ``` "
                 "avec son chemin après le langage, puis explique brièvement comment l'utiliser."},
    {"trigger": "/debug", "name": "Trouver un bug",
     "template": "Trouve la cause de ce problème et donne le code corrigé complet :\n\n{texte}"},
    {"trigger": "/mail", "name": "Rédiger un e-mail",
     "template": "Rédige un e-mail clair et poli en français à partir de ces éléments. "
                 "Propose un objet :\n\n{texte}"},
    {"trigger": "/idees", "name": "Trouver des idées",
     "template": "Donne 10 idées originales et concrètes sur ce sujet, avec une phrase d'explication "
                 "pour chacune :\n\n{texte}"},
    {"trigger": "/simplifie", "name": "Simplifier un texte",
     "template": "Réécris ce texte pour qu'il soit compréhensible par tout le monde, avec des phrases "
                 "courtes :\n\n{texte}"},
]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower()


def load() -> List[Dict]:
    saved = settings.get("quick_commands")
    return [dict(c) for c in saved] if saved else [dict(c) for c in DEFAULT_COMMANDS]


def save(commands: List[Dict]) -> None:
    clean = []
    for c in commands:
        trig = "/" + _norm(c.get("trigger", "")).strip().lstrip("/").replace(" ", "")
        if trig != "/" and c.get("template", "").strip():
            clean.append({"trigger": trig, "name": c.get("name", "").strip() or trig,
                          "template": c["template"]})
    settings.set("quick_commands", clean)


def reset() -> None:
    settings.set("quick_commands", None)


def expand(text: str, commands: Optional[List[Dict]] = None) -> Tuple[str, Optional[Dict]]:
    """Si le message commence par une commande connue, renvoie (consigne complète, commande)"""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return text, None
    first, _, rest = stripped.partition(" ")
    if "\n" in first:
        first, _, more = first.partition("\n")
        rest = more + (" " + rest if rest else "")
    key = _norm(first)
    for c in commands or load():
        if _norm(c["trigger"]) == key:
            body = rest.strip()
            template = c["template"]
            if "{texte}" in template:
                return template.replace("{texte}", body), c
            return (template + ("\n\n" + body if body else "")), c
    return text, None
