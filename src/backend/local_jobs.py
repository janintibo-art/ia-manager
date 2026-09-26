"""File FIFO des générations locales pilotées par cette instance d'IA Manager."""
import threading
import uuid
from urllib.parse import urlparse
from src.backend import settings, providers

_condition = threading.Condition()
_waiting = []
_owner = None


def is_local(ref):
    pid, _ = providers.split_ref(ref)
    if pid == "ollama": return True
    p = providers.get_provider(pid) or {}
    return urlparse(p.get("base_url", "")).hostname in ("localhost", "127.0.0.1", "::1")


def acquire(label, stopped):
    global _owner
    token = uuid.uuid4().hex
    with _condition:
        _waiting.append((token, label))
        try:
            while True:
                if stopped(): return None
                if _owner is None and _waiting[0][0] == token:
                    _owner = (token, label)
                    return token
                _condition.wait(.05)
        finally:
            _waiting[:] = [item for item in _waiting if item[0] != token]


def reserve(label):
    global _owner
    with _condition:
        if _owner is not None or _waiting: return None
        _owner = (uuid.uuid4().hex, label)
        return _owner[0]


def release(token):
    global _owner
    with _condition:
        if _owner and _owner[0] == token:
            _owner = None
            _condition.notify_all()


def state():
    with _condition:
        return {"active": _owner[1] if _owner else "", "waiting": [name for _,name in _waiting]}


def enabled():
    return settings.get("serialize_local_jobs") is not False
