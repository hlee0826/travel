import base64
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import server
from deploy.start import validate


class HostingConfigTests(unittest.TestCase):
    def test_hosting_requires_all_security_settings(self):
        config = {
            'MINHWA_PUBLIC_ORIGIN': 'https://minhwa.pinnedby.com',
            'MINHWA_PASSWORD_HASH': '$2a$14$' + 'a' * 53,
            'OPENAI_API_KEY': 'test-only-not-a-real-key',
            'MINHWA_IMAGE_PROVIDER': 'openai',
            'MINHWA_DATA_DIR': '/data/studio',
        }
        self.assertEqual(validate(config), 'minhwa.pinnedby.com')
        for key in config:
            with self.subTest(missing=key), self.assertRaises(ValueError):
                validate({k: v for k, v in config.items() if k != key})
        for key, value in (
            ('MINHWA_PUBLIC_ORIGIN', 'http://minhwa.pinnedby.com'),
            ('MINHWA_PUBLIC_ORIGIN', 'https://minhwa.pinnedby.com/path'),
            ('MINHWA_PUBLIC_ORIGIN', 'https://minhwa.pinnedby.com\nanything'),
            ('MINHWA_PASSWORD_HASH', 'plaintext-password'),
            ('MINHWA_PASSWORD_HASH', '$2a$04$' + 'a' * 53),
            ('MINHWA_DATA_DIR', 'relative-path'),
            ('PORT', '4187'), ('PORT', '0'), ('PORT', 'not-a-port'),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate(config | {key: value})


@unittest.skipUnless(os.environ.get('CADDY_BIN'), 'Set CADDY_BIN to run the real password proxy test')
class PasswordProxyTests(unittest.TestCase):
    def test_all_routes_are_gated_and_private_files_stay_private(self):
        caddy = os.environ['CADDY_BIN']
        password = secrets.token_urlsafe(32)
        hashed = subprocess.run([caddy, 'hash-password'], input=password, text=True, capture_output=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp, patch.object(server, 'DATA', Path(tmp) / 'data'), patch.object(server, 'PUBLIC_ORIGIN', 'https://minhwa.pinnedby.com'):
            backend = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            threading.Thread(target=backend.serve_forever, daemon=True).start()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            config = Path(tmp) / 'Caddyfile'
            config.write_text((server.ROOT / 'deploy/Caddyfile').read_text().replace('127.0.0.1:4187', f'127.0.0.1:{backend.server_port}'))
            env = {'PATH': os.environ['PATH'], 'HOME': tmp, 'PORT': str(port), 'MINHWA_PUBLIC_HOST': 'minhwa.pinnedby.com', 'MINHWA_PASSWORD_HASH': hashed}
            proxy = subprocess.Popen([caddy, 'run', '--config', str(config), '--adapter', 'caddyfile'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            auth = 'Basic ' + base64.b64encode(('studio:' + password).encode()).decode()

            def request(path, method='GET', authorization=None, **headers):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                h = {'Host': 'minhwa.pinnedby.com', **headers}
                if authorization:
                    h['Authorization'] = authorization
                connection.request(method, path, headers=h)
                response = connection.getresponse()
                body = response.read()
                result = response.status, dict(response.getheaders()), body
                connection.close()
                self.assertNotIn(password.encode(), body)
                self.assertNotIn(hashed.encode(), body)
                return result

            try:
                for _ in range(100):
                    try:
                        request('/')
                        break
                    except OSError:
                        if proxy.poll() is not None:
                            self.fail('Password proxy failed to start')
                        time.sleep(.05)
                for path in ('/', '/app.js', '/assets/peony-cat.png', '/api/session', '/api/jobs/' + 'a'*24, '/media/' + 'a'*24 + '/source.png', '/api/orders/' + 'a'*24 + '/download/png', '/.env.local'):
                    for method in ('GET', 'POST'):
                        with self.subTest(path=path, method=method):
                            status, headers, _ = request(path, method)
                            self.assertEqual(status, 401)
                            self.assertIn('www-authenticate', {k.lower(): v for k, v in headers.items()})
                            self.assertEqual(headers.get('Cache-Control'), 'no-store')
                self.assertEqual(request('/', authorization='Basic c3R1ZGlvOndyb25n')[0], 401)
                self.assertEqual(request('/', authorization=auth, Host='other.example')[0], 421)
                self.assertEqual(request('/', authorization=auth)[0], 200)
                status, headers, body = request('/api/session', authorization=auth, Origin='https://minhwa.pinnedby.com')
                self.assertEqual(status, 200)
                self.assertIn('; Secure', headers['Set-Cookie'])
                self.assertEqual(json.loads(body)['jobs'], [])
                self.assertEqual(request('/api/session', authorization=auth, Origin='https://evil.example')[0], 403)
                for path in ('/.env.local', '/.studio/jobs', '/server.py', '/deploy/Caddyfile', '/fonts/NotoSerifKR.ttf', '/../server.py', '/%2e%2e/server.py'):
                    self.assertEqual(request(path, authorization=auth)[0], 404)
            finally:
                proxy.terminate()
                proxy.wait(timeout=10)
                backend.shutdown()
                backend.server_close()
