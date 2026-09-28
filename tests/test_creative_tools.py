import ast
import tempfile
import unittest
from pathlib import Path
from src.backend import creative_tools as tools


class CreativeToolsTests(unittest.TestCase):
    def test_safe_argument_lists_and_separate_environments(self):
        with tempfile.TemporaryDirectory(prefix='tools with spaces ') as root:
            for key in tools.TOOLS:
                plan=tools.install_plan(root,key,'C:/Python/python.exe','C:/Git/git.exe','nvidia',windows=True)
                self.assertTrue(all(isinstance(s['args'],list) for s in plan))
                self.assertTrue(any(s['args'][:2]==['-m','venv'] for s in plan))
                p=tools.paths(root,key,True)
                self.assertEqual(p['python'].parts[-2:],('Scripts','python.exe'))
                self.assertTrue(any('https://download.pytorch.org/whl/'+('cu118' if key=='audiocraft' else 'cu128') in s['args'] for s in plan))
                for step in plan:
                    if '-c' in step['args']:ast.parse(step['args'][step['args'].index('-c')+1])

    def test_do_not_adopt_unmanaged_directory(self):
        with tempfile.TemporaryDirectory() as root:
            p=tools.paths(root,'comfyui')['base'];p.mkdir();(p/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):tools.prepare(root,'comfyui','cpu')
            self.assertEqual((p/'keep.txt').read_text(),'keep')

    def test_managed_resume_and_profile_guard(self):
        with tempfile.TemporaryDirectory() as root:
            tools.prepare(root,'audiocraft','cpu')
            tools.prepare(root,'audiocraft','cpu')
            self.assertEqual(tools.read_manifest(root,'audiocraft')['state'],'installation en cours')
            with self.assertRaises(ValueError):tools.prepare(root,'audiocraft','nvidia')
            ast.parse((tools.paths(root,'audiocraft')['base']/'audio_local.py').read_text())

    def test_offline_environment_and_launch(self):
        with tempfile.TemporaryDirectory() as root:
            for key in tools.TOOLS:
                env=tools.environment(root,key,True)
                self.assertEqual(env['HF_HUB_OFFLINE'],'1')
                self.assertEqual(env['GRADIO_SERVER_NAME'],'127.0.0.1')
                cmd=tools.launch_command(root,key,'cpu')
                self.assertNotIn('--share',cmd['args'])
                self.assertNotIn('0.0.0.0',cmd['args'])
            self.assertIn('--disable-api-nodes',tools.launch_command(root,'comfyui')['args'])
            self.assertIn('--cpu',tools.launch_command(root,'comfyui','cpu')['args'])
            self.assertIn('--disable_tex',tools.launch_command(root,'hunyuan3d','cpu')['args'])
            self.assertEqual(tools.environment(root,'comfyui',False)['HF_HUB_OFFLINE'],'0')

    def test_incomplete_clone_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            p=tools.prepare(root,'comfyui','cpu');p['source'].mkdir()
            with self.assertRaises(ValueError):tools.prepare(root,'comfyui','cpu')
            self.assertTrue(p['source'].is_dir())
