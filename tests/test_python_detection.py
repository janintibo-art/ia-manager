import json
import sys
import unittest
from unittest.mock import patch
from src.backend import python_detection as pd

class DetectionTests(unittest.TestCase):
    def test_valid_interpreter(self):
        path, version = pd.parse_probe(json.dumps({'executable': sys.executable, 'version': [3, 11, 9]}))
        self.assertEqual(path, sys.executable)
        self.assertEqual(version, '3.11.9')

    def test_old_and_missing(self):
        for path, version in ((sys.executable, [3, 9, 1]), ('/missing/python', [3, 11, 1])):
            with self.assertRaises(ValueError):
                pd.parse_probe(json.dumps({'executable': path, 'version': version}))

    def test_store_stub_excluded(self):
        with patch.object(pd.shutil, 'which', return_value=None):
            paths = list(pd.candidates('/Users/Test/WindowsApps/python.exe'))
        self.assertNotIn('/Users/Test/WindowsApps/python.exe', [p for p, _ in paths])

    def test_no_shell_parsing(self):
        paths = list(pd.candidates('py -c "bad command"'))
        self.assertEqual(paths[0], ('py -c "bad command"', []))

if __name__ == '__main__':
    unittest.main()
