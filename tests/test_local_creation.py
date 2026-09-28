import unittest
from unittest.mock import Mock, patch
from src.backend.local_creation import validate_engine_url
from src.backend import image_studio


class LocalCreationTests(unittest.TestCase):
    def test_loopback_addresses(self):
        for value in ('http://127.0.0.1:8188', 'http://localhost:7860', 'http://[::1]:8188'):
            self.assertEqual(validate_engine_url(value), value)

    def test_remote_addresses_rejected(self):
        for value in ('https://example.com', 'http://192.168.1.2:8188', 'http://localhost.example.com', 'http://127.0.0.1@example.com', 'file:///tmp'):
            with self.assertRaises(ValueError): validate_engine_url(value)
        self.assertEqual(validate_engine_url('https://example.com', False), 'https://example.com')

    def test_invalid_port(self):
        with self.assertRaises(ValueError): validate_engine_url('http://localhost:abc')

    def test_remote_blocked_before_request(self):
        with patch.object(image_studio, '_request') as request:
            with self.assertRaises(ValueError): image_studio.checkpoints('https://example.com')
            with self.assertRaises(ValueError): image_studio.generate('https://example.com', {})
            request.assert_not_called()

    def test_proxy_and_redirect_disabled(self):
        session = Mock()
        session.request.return_value.status_code = 302
        with patch.object(image_studio.requests, 'Session') as factory:
            factory.return_value.__enter__.return_value = session
            with self.assertRaises(ValueError): image_studio._request('GET', 'http://localhost:8188', timeout=1)
        self.assertFalse(session.trust_env)
        self.assertFalse(session.request.call_args.kwargs['allow_redirects'])

    def test_local_checkpoints(self):
        response=Mock()
        response.json.return_value={'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [['sdxl.safetensors']]}}}}
        with patch.object(image_studio, '_request', return_value=response):
            self.assertEqual(image_studio.checkpoints('http://localhost:8188'), ['sdxl.safetensors'])
