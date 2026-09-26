"""Aperçu, sauvegarde et restauration des fichiers proposés par le chat."""
import difflib
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path

from src.backend.code_tools import assign_filenames

MAX_FILE = 2 * 1024 * 1024
MAX_BATCH = 10 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def destination(root, name):
    name = name.replace("\\", "/")
    parts = name.split("/")
    if (not name or name.startswith("/") or ":" in name
            or any(p in ("", ".", "..") or p.lower() == ".git" for p in parts)):
        raise ValueError(f"Chemin interdit : {name}")
    target = root
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"Lien symbolique non accepté : {name}")
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Chemin extérieur au projet : {name}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Ce chemin n'est pas un fichier : {name}")
    return target


def read_file(path):
    if not path.exists():
        return None
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise ValueError(f"Fichier trop volumineux pour l'aperçu (2 Mio maximum) : {path.name}")
    return data


def prepare(blocks, folder):
    root = Path(folder).resolve()
    if not root.is_dir():
        raise ValueError("Le dossier du projet n'existe pas.")
    entries, total, seen = [], 0, set()
    for block in assign_filenames(blocks):
        name = block["filename"].replace("\\", "/")
        target = destination(root, name)
        key = os.path.normcase(str(target))
        if key in seen:
            raise ValueError(f"Destination en double : {name}")
        seen.add(key)
        before = read_file(target)
        after = (block["code"] + "\n").encode("utf-8")
        if len(after) > MAX_FILE:
            raise ValueError(f"Fichier généré trop volumineux : {name}")
        total += len(before or b"") + len(after)
        if total > MAX_BATCH:
            raise ValueError("Lot trop volumineux pour l'aperçu (10 Mio maximum).")
        if before == after:
            continue
        try:
            old = (before or b"").decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Le fichier existant n'est pas du texte UTF-8 : {name}") from None
        if "\x00" in old:
            raise ValueError(f"Le fichier existant est binaire : {name}")
        diff_lines = difflib.unified_diff(old.splitlines(keepends=True),
                                           after.decode("utf-8").splitlines(keepends=True),
                                           fromfile=name if before is not None else "/dev/null",
                                           tofile=name)
        delta = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                        for line in diff_lines)
        entries.append({"name": name, "before": before, "after": after, "diff": delta,
                        "mode": target.stat().st_mode & 0o777 if before is not None else 0o644})
    return {"root": str(root), "entries": entries}


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".ia_manager_", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(review):
    root = Path(review["root"]).resolve()
    entries = review["entries"]
    if not entries:
        raise ValueError("Aucun changement à appliquer.")
    for entry in entries:
        if read_file(destination(root, entry["name"])) != entry["before"]:
            raise ValueError(f"Fichier modifié depuis l'aperçu : {entry['name']}. Rouvrez l'aperçu.")
    backup = Path.home() / ".ia_manager" / "code_backups" / uuid.uuid4().hex
    backup.mkdir(parents=True)
    manifest = {"root": str(root), "restored": False, "files": []}
    for index, entry in enumerate(entries):
        if entry["before"] is not None:
            (backup / str(index)).write_bytes(entry["before"])
        manifest["files"].append({"name": entry["name"], "backup": str(index),
                                  "existed": entry["before"] is not None,
                                  "before_hash": digest(entry["before"]),
                                  "after_hash": digest(entry["after"]), "mode": entry["mode"]})
    (backup / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    written = []
    try:
        for entry in entries:
            target = destination(root, entry["name"])
            if read_file(target) != entry["before"]:
                raise ValueError(f"Fichier modifié pendant l'application : {entry['name']}")
            atomic_write(target, entry["after"], entry["mode"])
            written.append(entry)
    except Exception as error:
        failures = []
        for entry in reversed(written):
            try:
                target = destination(root, entry["name"])
                if read_file(target) != entry["after"]:
                    raise ValueError("modifié par une autre application")
                if entry["before"] is None:
                    target.unlink()
                else:
                    atomic_write(target, entry["before"], entry["mode"])
            except Exception as rollback_error:
                failures.append(f"{entry['name']} : {rollback_error}")
        suffix = " ; restauration incomplète : " + "; ".join(failures) if failures else " ; fichiers précédents rétablis"
        raise OSError(f"Application interrompue : {error}{suffix}. Sauvegarde : {backup}") from error
    return str(backup)


def restore(backup_path):
    backup = Path(backup_path).resolve()
    allowed = (Path.home() / ".ia_manager" / "code_backups").resolve()
    if not backup.is_relative_to(allowed) or backup == allowed:
        raise ValueError("Emplacement de sauvegarde invalide.")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("restored"):
        raise ValueError("Cette sauvegarde a déjà été restaurée.")
    root = Path(manifest["root"]).resolve()
    pending = []
    for entry in manifest["files"]:
        target = destination(root, entry["name"])
        current = read_file(target)
        if digest(current) != entry["after_hash"]:
            raise ValueError(f"Restauration refusée : {entry['name']} a été modifié depuis l'application.")
        source = backup / str(entry["backup"])
        if not source.resolve().is_relative_to(backup):
            raise ValueError("Sauvegarde invalide.")
        before = source.read_bytes() if entry["existed"] else None
        if digest(before) != entry["before_hash"]:
            raise ValueError(f"Sauvegarde endommagée : {entry['name']}")
        pending.append((target, before, current, entry["mode"]))
    changed = []
    try:
        for target, before, current, mode in pending:
            if read_file(target) != current:
                raise ValueError(f"Fichier modifié pendant la restauration : {target.name}")
            if before is None:
                target.unlink()
            else:
                atomic_write(target, before, mode)
            changed.append((target, before, current, mode))
    except Exception as error:
        failures = []
        for target, before, current, mode in reversed(changed):
            try:
                if read_file(target) != before:
                    raise ValueError("fichier modifié après restauration")
                atomic_write(target, current, mode)
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        raise OSError(f"Restauration interrompue : {error}. Sauvegarde conservée : {backup}. "
                      + ("Retour incomplet : " + "; ".join(failures) if failures else "État appliqué rétabli.")) from error
    manifest["restored"] = True
    atomic_write(backup / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    return str(root)


def commit_steps(names, message):
    if not names:
        raise ValueError("Aucun fichier à envoyer.")
    return [{"program": "git", "args": ["--literal-pathspecs", "add", "--", *names]},
            {"program": "git", "args": ["--literal-pathspecs", "commit", "--only", "-m", message, "--", *names]},
            {"program": "git", "args": ["push"]}]
