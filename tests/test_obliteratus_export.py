import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'src/backend/obliteratus_export.py'
spec = importlib.util.spec_from_file_location('obliteratus_export', SOURCE)
oe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oe)

class ExportTests(unittest.TestCase):
    def test_discovery_and_safe_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root / 'runs/run-one/checkpoint'
            checkpoint.mkdir(parents=True)
            for name in ('config.json', 'tokenizer_config.json', 'model.safetensors'):
                (checkpoint / name).write_text('{}')
            incomplete = root / 'runs/run-two/checkpoint'
            incomplete.mkdir(parents=True)
            self.assertEqual(oe.checkpoints(root / 'runs'), [checkpoint])
            python = root / 'python.exe'
            python.touch()
            steps = oe.make_steps(checkpoint, 'my-model', python, root / 'tools', 'ollama')
            self.assertEqual(steps[-1][1][:2], ['create', 'my-model'])
            # Windows peut rendre le même dossier sous son nom court RUNNER~1.
            self.assertTrue(Path(steps[-2][1][2]).samefile(checkpoint))
            self.assertIn('--outtype', steps[-2][1])
            self.assertEqual(steps[-2][1][-1], 'f16')
            self.assertNotEqual(steps[2][0], str(python))
            modelfile = Path(steps[-1][1][-1])
            self.assertEqual(modelfile.read_text(), 'FROM ./model.gguf\n')
            self.assertTrue((checkpoint / 'model.safetensors').exists())
            again = oe.make_steps(checkpoint, 'my-model', python, root / 'tools', 'ollama')
            self.assertNotEqual(again[-1][1][-1], str(modelfile))
            for name in ('../oops', 'a b', '-x', '', 'a\nFROM x'):
                with self.assertRaises(ValueError):
                    oe.make_steps(checkpoint, name, python, root / 'tools', 'ollama')
            with self.assertRaises(ValueError):
                oe.make_steps(incomplete, 'test', python, root / 'tools', 'ollama')

if __name__ == '__main__':
    unittest.main()
