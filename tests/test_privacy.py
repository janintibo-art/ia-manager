import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.backend import settings, providers, web_tools, diagnostics

class PrivacyTests(unittest.TestCase):
    def test_offline_blocks_remote_and_web(self):
        settings.set('offline_mode', True)
        remote={'id':'x','name':'Remote','kind':'openai_compat','base_url':'https://example.invalid/v1','enabled':True,'models':[],'api_key':'x'}
        providers.save_provider(remote)
        with self.assertRaises(RuntimeError): providers.fetch_models(remote)
        self.assertEqual(web_tools.search('test'),([], 'Hors ligne'))
        with patch.object(providers.requests,'post') as post:
            text=providers.chat('x::m',[])
        self.assertIn('hors ligne',text)
        settings.set('offline_mode', False)

    def test_diagnostic_has_no_secrets(self):
        settings.set('offline_mode', False)
        settings.set('providers',[{'id':'secret','name':'Secret','kind':'openai_compat','base_url':'https://x','api_key':'SUPER_SECRET','models':['m'],'enabled':True}])
        with tempfile.TemporaryDirectory() as folder:
            path=diagnostics.export(folder)
            text=Path(path).read_text()
            self.assertNotIn('SUPER_SECRET',text)
            data=json.loads(text)
            provider=next(item for item in data['providers'] if item['id']=='secret')
            self.assertTrue(provider['configured'])
        settings.set('providers',[])

if __name__=='__main__': unittest.main()
