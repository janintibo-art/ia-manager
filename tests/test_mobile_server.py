import json
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from src.backend.mobile_server import MobileServer, LocalEngine, validate_chat


class FakeEngine:
    def __init__(self):
        self.wait = False
        self.started = threading.Event()
        self.stopped = threading.Event()

    def models(self):
        return [{'id': 'ollama::test', 'label': 'Test', '_target': 'private-api-key'}], []

    def stream(self, target, messages, emit, stopped):
        self.started.set()
        emit('Bonjour é')
        if self.wait:
            deadline = time.monotonic()+3
            while not stopped() and time.monotonic()<deadline:
                time.sleep(.01)
            if stopped():
                self.stopped.set()
        else:
            emit('té')


class MobileServerTests(unittest.TestCase):
    def setUp(self):
        self.engine = FakeEngine()
        self.service = MobileServer(self.engine)
        self.port = self.service.start('127.0.0.1', 0)
        self.token = self.service.token
        self.settings_patch = patch('src.backend.local_jobs.enabled', return_value=False)
        self.settings_patch.start()

    def tearDown(self):
        self.service.stop()
        self.settings_patch.stop()

    def request(self, path, body=None, token=None, origin=None):
        headers = {'Authorization': 'Bearer '+(self.token if token is None else token)}
        if origin: headers['Origin'] = origin
        return urlopen(Request(f'http://127.0.0.1:{self.port}'+path,
                               json.dumps(body).encode() if body is not None else None,
                               headers), timeout=5)

    def chat(self):
        return {'model': 'ollama::test', 'request_id': 'request-123',
                'messages': [{'role': 'user', 'content': 'Salut'}]}

    def test_access_and_no_secrets(self):
        for kwargs in ({'token':'wrong'}, {'origin':'http://evil.example'}):
            with self.assertRaises(HTTPError) as err:
                self.request('/v1/models', **kwargs)
            self.assertEqual(err.exception.code,401)
        with self.request('/v1/models') as r:
            data=r.read().decode()
        self.assertNotIn('private-api-key',data)
        self.assertNotIn('_target',data)
        self.assertEqual(json.loads(data)['models'][0]['id'],'ollama::test')

    def test_stream(self):
        with self.request('/v1/chat', self.chat()) as r:
            events=[json.loads(line) for line in r]
        self.assertEqual(''.join(e.get('text','') for e in events),'Bonjour été')
        self.assertEqual(events[-1], {'type':'done','stopped':False})

    def test_remote_model_rejected(self):
        body=self.chat(); body['model']='chatgpt::remote'
        with self.assertRaises(HTTPError) as err:
            self.request('/v1/chat',body)
        self.assertEqual(err.exception.code,400)
        self.assertFalse(self.engine.started.is_set())

    def test_cancel_and_busy(self):
        self.engine.wait=True
        response=self.request('/v1/chat',self.chat())
        self.assertTrue(self.engine.started.wait(1))
        with self.assertRaises(HTTPError) as err:
            self.request('/v1/chat', self.chat())
        self.assertEqual(err.exception.code,409)
        with self.request('/v1/cancel',{'request_id':'request-123'}) as r:
            self.assertTrue(json.load(r)['cancelled'])
        events=[json.loads(line) for line in response]
        response.close()
        self.assertTrue(events[-1]['stopped'])
        self.assertTrue(self.engine.stopped.wait(1))

    def test_pc_busy(self):
        with patch('src.backend.local_jobs.enabled',return_value=True), patch('src.backend.local_jobs.reserve',return_value=None):
            with self.assertRaises(HTTPError) as err:
                self.request('/v1/chat',self.chat())
        self.assertEqual(err.exception.code,409)

    def test_invalid_requests(self):
        for body in ([],{}, {'model':'x','request_id':'request-123','messages':[{'role':'system','content':'execute'}]}):
            with self.assertRaises(HTTPError) as err:
                self.request('/v1/chat',body)
            self.assertEqual(err.exception.code,400)
        with self.assertRaises(HTTPError) as err:
            self.request('/v1/chat',{'x':'x'*300000})
        self.assertEqual(err.exception.code,400)

    def test_stop_cancels(self):
        self.engine.wait=True
        response=self.request('/v1/chat',self.chat())
        self.assertTrue(self.engine.started.wait(1))
        self.service.stop()
        self.assertTrue(self.engine.stopped.wait(1))
        response.close()

    def test_local_filter(self):
        class Response:
            def raise_for_status(self): pass
            def json(self): return {'models': [], 'data':[{'id':'local'}]}
        urls=[]
        def get(url, **kw): urls.append(url); return Response()
        sources=[{'id':'remote','kind':'openai_compat','base_url':'https://example.org/v1'},
                 {'id':'local','kind':'openai_compat','base_url':'http://127.0.0.1:1234/v1'}]
        with patch('src.backend.providers.get_providers',return_value=sources), patch('httpx.Client.get',side_effect=get):
            models,_=LocalEngine().models()
        self.assertEqual([m['id'] for m in models],['local::local'])
        self.assertFalse(any('example.org' in u for u in urls))

class LocalTransportTests(unittest.TestCase):
    def test_ollama_and_openai_streams(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if self.path == '/api/chat':
                    raw = b'{"message":{"content":"bonjour"}}\n{"done":true}\n'
                else:
                    raw = b'data: {"choices":[{"delta":{"content":"bonjour"}}]}\n\ndata: [DONE]\n\n'
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            for kind in ('ollama','openai'):
                parts=[]
                LocalEngine().stream((f'http://127.0.0.1:{server.server_port}',kind,{},'model'),
                                     [{'role':'user','content':'hi'}],parts.append,lambda:False)
                self.assertEqual(''.join(parts),'bonjour')
        finally:
            server.shutdown(); server.server_close(); thread.join()

if __name__=='__main__': unittest.main()
