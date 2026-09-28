import unittest
from src.backend import pipeline_designer as p


class PipelineDesignerTests(unittest.TestCase):
    def test_builtin_library_unique(self):
        ids = [s['id'] for s in p.STEP_LIBRARY]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 20)

    def test_normalize_v100_pipeline_labels(self):
        steps = p.normalize_steps(('Prompt', 'FLUX/SDXL', 'rembg', 'Real-ESRGAN', 'PNG'))
        self.assertEqual(steps, ['prompt', 'flux_sdxl', 'rembg', 'upscale', 'export_png'])

    def test_saved_pipeline_validation_is_defensive(self):
        data = [
            {'name': 'Mon flux', 'steps': ['prompt', 'flux_sdxl', 'export_png']},
            {'name': 'mon flux', 'steps': ['prompt']},
            {'name': '', 'steps': ['prompt']},
            'bad',
        ]
        clean = p.validate_saved(data)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]['name'], 'Mon flux')

    def test_profiles_have_valid_pipeline_names(self):
        names = {x['name'] for x in __import__('src.backend.studio_catalog', fromlist=['PIPELINES']).PIPELINES}
        for profile in p.PROJECT_PROFILES:
            self.assertIn(profile['pipeline'], names)

    def test_guide_contains_human_names(self):
        guide = p.guide_for_steps(['prompt', 'musicgen', 'demucs', 'export_audio'])
        self.assertEqual(len(guide), 4)
        self.assertIn('MusicGen', guide[1])


if __name__ == '__main__':
    unittest.main()
