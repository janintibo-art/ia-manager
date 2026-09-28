import json
import io
import runpy
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.backend import training_resources as r, training_lab as lab
from src.backend.system_analyzer import SystemAnalyzer, detect_gpu


def hardware(vram=12, ram=32, vendor='NVIDIA', exact=True):
    return dict(gpu_vendor=vendor, gpu_type='test GPU', vram_gb=vram, ram_gb=ram,
                ram_available_gb=ram-5, vram_exact=exact, cpu='CPU', cpu_count=16)


class ResourceTests(unittest.TestCase):
    def test_recommendations_evolve_with_ram_and_vram(self):
        self.assertEqual(r.recommend(hardware())['size'], 3)
        self.assertEqual(r.recommend(hardware(24))['size'], 7)
        self.assertEqual(r.recommend(hardware(48,64))['size'], 14)
        self.assertEqual(r.recommend(hardware(48,16))['size'], 3)
        self.assertEqual(r.recommend(hardware(6,16))['size'], 1.5)

    def test_ram_does_not_replace_gpu(self):
        for info in (hardware(0,128), hardware(24,64,'AMD'), hardware(exact=False), {}, hardware(float('nan'))):
            self.assertIsNone(r.recommend(info))

    def test_custom_models_not_guessed(self):
        self.assertIsNone(r.requirements('some/unknown-7B'))
        self.assertIn('inconnu', r.advisory({}, 'some/unknown-7B'))

    def test_more_context_increases_estimate_and_merge_is_cpu(self):
        model=r.PROFILES[1]['model']
        self.assertGreater(r.requirements(model,4096,16,2)['vram_gb'], r.requirements(model)['vram_gb'])
        self.assertEqual(r.requirements(model,action='merge')['vram_gb'], 0)

    def test_refresh_really_invalidates_gpu_cache(self):
        detect_gpu.cache_clear()
        self.addCleanup(detect_gpu.cache_clear)
        with patch('src.backend.system_analyzer._run', side_effect=['Old GPU, 8192','New GPU, 24576']):
            old=SystemAnalyzer.get_system_info()
            cached=SystemAnalyzer.get_system_info()
            new=SystemAnalyzer.get_system_info(refresh=True)
        self.assertEqual(old['gpu_type'], cached['gpu_type'])
        self.assertEqual(new['vram_gb'],24)

    def test_trial_receives_settings_and_never_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            data=root/'examples.jsonl'
            data.write_text('\n'.join(json.dumps(dict(instruction=f'Q{i}',output=f'A{i}')) for i in range(12)))
            with patch.object(lab,'lab_root',return_value=root):
                job=lab.create_job('trial',r.PROFILES[1]['model'],dataset=data,
                                   tuning=dict(context=2048,rank=16,batch=2), hardware=hardware())
            tokenizer=MagicMock()
            tokenizer.apply_chat_template.return_value='training text'
            tokenizer.return_value={'input_ids':[1,2,3]}
            model=MagicMock()
            loader=MagicMock()
            loader.from_pretrained.return_value=(model,tokenizer)
            loader.get_peft_model.return_value=model
            torch=types.ModuleType('torch')
            torch.cuda=MagicMock()
            torch.cuda.is_available.return_value=True
            torch.cuda.mem_get_info.return_value=(10*2**30,12*2**30)
            torch.cuda.get_device_name.return_value='Test RTX'
            torch.cuda.max_memory_allocated.return_value=4*2**30
            torch.cuda.max_memory_reserved.return_value=5*2**30
            ds=MagicMock()
            ds.from_list.return_value.train_test_split.return_value={'train':[], 'test':[]}
            trainer=MagicMock()
            config=MagicMock(side_effect=lambda **kw:kw)
            modules={'torch':torch,
                     'unsloth':types.SimpleNamespace(FastLanguageModel=loader,is_bfloat16_supported=lambda:True),
                     'datasets':types.SimpleNamespace(Dataset=ds),
                     'trl':types.SimpleNamespace(SFTTrainer=trainer,SFTConfig=config)}
            with patch.dict(sys.modules,modules), patch.object(sys,'argv',['runner',str(job)]), redirect_stdout(io.StringIO()):
                runpy.run_path(str(job/'runner.py'),run_name='__main__')
            self.assertEqual(config.call_args.kwargs['max_steps'],2)
            self.assertEqual(config.call_args.kwargs['max_length'],2048)
            self.assertEqual(config.call_args.kwargs['per_device_train_batch_size'],2)
            self.assertEqual(loader.get_peft_model.call_args.kwargs['r'],16)
            model.save_pretrained_merged.assert_not_called()
            result=json.loads((job/'trial.json').read_text())
            self.assertEqual(result['peak_allocated_gb'],4)
            self.assertTrue((job/'hardware.json').is_file())

    def test_invalid_tuning_rejected_before_creating_job(self):
        for tuning in (dict(context=999,rank=8,batch=1), dict(context=1024,rank=8,batch=True), {'context':1024}):
            with self.assertRaises(ValueError): lab.create_job('diagnostic',tuning=tuning)
