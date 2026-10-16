"""Dashboard and HTTP tests using synthetic data and in-memory requests only."""
from contextlib import redirect_stdout
from datetime import datetime
from email.parser import BytesParser
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import server
from activity_dashboard.activitywatch import ActivityWatchError


NOW = datetime(2026, 10, 16, 12, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
LIVE_QUERY = {'source': ['live'], 'year': ['2026'], 'date': ['2026-10-16']}


def connected_status():
    return {'backend': 'connected', 'message': 'Synthetic test backend',
            'devices': [{'id': 'SYNTHETIC', 'label': 'SYNTHETIC'}],
            'selectedDevice': 'SYNTHETIC', 'watchers': [], 'warnings': []}


def synthetic_buckets():
    return [
        {'id': 'window', 'type': 'currentwindow', 'hostname': 'SYNTHETIC',
         'events': [{'timestamp': '2026-10-16T09:00:00+07:00', 'duration': 60,
                     'data': {'app': 'Visual Studio Code', 'title': 'PRIVATE_SYNTHETIC_TITLE'}}]},
        {'id': 'afk', 'type': 'afkstatus', 'hostname': 'SYNTHETIC',
         'events': [{'timestamp': '2026-10-16T09:00:00+07:00', 'duration': 60,
                     'data': {'status': 'not-afk'}}]},
    ]


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(server, 'datetime')
        self.mock_datetime = self.clock.start()
        self.mock_datetime.now.return_value = NOW
        self.addCleanup(self.clock.stop)

    def test_unavailable_live_is_missing_not_zero_or_demo(self):
        loader = Mock(side_effect=ActivityWatchError('Synthetic offline error'))
        data = server.Dashboard(loader=loader).get(LIVE_QUERY)
        self.assertEqual(data['source'], 'live')
        self.assertEqual(data['status']['backend'], 'unavailable')
        self.assertEqual(data['selected']['status'], 'missing')
        self.assertIsNone(data['selected']['totalSeconds'])
        self.assertGreater(data['selected']['unknownSeconds'], 0)
        self.assertEqual(data['selected']['segments'], [])
        self.assertTrue(all(day['totalSeconds'] is None for day in data['days']))
        self.assertEqual(data['status']['orcaBackground']['status'], 'unsupported')

    def test_connected_empty_backend_is_still_missing_not_zero(self):
        loader = Mock(return_value=([], connected_status()))
        data = server.Dashboard(loader=loader).get(LIVE_QUERY)
        self.assertEqual(data['status']['backend'], 'connected')
        self.assertEqual(data['selected']['status'], 'missing')
        self.assertIsNone(data['selected']['totalSeconds'])

    def test_demo_is_explicitly_synthetic_and_does_not_query_live_backend(self):
        loader = Mock(side_effect=AssertionError('Demo must not read live data'))
        data = server.Dashboard(loader=loader).get({**LIVE_QUERY, 'source': ['demo']})
        self.assertEqual(data['source'], 'demo')
        self.assertEqual(data['status']['backend'], 'demo')
        self.assertIn('Synthetic', data['status']['message'])
        self.assertIn('not your activity', data['status']['message'])
        loader.assert_not_called()

    def test_raw_titles_do_not_leave_dashboard_and_orca_background_is_separate(self):
        loader = Mock(return_value=(synthetic_buckets(), connected_status()))
        data = server.Dashboard(loader=loader).get(LIVE_QUERY)
        self.assertEqual(data['selected']['totalSeconds'], 60)
        self.assertEqual(data['selected']['categories']['coding'], 60)
        self.assertNotIn('PRIVATE_SYNTHETIC_TITLE', json.dumps(data))
        self.assertEqual(data['status']['orcaBackground']['status'], 'unsupported')
        self.assertNotIn('background', data['selected']['categories'])

    def test_expired_success_is_not_used_when_backend_later_fails(self):
        loader = Mock(side_effect=[(synthetic_buckets(), connected_status()),
                                   ActivityWatchError('Synthetic disconnected')])
        dashboard = server.Dashboard(loader=loader)
        with patch.object(server.time, 'monotonic', return_value=100):
            first = dashboard.get(LIVE_QUERY)
        self.assertEqual(first['selected']['totalSeconds'], 60)
        with patch.object(server.time, 'monotonic', return_value=131):
            second = dashboard.get(LIVE_QUERY)
        self.assertEqual(second['status']['backend'], 'unavailable')
        self.assertIsNone(second['selected']['totalSeconds'])
        self.assertEqual(second['selected']['segments'], [])

    def test_cached_reads_stay_scoped_to_device(self):
        loader = Mock(return_value=([], connected_status()))
        dashboard = server.Dashboard(loader=loader)
        with patch.object(server.time, 'monotonic', return_value=100):
            dashboard.get({**LIVE_QUERY, 'device': ['SYNTHETIC-A']})
            dashboard.get({**LIVE_QUERY, 'device': ['SYNTHETIC-A']})
            dashboard.get({**LIVE_QUERY, 'device': ['SYNTHETIC-B']})
        self.assertEqual(loader.call_count, 2)
        self.assertEqual([call.args[2] for call in loader.call_args_list], ['SYNTHETIC-A', 'SYNTHETIC-B'])

    def test_invalid_parameters_fail_before_live_reads(self):
        invalid = [
            {'source': ['cloud']}, {'year': ['not-a-year']}, {'year': ['1999']},
            {'year': ['2101']}, {'date': ['2026-02-30']}, {'date': ['2025-10-16']},
            {'date': ['20261016']}, {'date': ['bad']},
        ]
        loader = Mock(return_value=([], connected_status()))
        dashboard = server.Dashboard(loader=loader)
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                dashboard.get({**LIVE_QUERY, **changes})
        loader.assert_not_called()


class MemorySocket:
    """Only enough socket surface for BaseHTTPRequestHandler's normal lifecycle."""
    def __init__(self, request):
        self.incoming = io.BytesIO(request)
        self.outgoing = bytearray()

    def makefile(self, mode, buffering=None):
        return self.incoming

    def sendall(self, data):
        self.outgoing.extend(data)


class HttpTests(unittest.TestCase):
    def request(self, target='/', headers=None, dashboard=None, method='GET'):
        headers = {'Host': '127.0.0.1:8766', **(headers or {})}
        header_text = ''.join(f'{key}: {value}\r\n' for key, value in headers.items() if value is not None)
        conn = MemorySocket(f'{method} {target} HTTP/1.0\r\n{header_text}\r\n'.encode())
        runtime = SimpleNamespace(server_port=8766, dashboard=dashboard or Mock())
        server.Handler(conn, ('127.0.0.1', 12000), runtime)
        head, body = bytes(conn.outgoing).split(b'\r\n\r\n', 1)
        status_line, header_bytes = head.split(b'\r\n', 1)
        return int(status_line.split()[1]), BytesParser().parsebytes(header_bytes), body

    def test_cross_origin_and_untrusted_host_are_rejected_before_data_read(self):
        for headers in [
            {'Host': 'evil.example:8766'}, {'Host': '127.0.0.1:8765'},
            {'Host': None}, {'Origin': 'https://evil.example'},
            {'Origin': 'null'}, {'Origin': 'http://localhost:9999'},
            {'Sec-Fetch-Site': 'cross-site'},
        ]:
            dashboard = Mock()
            with self.subTest(headers=headers):
                code, _, _ = self.request('/api/dashboard', headers, dashboard)
                self.assertEqual(code, 403)
                dashboard.get.assert_not_called()

    def test_same_origin_request_returns_json_and_privacy_headers(self):
        dashboard = Mock()
        dashboard.get.return_value = {'source': 'live', 'synthetic': True}
        code, headers, body = self.request('/api/dashboard?year=2026&date=2026-10-16',
                                          {'Origin': 'http://127.0.0.1:8766', 'Sec-Fetch-Site': 'same-origin'}, dashboard)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body), {'source': 'live', 'synthetic': True})
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])
        self.assertIsNone(headers['Access-Control-Allow-Origin'])
        dashboard.get.assert_called_once_with({'year': ['2026'], 'date': ['2026-10-16']})

    def test_static_whitelist_does_not_serve_workspace_files_or_traversal(self):
        for target in ['/server.py', '/config.json', '/README.md', '/../server.py',
                       '/%2e%2e/server.py', '/activity_dashboard/activitywatch.py']:
            with self.subTest(target=target):
                code, _, _ = self.request(target)
                self.assertEqual(code, 404)
        code, headers, body = self.request('/')
        self.assertEqual(code, 200)
        self.assertIn('text/html', headers['Content-Type'])
        self.assertIn(b'<html', body.lower())

    def test_invalid_api_parameters_return_400_and_unexpected_error_is_redacted(self):
        dashboard = Mock()
        dashboard.get.side_effect = ValueError('Invalid synthetic date')
        code, _, body = self.request('/api/dashboard?date=nope', dashboard=dashboard)
        self.assertEqual(code, 400)
        self.assertIn('Invalid synthetic date', json.loads(body)['error'])
        dashboard.get.side_effect = RuntimeError('PRIVATE_SYNTHETIC_ERROR')
        code, _, body = self.request('/api/dashboard', dashboard=dashboard)
        self.assertEqual(code, 500)
        self.assertNotIn(b'PRIVATE_SYNTHETIC_ERROR', body)

    def test_no_post_endpoint_can_mutate_data(self):
        dashboard = Mock()
        code, _, _ = self.request('/api/dashboard', dashboard=dashboard, method='POST')
        self.assertEqual(code, 501)
        dashboard.get.assert_not_called()

    def test_entrypoint_binds_only_ipv4_loopback(self):
        runtime = Mock()
        runtime.server_port = 8766
        runtime.serve_forever.side_effect = KeyboardInterrupt
        with patch.object(server, 'ThreadingHTTPServer', return_value=runtime) as factory, \
                patch('sys.argv', ['server.py', '--config', '/tmp/synthetic-no-config-for-dashboard-tests.json']), \
                patch.object(server.Path, 'exists', return_value=False), redirect_stdout(io.StringIO()):
            server.main()
        factory.assert_called_once_with(('127.0.0.1', 8766), server.Handler)
        runtime.server_close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
