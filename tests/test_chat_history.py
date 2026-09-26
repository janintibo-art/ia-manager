import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.backend.chat_history import archive_and_compact, MEMORY_PREFIX


class ChatHistoryTests(unittest.TestCase):
    def messages(self):
        return [{'role': 'user' if i % 2 == 0 else 'assistant',
                 'content': f'Échange {i} ' + 'détail ' * 300,
                 'attachments': ['document.txt']} for i in range(12)]

    def test_lossless_archive_and_reduction(self):
        messages = self.messages()
        with TemporaryDirectory() as root:
            reduced, folder = archive_and_compact(messages, root, {'conversation_id': 'abc'})
            saved = json.loads((folder / 'historique.json').read_text())
            self.assertEqual(saved['messages'], messages)
            self.assertEqual(len(messages), 12)
            self.assertEqual(reduced[1:], messages[-6:])
            self.assertTrue(reduced[0]['content'].startswith(MEMORY_PREFIX))
            self.assertLess(sum(len(m['content']) for m in reduced), sum(len(m['content']) for m in messages))
            self.assertIn('Échange 0', (folder / 'historique.md').read_text())
            reduced.extend(self.messages()[:2])
            _, second = archive_and_compact(reduced, root)
            self.assertNotEqual(folder, second)
            self.assertTrue((folder / 'historique.json').exists())

    def test_disk_failure_preserves_input_and_leaves_no_partial_archive(self):
        messages = self.messages()
        original = json.dumps(messages)
        with TemporaryDirectory() as root:
            with patch('src.backend.chat_history.os.fsync', side_effect=OSError('disque plein')):
                with self.assertRaises(OSError):
                    archive_and_compact(messages, root)
            self.assertEqual(list(Path(root).iterdir()), [])
        self.assertEqual(json.dumps(messages), original)

    def test_keeps_user_response_pairs(self):
        messages = self.messages() + [{'role': 'user', 'content': 'en attente'}]
        with TemporaryDirectory() as root:
            reduced, _ = archive_and_compact(messages, root)
            self.assertEqual(reduced[1]['role'], 'user')
            self.assertEqual(reduced[-1], messages[-1])


if __name__ == '__main__':
    unittest.main()
