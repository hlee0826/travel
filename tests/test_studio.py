import base64
import http.client
import io
import json
from pathlib import Path
import secrets
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock
from PIL import Image
import server
import studio


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_data = server.DATA
        server.DATA = Path(cls.tmp.name)
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        output = io.BytesIO()
        Image.new('RGB', (800, 1000), 'white').save(output, 'PNG')
        cls.photo = output.getvalue()
        cls.image_path = Path(cls.tmp.name) / 'art.png'
        cls.image_path.write_bytes(cls.photo)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        server.DATA = cls.old_data
        cls.tmp.cleanup()

    def request(self, method, path, data=None, cookie=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=10)
        h = {'Content-Type': 'application/json'}
        if cookie:
            h['Cookie'] = cookie
        h.update(headers or {})
        connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=h)
        response = connection.getresponse()
        content = response.read()
        result = json.loads(content) if 'application/json' in response.getheader('Content-Type', '') else content
        result_headers = dict(response.getheaders())
        connection.close()
        return response.status, result, result_headers

    def session(self):
        status, _, headers = self.request('GET', '/api/session')
        self.assertEqual(status, 200)
        return headers['Set-Cookie'].split(';')[0]

    def create_job(self, cookie):
        encoded = base64.b64encode(self.photo).decode()
        status, job, _ = self.request('POST', '/api/jobs', {'face_image': encoded, 'body_image': encoded, 'name': '보리 <test>', 'style': 'peony', 'rights': True, 'generation_consent': True}, cookie)
        self.assertEqual(status, 201)
        return job

    def test_real_photo_lifecycle_and_order_idempotency(self):
        cookie = self.session()
        job = self.create_job(cookie)
        self.assertEqual(job['status'], 'awaiting_artwork')
        self.assertNotIn('session', job)
        inputs = server.read_json(server.job_path(job['id']) / 'generation-inputs.json')
        self.assertEqual(inputs['referenced_image_paths'], [str((server.job_path(job['id']) / 'face.png').resolve()), str((server.job_path(job['id']) / 'body.png').resolve()), *map(str, server.workflow.STYLE_ANCHORS)])
        self.assertEqual(len(inputs['referenced_image_paths']), 6)
        for path in inputs['referenced_image_paths']:
            with Image.open(path) as image:
                image.verify()
        self.assertIn('FACE IDENTITY', inputs['prompt'])
        self.assertIn('STYLE AND COMPOSITION ANCHORS', inputs['prompt'])
        self.assertIn('images 3 and 4 as the primary', inputs['prompt'])
        lotus = server.workflow.generation_inputs(server.job_path(job['id']) / 'face.png', 'lotus', body_source=server.job_path(job['id']) / 'body.png')
        self.assertIn('image 5 as the primary', lotus['prompt'])
        self.assertIn('generation-inputs.json', job['request'])
        complete = studio.complete(job['id'], [self.image_path])
        self.assertEqual(complete['completed_batches'], 1)
        self.assertEqual(complete['candidates'][0]['style_anchors'], [p.name for p in server.workflow.STYLE_ANCHORS])
        data = {'key': secrets.token_hex(12), 'job_id': job['id'], 'candidate_id': complete['candidates'][0]['id'], 'approved': True, 'product': 'framed', 'size': '5x7', 'total': 1}
        status, order, _ = self.request('POST', '/api/orders', data, cookie)
        self.assertEqual(status, 201)
        self.assertEqual(order['totals']['total'], 8500)
        status, duplicate, _ = self.request('POST', '/api/orders', data, cookie)
        self.assertEqual(status, 200)
        self.assertEqual(order, duplicate)
        self.assertEqual(len(list((server.DATA / 'orders').glob('*.json'))), 1)
        for expected in ['in_production', 'shipped', 'delivered', 'delivered']:
            status, advanced, _ = self.request('POST', f"/api/orders/{order['id']}/advance", {}, cookie)
            self.assertEqual(advanced['status'], expected)
        status, retry, _ = self.request('POST', f"/api/jobs/{job['id']}/retry", {}, cookie)
        self.assertEqual(status, 200)
        self.assertEqual(retry['workflow_version'], server.workflow.WORKFLOW_VERSION)
        self.assertEqual(server.read_json(server.job_path(job['id']) / 'generation-inputs.json'), inputs)
        studio.complete(job['id'], [self.image_path])
        status, _, _ = self.request('POST', f"/api/jobs/{job['id']}/retry", {}, cookie)
        self.assertEqual(status, 400)
        status, original, _ = self.request('POST', '/api/orders', data, cookie)
        self.assertEqual(original['candidate'], order['candidate'])

    def test_private_media_and_invalid_input(self):
        owner, stranger = self.session(), self.session()
        job = self.create_job(owner)
        status, _, _ = self.request('GET', job['source'], cookie=stranger)
        self.assertEqual(status, 404)
        status, _, _ = self.request('GET', job['source'], cookie=owner)
        self.assertEqual(status, 200)
        status, _, _ = self.request('GET', '/api/jobs/'+job['id'], cookie=stranger)
        self.assertEqual(status, 404)
        invalid = base64.b64encode(b'not a photo').decode()
        status, _, _ = self.request('POST', '/api/jobs', {'style':'peony','rights':True,'face_image':invalid,'body_image':invalid}, owner)
        self.assertEqual(status, 400)
        status, _, _ = self.request('POST', '/api/orders', {'job_id':job['id'],'approved':True,'candidate_id':'fake'}, owner)
        self.assertEqual(status, 400)
        status, _, _ = self.request('GET', '/api/session', headers={'Host':'evil.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/jobs', {}, owner, {'Origin':'https://evil.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('GET', '/../server.py')
        self.assertEqual(status, 404)
        for private_path in ('/.env.local', '/generation.py'):
            self.assertEqual(self.request('GET', private_path)[0], 404)

    def test_product_quotes(self):
        self.assertEqual(server.quote('digital','digital')['total'],1900)
        self.assertEqual(server.quote('print','5x7')['total'],4500)
        self.assertEqual(server.quote('framed','5x7')['total'],8500)
        self.assertEqual(server.quote('framed','12x16')['total'],11500)
        for size in ('8x10', '16x20', 'digital'):
            with self.assertRaises(ValueError):
                server.quote('print',size)

    def test_hosted_cookie_and_origin_boundary(self):
        with patch.object(server, 'PUBLIC_ORIGIN', 'https://minhwa.pinnedby.com'):
            status, _, headers = self.request('GET', '/api/session', headers={'Origin': 'https://minhwa.pinnedby.com'})
            self.assertEqual(status, 200)
            self.assertIn('; Secure', headers['Set-Cookie'])
            self.assertIn('HttpOnly', headers['Set-Cookie'])
            self.assertIn('SameSite=Strict', headers['Set-Cookie'])
            for origin in ('https://evil.example', 'https://pinnedby.com', 'null', f'http://localhost:{self.httpd.server_port}'):
                self.assertEqual(self.request('POST', '/api/jobs', {}, headers={'Origin': origin})[0], 403)
            # Forwarded headers cannot open a direct route around the loopback proxy.
            self.assertEqual(self.request('GET', '/api/session', headers={'Host': 'minhwa.pinnedby.com', 'X-Forwarded-Host': 'localhost'})[0], 403)

    def test_missing_anchor_blocks_generation_without_changing_existing_art(self):
        cookie = self.session()
        job = self.create_job(cookie)
        studio.complete(job['id'], [self.image_path])
        folder = server.job_path(job['id'])
        before = (folder / 'job.json').read_bytes()
        request_before = (folder / 'request.txt').read_bytes()
        with patch.object(server.workflow, 'STYLE_ANCHORS', (Path(self.tmp.name) / 'missing.png',)):
            status, error, _ = self.request('POST', f"/api/jobs/{job['id']}/retry", {}, cookie)
            self.assertEqual(status, 400)
            self.assertIn('reference is missing', error['error'])
            encoded = base64.b64encode(self.photo).decode()
            status, _, _ = self.request('POST', '/api/jobs', {'face_image': encoded, 'body_image': encoded, 'style': 'peony', 'rights': True}, cookie)
            self.assertEqual(status, 400)
            # Reading completed artwork never rebuilds a request with newer directions.
            self.assertEqual(self.request('GET', '/api/jobs/' + job['id'], cookie=cookie)[0], 200)
        self.assertEqual((folder / 'job.json').read_bytes(), before)
        self.assertEqual((folder / 'request.txt').read_bytes(), request_before)
        status, _, _ = self.request('GET', '/minhwa_workflow/style-anchors/peony-tuxedo-cat.png')
        self.assertEqual(status, 404)


if __name__ == '__main__':
    unittest.main()
