"""Réseau local silencieux, documents, workers et coordination locale."""
import os
import sys
import json
import threading
import tempfile
import time
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from src.backend import providers, settings, project_memory as memory, local_jobs
from src.ui.workers import AttachmentWorker
from PyQt6.QtWidgets import QApplication
from src.ui.tabs.workspace_tab import WorkspaceTab

APP=QApplication.instance() or QApplication([])


def spin(predicate, seconds=5):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        APP.processEvents()
        if predicate():return
        time.sleep(.01)
    raise AssertionError('Délai dépassé')


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length','0')))
        if self.server.mode=='before':
            self.server.started.set()
            self.server.release.wait(5)
        try:
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream')
            self.end_headers()
            if self.server.mode=='between':
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"debut"}}]}\n\n')
                self.wfile.flush()
                self.server.started.set()
                self.server.release.wait(5)
            elif self.server.mode=='anthropic':
                self.wfile.write(b'data: {"type":"content_block_delta","delta":{"text":"bonjour"}}\n\n')
                self.wfile.write(b'data: {"type":"message_delta","usage":{"output_tokens":4}}\n\n')
                self.wfile.write(b'data: {"type":"message_stop"}\n\n')
            else:
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"bonjour"}}]}\n\n')
                self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError,ConnectionResetError):pass


class V24Tests(unittest.TestCase):
    def serve(self,mode):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.mode=mode;server.started=threading.Event();server.release=threading.Event()
        threading.Thread(target=server.serve_forever,daemon=True).start()
        def cleanup():server.release.set();server.shutdown();server.server_close()
        self.addCleanup(cleanup)
        provider={'id':'v24','name':'Test','kind':'anthropic' if mode=='anthropic' else 'openai_compat',
                  'base_url':f'http://127.0.0.1:{server.server_port}/v1','api_key':'test','enabled':True,'models':['m']}
        return server,provider

    def check_cancel(self,mode):
        server,provider=self.serve(mode)
        stop=threading.Event(); result=[]
        with patch.object(providers,'get_provider',return_value=provider):
            worker=threading.Thread(target=lambda:result.append(providers.chat_stream('v24::m',[],should_stop=stop.is_set)))
            worker.start()
            self.assertTrue(server.started.wait(3))
            started=time.monotonic();stop.set();worker.join(2)
            self.assertFalse(worker.is_alive(),'annulation réseau trop lente')
            self.assertLess(time.monotonic()-started,2)
        self.assertTrue(result[0][1]['stopped'])
        if mode=='between':self.assertEqual(result[0][0],'debut')

    def test_stop_before_headers(self):self.check_cancel('before')
    def test_stop_between_tokens(self):self.check_cancel('between')

    def test_anthropic_stream(self):
        _,provider=self.serve('anthropic')
        with patch.object(providers,'get_provider',return_value=provider):
            text,stats=providers.chat_stream('v24::m',[])
        self.assertEqual(text,'bonjour');self.assertEqual(stats['tokens'],4)

    def test_memory_search_update_remove(self):
        with tempfile.TemporaryDirectory() as d:
            identity=memory.add(d,'atelier.txt','Le synthétiseur violet possède trois oscillateurs. '*50)
            memory.add(d,'jardin.txt','Les pommes mûrissent dans le jardin.')
            results=memory.search(d,'synthétiseur oscillateurs')
            self.assertTrue(results);self.assertEqual(results[0]['name'],'atelier.txt')
            self.assertIn('[D1]',memory.context(results))
            memory.add(d,'atelier.txt','Le document a changé.')
            self.assertEqual(memory.search(d,'oscillateurs'),[])
            memory.remove(d,identity)
            self.assertEqual(len(memory.documents(d)),1)

    def test_attachment_cancel_discards_late_result(self):
        entered=threading.Event();release=threading.Event();loaded=[]
        def loader(path):entered.set();release.wait(3);return path
        worker=AttachmentWorker(['one','two'],loader)
        worker.loaded.connect(lambda *args:loaded.append(args));worker.start()
        self.assertTrue(entered.wait(1));worker.stop();release.set()
        spin(lambda:not worker.isRunning())
        APP.processEvents();self.assertEqual(loaded,[])

    def test_local_queue_cancel_and_release(self):
        token=local_jobs.reserve('first');self.assertIsNotNone(token)
        stop=threading.Event();result=[]
        thread=threading.Thread(target=lambda:result.append(local_jobs.acquire('second',stop.is_set)))
        thread.start();spin(lambda:bool(local_jobs.state()['waiting']))
        stop.set();thread.join(1);self.assertEqual(result,[None])
        local_jobs.release(token);self.assertEqual(local_jobs.state()['active'],'')
        token2=local_jobs.acquire('third',lambda:False);self.assertIsNotNone(token2)
        local_jobs.release(token2)

    def test_profiles_and_trials_persist(self):
        tab=WorkspaceTab()
        tab.name.setText('Profil test v24');tab.model.setCurrentText('ollama::test')
        tab.instructions.setPlainText('Consigne test');tab.save_profile()
        received=[];tab.apply_profile.connect(received.append);tab.use_profile()
        self.assertEqual(received[0]['instructions'],'Consigne test')
        second=WorkspaceTab();self.assertGreaterEqual(second.profiles.findText('Profil test v24'),0)
        trials=tab.trials;trials.title.setText('Essai test');trials.source.setText('ollama::a');trials.result.setText('ollama::b')
        trials.before.setValue(10);trials.after.setValue(12);trials.save()
        self.assertIn('+20.0',trials.status.text())
        records=settings.get('obliteratus_trials');self.assertEqual(records[-1]['source'],'ollama::a')
        tab.resources.timer.stop();second.resources.timer.stop()


if __name__=='__main__':unittest.main()
