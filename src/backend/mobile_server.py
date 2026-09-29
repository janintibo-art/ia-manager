"""LAN companion API. Opt-in, session token, local inference only, no file/tool API."""
import asyncio
import hmac
import ipaddress
import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import httpx
import psutil

MAX_BODY = 256 * 1024
MAX_REPLY = 512 * 1024


def lan_addresses():
    addresses = []
    try:
        interfaces = psutil.net_if_addrs()
    except (OSError, PermissionError):
        return []
    for entries in interfaces.values():
        for entry in entries:
            if entry.family == socket.AF_INET:
                ip = ipaddress.ip_address(entry.address)
                if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                    addresses.append(str(ip))
    return sorted(set(addresses))


def validate_chat(data):
    if not isinstance(data, dict):
        raise ValueError("Objet JSON attendu.")
    ref, rid, messages = data.get("model"), data.get("request_id"), data.get("messages")
    if not isinstance(ref, str) or not 1 <= len(ref) <= 256:
        raise ValueError("Modèle invalide.")
    if not isinstance(rid, str) or not 8 <= len(rid) <= 80 or not all(c.isalnum() or c == '-' for c in rid):
        raise ValueError("Identifiant invalide.")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
        raise ValueError("Entre 1 et 64 messages attendus.")
    clean = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            raise ValueError("Rôle de message invalide.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > (16000 if message["role"] == "user" else 70000):
            raise ValueError("Message vide ou trop long (16 000 caractères maximum).")
        clean.append({"role": message["role"], "content": content})
    if clean[-1]["role"] != "user":
        raise ValueError("Le dernier message doit provenir de l’utilisateur.")
    if sum(len(m['content']) for m in clean) > 100000:
        raise ValueError("Discussion trop longue : commencez une nouvelle conversation.")
    return ref, rid, clean


class LocalEngine:
    """Snapshot local endpoints; never accept an upstream URL from the phone."""
    def models(self):
        from src.backend import providers
        result, warnings = [], []
        sources = [("ollama", "Ollama", "http://127.0.0.1:11434", "ollama", {})]
        for p in providers.get_providers():
            base = p.get('base_url', '').rstrip('/')
            parsed = urlparse(base)
            if (p.get('enabled', True) and p.get('kind') == 'openai_compat'
                    and parsed.scheme in ('http', 'https')
                    and parsed.hostname in ('localhost', '127.0.0.1', '::1')
                    and not parsed.username and not parsed.password):
                headers = {'Authorization': 'Bearer ' + p['api_key']} if p.get('api_key') else {}
                sources.append((p['id'], p.get('name', p['id']), base, 'openai', headers))
        with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
            for pid, name, base, kind, headers in sources[:12]:
                try:
                    r = client.get(base + ('/api/tags' if kind == 'ollama' else '/models'), headers=headers)
                    r.raise_for_status()
                    items = r.json().get('models' if kind == 'ollama' else 'data', [])
                    for item in items[:200]:
                        model = item.get('name' if kind == 'ollama' else 'id')
                        if isinstance(model, str) and model:
                            result.append({'id': pid + '::' + model, 'label': name + ' · ' + model,
                                           '_target': (base, kind, headers, model)})
                except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                    warnings.append(name + ' indisponible')
        return result, warnings

    def stream(self, target, messages, emit, stopped):
        base, kind, headers, model = target
        async def request():
            body = {'model': model, 'messages': messages, 'stream': True}
            endpoint = '/api/chat' if kind == 'ollama' else '/chat/completions'
            async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=5), trust_env=False, follow_redirects=False) as client:
                async with client.stream('POST', base + endpoint, headers=headers, json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if kind != 'ollama':
                            if not line.startswith('data:'):
                                continue
                            line = line[5:].strip()
                            if line == '[DONE]':
                                return
                        data = json.loads(line)
                        if data.get('error'):
                            raise RuntimeError('Le moteur local a signalé une erreur.')
                        if kind == 'ollama':
                            token = (data.get('message') or {}).get('content', '')
                            done = bool(data.get('done'))
                        else:
                            choices = data.get('choices') or []
                            token = (choices[0].get('delta') or {}).get('content', '') if choices else ''
                            done = bool(choices and choices[0].get('finish_reason'))
                        if token:
                            emit(token)
                        if done:
                            return
                    raise RuntimeError('Réponse interrompue avant sa fin.')
        async def supervise():
            if stopped():
                return
            task = asyncio.create_task(request())
            deadline = time.monotonic() + 600
            try:
                while not task.done():
                    await asyncio.wait({task}, timeout=.1)
                    if stopped():
                        task.cancel()
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError('Génération trop longue.')
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            finally:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        asyncio.run(supervise())


class LimitedServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.slots.acquire(False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class MobileServer:
    def __init__(self, engine=None):
        self.engine = engine or LocalEngine()
        self.server = None
        self.thread = None
        self.token = ''
        self.lock = threading.Lock()
        self.chat_lock = threading.Lock()
        self.active = None
        self.stopping = threading.Event()
        self.last_status = 'Arrêté'

    def start(self, host, port):
        if self.server:
            raise RuntimeError('Serveur déjà démarré.')
        if self.chat_lock.locked():
            raise RuntimeError('Arrêt de la génération en cours. Réessayez dans quelques secondes.')
        ip = ipaddress.ip_address(host)
        if ip.version != 4 or not ip.is_private or ip.is_unspecified or ip.is_multicast:
            raise ValueError('Choisissez une adresse IPv4 locale.')
        self.token = secrets.token_urlsafe(24)
        self.stopping.clear()
        service = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def log_message(self, *_):
                pass  # Do not log chat contents or the access token.

            def respond(self, code, data):
                raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(raw)

            def authorized(self):
                supplied = self.headers.get('Authorization', '')
                expected = 'Bearer ' + service.token
                if (service.stopping.is_set() or self.headers.get('Origin')
                        or not hmac.compare_digest(supplied.encode(), expected.encode())):
                    self.respond(401, {'error': 'Code d’accès incorrect ou serveur arrêté.'})
                    return False
                return True

            def body(self):
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Transfert non pris en charge.')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    raise ValueError('Requête vide ou trop volumineuse.')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('Requête incomplète.')
                return json.loads(raw)

            def do_GET(self):
                if not self.authorized():
                    return
                if self.path != '/v1/models':
                    self.respond(404, {'error': 'Adresse inconnue.'})
                    return
                try:
                    models, warnings = service.engine.models()
                    self.respond(200, {'models': [{k: m[k] for k in ('id', 'label')} for m in models], 'warnings': warnings})
                except Exception:
                    self.respond(502, {'error': 'Impossible de lire les modèles locaux.'})

            def do_POST(self):
                if not self.authorized():
                    return
                try:
                    data = self.body()
                    if self.path == '/v1/cancel':
                        rid = data.get('request_id') if isinstance(data, dict) else None
                        with service.lock:
                            found = bool(service.active and service.active[0] == rid)
                            if found:
                                service.active[1].set()
                        self.respond(200, {'cancelled': found})
                        return
                    if self.path != '/v1/chat':
                        self.respond(404, {'error': 'Adresse inconnue.'})
                        return
                    ref, rid, messages = validate_chat(data)
                except (ValueError, TypeError, UnicodeError):
                    self.respond(400, {'error': 'Requête invalide ou discussion trop longue. Démarrez un nouveau chat.'})
                    return
                if not service.chat_lock.acquire(False):
                    self.respond(409, {'error': 'Une génération mobile est déjà en cours.'})
                    return
                from src.backend import local_jobs
                reservation, streaming = None, False
                cancelled = threading.Event()
                with service.lock:
                    service.active = (rid, cancelled)
                try:
                    if local_jobs.enabled():
                        reservation = local_jobs.reserve('Téléphone Android')
                        if reservation is None:
                            self.respond(409, {'error': 'Le PC effectue déjà un travail local. Réessayez après sa fin.'})
                            return
                    models, _ = service.engine.models()
                    match = next((m for m in models if m['id'] == ref), None)
                    if not match:
                        self.respond(400, {'error': 'Modèle local indisponible. Actualisez la liste.'})
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    streaming = True
                    def event(data):
                        self.wfile.write((json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8'))
                        self.wfile.flush()
                    total = 0
                    def emit(token):
                        nonlocal total
                        total += len(token)
                        if total > MAX_REPLY:
                            raise ValueError('Réponse trop longue.')
                        event({'type': 'token', 'text': token})
                    service.last_status = 'Génération mobile en cours'
                    event({'type': 'start'})
                    service.engine.stream(match['_target'], messages, emit,
                                          lambda: cancelled.is_set() or service.stopping.is_set())
                    event({'type': 'done', 'stopped': cancelled.is_set() or service.stopping.is_set()})
                    service.last_status = 'Dernier échange terminé'
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    cancelled.set()
                    service.last_status = 'Téléphone déconnecté ou délai dépassé'
                except Exception:
                    service.last_status = 'Erreur du moteur local'
                    try:
                        if streaming:
                            event({'type': 'error', 'message': 'Le moteur local a interrompu la réponse. Vérifiez le modèle sur le PC.'})
                        else:
                            self.respond(502, {'error': 'Le moteur local ne répond pas.'})
                    except OSError:
                        pass
                finally:
                    local_jobs.release(reservation)
                    with service.lock:
                        service.active = None
                    service.chat_lock.release()
        server = LimitedServer((host, int(port)), Handler)
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
        self.thread.start()
        self.last_status = 'En attente du téléphone'
        return server.server_address[1]

    def stop(self):
        self.stopping.set()
        with self.lock:
            if self.active:
                self.active[1].set()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.token = ''
        self.last_status = 'Arrêté'
