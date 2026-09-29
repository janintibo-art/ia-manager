"""Sous-processus longs avec annulation et arrêt de leurs enfants."""
from __future__ import annotations

import os
import subprocess
import time


def stop_tree(process: subprocess.Popen) -> None:
    try:
        import psutil
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except psutil.Error:
                pass
    except ImportError:
        pass
    except Exception:
        pass
    try:
        process.kill()
    except OSError:
        pass


def run(command, *, cwd=None, env=None, timeout=1800, should_stop=lambda: False):
    flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(value) for value in command], cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, creationflags=flags, encoding="utf-8", errors="replace",
    )
    deadline = time.monotonic() + timeout
    while True:
        if should_stop():
            stop_tree(process)
            process.communicate()
            raise InterruptedError("Création arrêtée.")
        if time.monotonic() >= deadline:
            stop_tree(process)
            process.communicate()
            raise TimeoutError("Le moteur a dépassé le délai autorisé.")
        try:
            stdout, stderr = process.communicate(timeout=0.2)
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            continue
