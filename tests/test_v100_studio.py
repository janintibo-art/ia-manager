import unittest
from src.backend import studio_catalog as c


class V100StudioTests(unittest.TestCase):
    def test_catalog_size_and_domains(self):
        self.assertGreaterEqual(len(c.MODELS), 30)
        self.assertGreaterEqual(len(c.TOOLS), 20)
        self.assertGreaterEqual(len(c.PIPELINES), 10)
        categories = {m['category'] for m in c.MODELS}
        self.assertIn('Image', categories)
        self.assertIn('Audio & musique', categories)
        self.assertIn('Vidéo', categories)
        self.assertIn('3D', categories)
        self.assertIn('Texte & code', categories)
        self.assertIn('Documents & RAG', categories)

    def test_compatibility(self):
        heavy = next(m for m in c.MODELS if m['id'] == 'flux-dev')
        self.assertEqual(c.compatibility(heavy, 16, 32)[0], 'bon')
        self.assertIn(c.compatibility(heavy, 8, 32)[0], ('limite', 'difficile'))
        cpu = next(m for m in c.MODELS if m['id'] == 'bge-m3')
        self.assertEqual(c.compatibility(cpu, 0, 16)[0], 'bon')

    def test_filter(self):
        found = c.filter_models('music')
        self.assertTrue(any('MusicGen' in m['name'] for m in found))
        found = c.filter_models(category='3D')
        self.assertTrue(found and all(m['category'] == '3D' for m in found))

    def test_hardware_parser(self):
        cap = c.hardware_capacity({'gpu': {'vram': '12 GB'}, 'ram': '64 GB'})
        self.assertGreaterEqual(cap['vram'], 12)
        self.assertGreaterEqual(cap['ram'], 64)


if __name__ == '__main__':
    unittest.main()
