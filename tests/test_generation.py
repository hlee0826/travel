import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from PIL import Image
from generation import OpenAIImages, settings, estimated_cost


class GenerationTests(unittest.TestCase):
    def test_all_seven_references_and_success_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            references = []
            for i in range(7):
                path = Path(folder) / f'{i}.png'
                Image.new('RGB', (100 + i, 150), (i * 40, 20, 10)).save(path)
                references.append(str(path))
            response = io.BytesIO(json.dumps({'data': [{'b64_json': base64.b64encode(b'generated PNG').decode()}], 'usage': {'total_tokens': 123}}).encode())
            response.headers = {'x-request-id': 'req_test'}
            with patch('generation.urllib.request.urlopen', return_value=response) as request:
                raw, metadata = OpenAIImages('fake-local-key').generate({'prompt': 'identity and style', 'referenced_image_paths': references}, 'anonymous-session')
            sent = request.call_args.args[0]
            payload = json.loads(sent.data)
            self.assertEqual(sent.full_url, 'https://api.openai.com/v1/images/edits')
            self.assertEqual(payload['n'], 1)
            self.assertEqual(payload['model'], 'gpt-image-2.6-sunburst')
            self.assertEqual(len(payload['images']), 7)
            for i, image in enumerate(payload['images']):
                with Image.open(io.BytesIO(base64.b64decode(image['image_url'].split(',', 1)[1]))) as decoded:
                    self.assertEqual(decoded.getpixel((0, 0)), (i * 40, 20, 10))
            self.assertEqual(raw, b'generated PNG')
            self.assertEqual(metadata['request_id'], 'req_test')
            self.assertEqual(metadata['usage'], {'total_tokens': 123})
            self.assertNotIn('fake-local-key', json.dumps(metadata))

    def test_changed_reference_blocks_request_and_cost_estimates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.png'
            Image.new('RGB', (800, 1000)).save(path)
            with patch('generation.request_json') as request:
                with self.assertRaisesRegex(ValueError, 'reference changed'):
                    OpenAIImages('fake').generate({'referenced_image_paths': [str(path)],
                        'reference_hashes': ['changed'], 'prompt': 'test'}, 'session')
                request.assert_not_called()
        self.assertEqual(estimated_cost('gpt-image-2.6-sunburst', {
            'input_tokens_details': {'image_tokens': 4313, 'text_tokens': 828}, 'output_tokens': 4284}), .167164)
        self.assertEqual(estimated_cost('gpt-5-mini', {'input_tokens': 1000,
            'input_tokens_details': {'cached_tokens': 200}, 'output_tokens': 100}), .000405)
        self.assertIsNone(estimated_cost('unknown-model', {'input_tokens': 1000}))
        self.assertIsNone(estimated_cost('gpt-image-2.6-sunburst', {'total_tokens': 10}))

    def test_quota_error_has_no_automatic_retry_or_provider_body(self):
        error = urllib.error.HTTPError('https://api.openai.com/v1/images/edits', 429, 'secret provider details', {}, io.BytesIO(b'private data'))
        with patch('generation.urllib.request.urlopen', side_effect=error) as request:
            with self.assertRaisesRegex(ValueError, 'credit or request limit'):
                OpenAIImages('fake-local-key').generate({'prompt': 'test', 'referenced_image_paths': []}, 'session')
            self.assertEqual(request.call_count, 1)

    def test_empty_response_fails_and_environment_overrides_file(self):
        response = io.BytesIO(b'{"data":[]}')
        response.headers = {}
        with patch('generation.urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'no readable artwork'):
                OpenAIImages('fake-local-key').generate({'prompt': 'test', 'referenced_image_paths': []}, 'session')
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / '.env.local').write_text('OPENAI_API_KEY=file-key\nMINHWA_IMAGE_PROVIDER=openai\n')
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'environment-key'}):
                self.assertEqual(settings(folder)['OPENAI_API_KEY'], 'environment-key')


if __name__ == '__main__':
    unittest.main()
