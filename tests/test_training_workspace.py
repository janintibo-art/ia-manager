import io
import json
import runpy
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.backend import training_lab as lab, training_workspace as ws


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.mock=patch.object(lab,'lab_root',return_value=self.root)
        self.mock.start();self.addCleanup(self.mock.stop)

    def test_drafts_deduplicate_and_do_not_overwrite(self):
        row=dict(instruction=' question ',input='',output=' réponse ')
        a,count=ws.save_examples([row,row]);b,_=ws.save_examples([row])
        self.assertEqual(count,1);self.assertNotEqual(a,b)
        self.assertEqual(lab.read_dataset(a,minimum=1)[0]['instruction'],'question')
        with self.assertRaises(ValueError):lab.read_dataset(a)

    def test_invalid_draft_rejected(self):
        for rows in ([],[{}],[{'instruction':'q','output':3}]):
            with self.assertRaises(ValueError):ws.save_examples(rows)

    def test_history_state_and_partial_results(self):
        job=lab.create_job('merge','source-a','source-b')
        ws.record_state(job,'running')
        self.assertEqual(ws.history()[0]['status'],'incomplete')
        self.assertEqual(ws.history(active=job)[0]['status'],'running')
        (job/'model').mkdir();(job/'model'/'config.json').write_text('{}');(job/'model'/'weights.safetensors').touch()
        ws.record_state(job,'failed',1)
        self.assertFalse(ws.history()[0]['model_ready'])
        ws.record_state(job,'success',0)
        self.assertTrue(ws.history()[0]['model_ready'])

    def test_corrupt_history_record_ignored(self):
        path=self.root/'broken';path.mkdir();(path/'job.json').write_text('{')
        self.assertEqual(ws.history(),[])
        self.assertEqual(ws.metric(float('nan')),'—')

    def test_slerp_recipe_reaches_runner(self):
        job=lab.create_job('merge','base-a','variant-b',weight=.25,merge_method='slerp')
        auto=MagicMock();auto.from_pretrained.return_value.to_dict.return_value={'model_type':'qwen2'}
        token=MagicMock();token.from_pretrained.return_value.get_vocab.return_value={'test':0}
        token.from_pretrained.return_value.special_tokens_map={}
        original=Path.is_file
        def is_file(p):return p.name in ('mergekit-yaml','mergekit-yaml.exe') or original(p)
        with patch.dict(sys.modules,{'transformers':types.SimpleNamespace(AutoConfig=auto,AutoTokenizer=token)}), \
             patch.object(sys,'argv',['runner',str(job)]), patch.object(Path,'is_file',is_file), \
             patch('subprocess.run') as run, redirect_stdout(io.StringIO()):
            runpy.run_path(str(job/'runner.py'),run_name='__main__')
        recipe=json.loads((job/'merge.json').read_text())
        self.assertEqual(recipe['merge_method'],'slerp')
        self.assertEqual(recipe['base_model'],'base-a')
        self.assertEqual(recipe['models'],[{'model':'variant-b'}])
        self.assertEqual(recipe['parameters'],{'t':.25})
        run.assert_called_once()

    def test_unknown_merge_method_rejected(self):
        with self.assertRaises(ValueError):lab.create_job('merge','a','b',merge_method='unknown')
