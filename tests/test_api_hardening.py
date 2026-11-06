"""Exercise access control and rolling quotas through real HTTP requests."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from shelfscale.api import RateLimiter, ShelfScaleServer, ROUTES
from shelfscale.lookup import DATA_RELEASE

KEY = 'local-test-token'


class TestStartup(unittest.TestCase):
    def test_missing_or_invalid_key_refuses_before_binding(self):
        for key in (None, '', '   ', 'leading space', 'trailing\n', '非ascii'):
            with self.subTest(key=key), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, 'SHELFSCALE_API_KEY'):
                    ShelfScaleServer(('127.0.0.1', 0), api_key=key)

    def test_command_exits_without_key_and_does_not_print_secrets(self):
        env = {**os.environ, 'PYTHONPATH': 'src'}
        env.pop('SHELFSCALE_API_KEY', None)
        result = subprocess.run([sys.executable, '-m', 'shelfscale.api', '--port', '0'],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('SHELFSCALE_API_KEY must be set', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(result.stdout, '')


class TestLimiter(unittest.TestCase):
    def test_atomic_quota_is_bounded_under_concurrency(self):
        limiter = RateLimiter(clock=lambda: 100.)
        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: limiter.admit(), range(200)))
        self.assertEqual(results.count(0), 60)
        self.assertEqual(results.count(60), 140)
        self.assertEqual(len(limiter.requests), 60)

    def test_window_is_rolling_with_fractional_retry(self):
        now = [100.25]
        limiter = RateLimiter(clock=lambda: now[0])
        self.assertEqual(limiter.admit(), 0)
        now[0] = 110.25
        for _ in range(59): self.assertEqual(limiter.admit(), 0)
        now[0] = 159.75
        self.assertEqual(limiter.admit(), 1)
        now[0] = 160.25
        self.assertEqual(limiter.admit(), 0)  # only the first request expired
        self.assertEqual(limiter.admit(), 10)
        now[0] = 170.25
        self.assertEqual(limiter.admit(), 0)
        self.assertEqual(len(limiter.requests), 2)


class TestHttpHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ShelfScaleServer(('127.0.0.1', 0), api_key=KEY)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.now = [100.]
        self.server.limiter = RateLimiter(clock=lambda: self.now[0])

    def request(self, path, *, method='POST', keys=(), payload=None):
        body = json.dumps({} if payload is None else payload).encode()
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            conn.putrequest(method, path)
            for key in keys: conn.putheader('X-API-Key', key)
            if method == 'POST': conn.putheader('Content-Length', str(len(body)))
            conn.endheaders(body if method == 'POST' else None)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            conn.close()

    def test_all_assessment_routes_require_exact_single_key(self):
        for route in ROUTES:
            for keys in ((), ('wrong',), (KEY + 'x',), (KEY, KEY), ('é',)):
                status, _, body = self.request(route, keys=keys)
                self.assertEqual(status, 401, (route, keys))
                self.assertNotIn(KEY, json.dumps(body))
        self.assertEqual(len(self.server.limiter.requests), 0)
        with patch('shelfscale.api.hmac.compare_digest', wraps=__import__('hmac').compare_digest) as compare:
            status, _, _ = self.request('/v1/lookup', keys=(KEY,), payload={'code':'18-017'})
            self.assertEqual(status, 200)
            compare.assert_called_once()

    def test_health_root_are_public_and_never_reveal_key(self):
        for path in ('/', '/health'):
            status, headers, body = self.request(path, method='GET')
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertNotIn(KEY, json.dumps(body))
            self.assertIn('shadow model', body['models']['uk-npm-2018'])
            if path == '/':
                self.assertEqual(body['data_release'], DATA_RELEASE)
                self.assertEqual(body['limits']['requests'], 60)
                self.assertEqual(len(body['endpoints']['authenticated']), 4)
        self.assertEqual(len(self.server.limiter.requests), 0)
        self.assertEqual(self.request('/missing', method='GET')[0], 404)

    def test_quota_shared_across_routes_and_public_health_survives(self):
        # Invalid authenticated requests count too, so errors cannot bypass the quota.
        routes = list(ROUTES)
        for i in range(60):
            self.assertEqual(self.request(routes[i % 4], keys=(KEY,))[0], 400)
        status, headers, body = self.request('/v1/lookup', keys=(KEY,))
        self.assertEqual((status, headers['Retry-After']), (429, '60'))
        self.assertNotIn(KEY, json.dumps(body))
        self.assertEqual(self.request('/health', method='GET')[0], 200)
        self.assertEqual(self.request('/', method='GET')[0], 200)
        self.assertEqual(self.request('/v1/lookup')[0], 401)
        self.now[0] += 59.5
        self.assertEqual(self.request('/v1/assess', keys=(KEY,))[1]['Retry-After'], '1')
        self.now[0] += .5
        self.assertEqual(self.request('/v1/lookup', keys=(KEY,), payload={'code':'18-017'})[0], 200)
        self.assertEqual(len(self.server.limiter.requests), 1)

    def test_env_key_and_revision_read_only_at_startup(self):
        with patch.dict(os.environ, {'SHELFSCALE_API_KEY':KEY, 'RAILWAY_GIT_COMMIT_SHA':'a'*40}):
            with ShelfScaleServer(('127.0.0.1', 0)) as server:
                self.assertEqual(server.api_key, KEY.encode())
                self.assertEqual(server.revision, 'a'*40)
        with patch.dict(os.environ, {'RAILWAY_GIT_COMMIT_SHA':KEY}):
            with ShelfScaleServer(('127.0.0.1', 0), api_key=KEY) as server:
                self.assertIsNone(server.revision)
