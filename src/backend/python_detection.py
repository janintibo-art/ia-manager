"""Discover real interpreters without executing shell commands."""
import json
import os
from pathlib import Path
import shutil
import sys

PROBE = ('import sys,json,venv; print(json.dumps({"executable":sys.executable,'
         '"version":list(sys.version_info[:3])}))')


def candidates(preferred=""):
    entries = []
    if preferred.strip():
        value = preferred.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        entries.append((value, []))
    if not getattr(sys, "frozen", False):
        entries.append((sys.executable, []))
    launcher = shutil.which("py")
    if launcher:
        entries.append((launcher, ["-3"]))
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path:
            entries.append((path, []))
    if os.name == "nt":
        for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(key)
            if base:
                for pattern in ("Programs/Python/Python*/python.exe", "Python*/python.exe"):
                    entries.extend((str(p), []) for p in sorted(Path(base).glob(pattern), reverse=True))
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Python\PythonCore", 0, winreg.KEY_READ | view) as root:
                        for i in range(winreg.QueryInfoKey(root)[0]):
                            version = winreg.EnumKey(root, i)
                            try:
                                with winreg.OpenKey(root, version + r"\InstallPath") as sub:
                                    try:
                                        path = winreg.QueryValueEx(sub, "ExecutablePath")[0]
                                    except OSError:
                                        path = str(Path(winreg.QueryValue(sub, "")) / "python.exe")
                                    entries.append((path, []))
                            except OSError:
                                pass
                except OSError:
                    pass
    seen = set()
    for path, args in entries:
        # The direct WindowsApps stub opens the Store instead of running Python.
        if Path(path).parent.name.lower() == "windowsapps" and Path(path).name.lower() in ("python.exe", "python3.exe"):
            continue
        if getattr(sys, "frozen", False) and os.path.normcase(os.path.abspath(path)) == os.path.normcase(sys.executable):
            continue
        key = (os.path.normcase(path), tuple(args))
        if key not in seen:
            seen.add(key)
            yield path, args


def parse_probe(output):
    data = json.loads(output.strip().splitlines()[-1])
    version = tuple(data["version"])
    path = data["executable"]
    if version < (3, 10) or not Path(path).is_file():
        raise ValueError("Python 3.10 minimum requis.")
    return path, ".".join(map(str, version))
