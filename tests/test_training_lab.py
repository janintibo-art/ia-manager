import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.backend import training_lab as lab


class TrainingLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def dataset(self):
        path = self.root/'data.jsonl'
        rows = [dict(instruction=f'Question {i}', output=f'Réponse {i}') for i in range(12)]
        path.write_text('\n'.join(json.dumps(r) for r in rows+[rows[0]]), encoding='utf-8')
        return path

    def test_duplicates_removed_and_job_snapshot(self):
        source = self.dataset()
        with patch.object(lab, 'lab_root', return_value=self.root/'jobs'):
            job = lab.create_job('train', 'Qwen/Qwen2.5-3B-Instruct', dataset=source)
        self.assertEqual(len((job/'dataset.jsonl').read_text().splitlines()), 12)
        compile((job/'runner.py').read_text(), 'runner.py', 'exec')
        source.unlink()
        self.assertTrue((job/'dataset.jsonl').is_file())

    def test_bad_examples_rejected(self):
        path = self.dataset()
        with path.open('a') as f: f.write('\n{"instruction": 3, "output": "a"}')
        with self.assertRaisesRegex(ValueError, 'Ligne 14'):
            lab.read_dataset(path)

    def test_minimum_unique_examples(self):
        path = self.root/'tiny.jsonl'
        path.write_text('\n'.join([json.dumps(dict(instruction='q', output='a'))]*20))
        with self.assertRaisesRegex(ValueError, 'distincts'): lab.read_dataset(path)

    def test_no_identical_merge_or_overwrite(self):
        with self.assertRaises(ValueError): lab.create_job('merge', 'a', 'a')
        with patch.object(lab, 'lab_root', return_value=self.root):
            a = lab.create_job('diagnostic')
            b = lab.create_job('diagnostic')
        self.assertNotEqual(a, b)

    def test_import_checks_and_path_quoting(self):
        folder = self.root/'model with spaces'
        folder.mkdir()
        (folder/'config.json').write_text('{}')
        (folder/'model.safetensors').touch()
        with patch.object(lab, 'lab_root', return_value=self.root):
            path = lab.import_modelfile(folder, 'my-model')
            self.assertIn(json.dumps(folder.as_posix()), path.read_text())
            with self.assertRaises(ValueError): lab.import_modelfile(folder, 'bad\nFROM x')
            with self.assertRaises(ValueError): lab.import_modelfile(self.root, 'valid')

if __name__ == '__main__': unittest.main()
