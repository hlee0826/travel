import base64
import hashlib
import http.client
import io
import json
from pathlib import Path
import secrets
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from PIL import Image
import server
from artifacts import artwork_files, matted_print
from generation import ART_FIELDS, OpenAIReview, PHOTO_FIELDS


def png(size, color):
    stream = io.BytesIO()
    Image.new('RGB', size, color).save(stream, 'PNG')
    return stream.getvalue()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(server, 'DATA', Path(self.temp.name)),
                        patch.object(server, 'GENERATOR', Mock()), patch.object(server, 'REVIEWER', Mock()),
                        patch.object(server, 'DAILY_BUDGET_CENTS', 1500)]
        for p in self.patches:
            p.start()
        self.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.photo = png((800, 1000), '#523315')
        self.art = png((2432, 3040), '#d6bba1')
        self.verdict = {'usable': True, 'pet_count': 1, 'species': 'dog', 'face_visible': True,
            'details_clear': True, 'identity': 'Upright ears; tan eyebrows; black coat.',
            'unseen_features': 'Tail hidden.', 'reason': 'Clear face.'}
        self.quality = {k: True for k in ART_FIELDS if k != 'reason'} | {'reason': 'All visible criteria match.'}
        server.REVIEWER.photo.return_value = (self.verdict, {'usage': {'input_tokens': 500}})
        server.REVIEWER.artwork.return_value = (self.quality, {'usage': {'input_tokens': 2000}})
        server.GENERATOR.generate.return_value = (self.art, {'provider': 'openai', 'model': 'test', 'request_id': 'test-image'})
        self.cookie = self.request('GET', '/api/session')[2]['Set-Cookie'].split(';')[0]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def request(self, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=10)
        conn.request(method, path, json.dumps(body) if body is not None else None,
            {'Content-Type': 'application/json', 'Cookie': cookie or getattr(self, 'cookie', '')})
        r = conn.getresponse(); raw = r.read(); headers = dict(r.getheaders())
        data = json.loads(raw) if 'application/json' in headers['Content-Type'] else raw
        conn.close()
        return r.status, data, headers

    def body(self):
        return {'key': secrets.token_hex(12), 'image': base64.b64encode(self.photo).decode(),
                'name': '보리', 'style': 'peony', 'rights': True, 'generation_consent': True}

    def create(self, body=None):
        status, job, _ = self.request('POST', '/api/jobs', body or self.body())
        self.assertEqual(status, 201, job)
        return job

    def stored(self, job):
        return server.read_json(server.job_path(job['id']) / 'job.json')

    def run_job(self, job):
        server.generate_artwork(job['id'], server.GENERATOR, server.REVIEWER)
        return self.stored(job)

    def test_product_preferences_survive_reload_and_invalid_sizes_fail(self):
        body = self.body() | {'product': 'framed', 'size': '12x16'}
        job = self.create(body)
        status, saved, _ = self.request('GET', f"/api/jobs/{job['id']}")
        self.assertEqual(status, 200)
        self.assertEqual((saved['product_preference'], saved['size_preference']), ('framed', '12x16'))
        self.assertEqual(self.request('POST', '/api/jobs', self.body() | {'product': 'framed', 'size': 'gigantic'})[0], 400)

    def test_consent_and_idempotency_survive_refresh(self):
        body = self.body(); body['generation_consent'] = False
        self.assertEqual(self.request('POST', '/api/jobs', body)[0], 400)
        body['generation_consent'] = True
        job = self.create(body)
        status, same, _ = self.request('POST', '/api/jobs', body)
        self.assertEqual(status, 200)
        self.assertEqual(same['id'], job['id'])
        self.assertEqual(len(self.stored(job)['attempts']), 1)
        body['style'] = 'lotus'
        self.assertEqual(self.request('POST', '/api/jobs', body)[0], 400)
        self.assertEqual(self.request('POST', f"/api/jobs/{job['id']}/retry", {})[1]['status'], 'queued')
        server.GENERATOR.generate.assert_not_called()

    def test_queue_serial_worker_and_recovery(self):
        first, second = self.create(), self.create()
        self.assertEqual(second['status'], 'queued')
        server.recover_jobs()
        self.assertEqual(self.stored(first)['status'], 'queued')
        server.STOP.clear()
        worker = threading.Thread(target=server.worker_loop)
        worker.start()
        try:
            deadline = time.time() + 5
            while time.time() < deadline and self.stored(second)['status'] != 'ready':
                time.sleep(.02)
            self.assertEqual(self.stored(first)['status'], 'ready')
            self.assertEqual(self.stored(second)['status'], 'ready')
            calls = server.GENERATOR.generate.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertIn(first['id'], calls[0].args[0]['referenced_image_paths'][0])
            self.assertIn(second['id'], calls[1].args[0]['referenced_image_paths'][0])
        finally:
            server.STOP.set(); server.WAKE.set(); worker.join(5)
            self.assertFalse(worker.is_alive())

    def test_bad_photo_never_paints(self):
        self.verdict.update(usable=False, pet_count=2, reason='Choose a photo of one pet.')
        job = self.run_job(self.create())
        self.assertEqual(job['status'], 'needs_photo')
        self.assertEqual(job['completed_batches'], 0)
        server.GENERATOR.generate.assert_not_called()
        self.assertEqual(self.request('POST', f"/api/jobs/{job['id']}/retry", {})[0], 400)

    def test_pass_releases_art_but_requires_customer_approval_and_exact_download(self):
        job = self.run_job(self.create())
        c = job['candidates'][0]
        self.assertEqual(job['status'], 'ready')
        self.assertEqual(c['studio_review']['reviewer'], 'automated')
        self.assertEqual(len(server.public_job(job)['candidates']), 1)
        self.assertEqual(job['completed_batches'], 1)
        server.recover_jobs()
        self.assertEqual(self.stored(job)['completed_batches'], 1)
        order = {'key': secrets.token_hex(12), 'job_id': job['id'], 'candidate_id': c['id'], 'approved': True, 'product': 'framed', 'size': '12x16'}
        self.assertEqual(self.request('POST', '/api/orders', order | {'approved': False})[0], 400)
        preview = self.request('GET', c['url'])[1]
        with Image.open(io.BytesIO(preview)) as im:
            self.assertEqual(im.size, (800, 1000))
        status, saved, _ = self.request('POST', '/api/orders', order)
        self.assertEqual(status, 201)
        raw = self.request('GET', f"/api/orders/{saved['id']}/download/png")[1]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), saved['candidate']['master_sha256'])
        stranger = self.request('GET', '/api/session', cookie='invalid')[2]['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('GET', f"/api/orders/{saved['id']}/download/png", cookie=stranger)[0], 404)
        self.assertEqual(self.request('GET', '/.studio/jobs/' + job['id'] + '/artifacts/' + c['id'] + '/master.png')[0], 404)
        paper = self.request('GET', f"/api/orders/{saved['id']}/download/print")[1]
        with Image.open(io.BytesIO(paper)) as im, Image.open(io.BytesIO(raw)) as master:
            self.assertEqual(im.size, (2432, 3243))
            self.assertEqual(im.crop((0, 101, 2432, 3141)).tobytes(), master.tobytes())
        self.assertEqual(self.request('POST', '/api/orders', order)[1], saved)

    def test_failed_checks_need_explicit_human_override(self):
        self.quality['likeness'] = False
        job = self.run_job(self.create()); c = job['candidates'][0]
        self.assertEqual(job['status'], 'awaiting_review')
        self.assertEqual(server.public_job(job)['candidates'], [])
        self.assertEqual(self.request('GET', c['url'])[0], 404)
        order = {'key': secrets.token_hex(12), 'job_id': job['id'], 'candidate_id': c['id'],
                 'approved': True, 'product': 'digital', 'size': 'digital'}
        self.assertEqual(self.request('POST', '/api/orders', order)[0], 400)
        with self.assertRaisesRegex(ValueError, 'flagged'):
            server.review_candidate(job['id'], c['id'], True, 'Looks okay')
        rejected = server.review_candidate(job['id'], c['id'], False, 'Ears differ from the source.')
        self.assertEqual(rejected['completed_batches'], 0)
        self.assertTrue(server.public_job(rejected)['can_retry'])
        self.assertEqual(server.public_job(rejected)['candidates'], [])

    def test_uncertain_call_never_retries_until_reconciled(self):
        server.GENERATOR.generate.side_effect = TimeoutError('timeout')
        job = self.run_job(self.create())
        self.assertEqual(job['status'], 'uncertain')
        self.assertEqual(job['completed_batches'], 0)
        self.assertEqual(self.request('POST', f"/api/jobs/{job['id']}/retry", {})[0], 400)
        server.recover_jobs()
        self.assertEqual(server.GENERATOR.generate.call_count, 1)
        server.reconcile_attempt(job['id'], 'Checked provider usage; request did not yield a retrievable output.')
        self.assertEqual(self.request('POST', f"/api/jobs/{job['id']}/retry", {})[1]['status'], 'queued')
        self.assertEqual(len(self.stored(job)['attempts']), 2)

    def test_spending_cap_includes_failed_and_pending_reservations(self):
        server.DAILY_BUDGET_CENTS = 600
        first, second = self.create(), self.create()
        self.assertEqual(self.request('POST', '/api/jobs', self.body())[0], 400)
        pending = self.stored(first);pending['status'] = 'painting';server.update_job(pending)
        server.recover_jobs()
        self.assertEqual(self.stored(first)['status'], 'uncertain')
        self.assertEqual(self.request('POST', '/api/jobs', self.body())[0], 400)
        self.assertEqual(self.stored(second)['status'], 'queued')

    def test_retry_uses_original_and_anchors_and_preserves_order(self):
        job = self.run_job(self.create()); c = job['candidates'][0]
        order = {'key': secrets.token_hex(12), 'job_id': job['id'], 'candidate_id': c['id'], 'approved': True, 'product': 'digital', 'size': 'digital'}
        saved = self.request('POST', '/api/orders', order)[1]
        status, _, _ = self.request('POST', f"/api/jobs/{job['id']}/retry", {'feedback': 'markings'})
        self.assertEqual(status, 200)
        next_job = self.run_job(job)
        request = server.GENERATOR.generate.call_args.args[0]
        self.assertEqual(len(request['referenced_image_paths']), 5)
        self.assertNotIn('art-', request['referenced_image_paths'][0])
        self.assertIn('patch locations', request['prompt'])
        self.assertIn('tan eyebrows', request['prompt'])
        self.assertEqual(self.request('POST', '/api/orders', order)[1], saved)
        self.assertEqual(next_job['status'], 'ready')
        self.assertEqual(next_job['completed_batches'], 2)
        self.assertEqual(self.request('POST', f"/api/jobs/{job['id']}/retry", {})[0], 400)

    def test_artifact_failure_cannot_release_an_unusable_master(self):
        with patch('server.artwork_files', side_effect=OSError('disk failure')):
            job = self.run_job(self.create())
        self.assertEqual(job['status'], 'uncertain')
        self.assertEqual(job['completed_batches'], 0)
        self.assertEqual(server.public_job(job)['candidates'], [])
        self.assertEqual(self.request('GET', job['candidates'][0]['url'])[0], 404)
        self.assertEqual(server.GENERATOR.generate.call_count, 1)

    def test_invalid_dimensions_or_source_copy_are_held(self):
        server.GENERATOR.generate.return_value = (self.photo, {})
        job = self.run_job(self.create())
        self.assertEqual(job['status'], 'uncertain')
        server.REVIEWER.artwork.assert_not_called()


class ReviewAndArtifactTests(unittest.TestCase):
    def test_review_schema_and_incomplete_response_fail_closed(self):
        response = io.BytesIO(b'{"status":"incomplete","output":[]}');response.headers = {}
        with patch('generation.urllib.request.urlopen', return_value=response) as request:
            with self.assertRaisesRegex(ValueError, 'complete assessment'):
                OpenAIReview('fake').analyze([], 'check', PHOTO_FIELDS, 'anonymous')
            body = json.loads(request.call_args.args[0].data)
            self.assertFalse(body['store'])
            self.assertTrue(body['text']['format']['strict'])
            self.assertEqual(body['max_output_tokens'], 3000)

    def test_name_rendering_is_repeatable_and_mat_never_crops(self):
        raw = png((800, 1000), '#a4b5c6')
        first = artwork_files(raw, '보리 Miso')
        self.assertEqual(first, artwork_files(raw, '보리 Miso'))
        self.assertNotEqual(first['master.png'], raw)
        with Image.open(io.BytesIO(first['master.png'])) as im:
            self.assertEqual(im.size, (800, 1000))
        with self.assertRaises(ValueError):
            matted_print(png((600, 600), 'white'))

if __name__ == '__main__':
    unittest.main()
