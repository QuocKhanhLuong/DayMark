"""Synthetic aggregate-only sync boundary tests. Never contact a remote service."""
import contextlib
from datetime import datetime
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from activity_dashboard.export import export_snapshot, ExportError
from sync import send_payload, validate_origin, SyncError, NoRedirect, main

CATS = ('coding', 'github', 'chatgpt', 'orca', 'reading', 'other')
TOKEN = 'synthetic-test-token-ONLY-12345678901234567890'


def snapshot():
    return {'source': 'live', 'timezone': 'Asia/Ho_Chi_Minh', 'today': '2026-10-16',
            'status': {'backend': 'connected', 'selectedDevice': 'PRIVATE DEVICE'},
            'title': 'PRIVATE TITLE', 'url': 'https://private.example',
            'days': [
                {'date': '2026-10-15', 'status': 'missing', 'totalSeconds': None, 'categories': dict.fromkeys(CATS, 0)},
                {'date': '2026-10-16', 'status': 'partial', 'totalSeconds': 60, 'categories': {c: 60 if c == 'coding' else 0 for c in CATS}, 'segments': [{'title': 'PRIVATE TITLE'}]},
                {'date': '2026-10-17', 'status': 'future', 'totalSeconds': None}
            ]}


class Response:
    status = 200
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.data[:limit]


class ExportTests(unittest.TestCase):
    def test_whitelist_has_no_raw_data_device_or_future_days(self):
        result = export_snapshot(snapshot())
        self.assertEqual(set(result), {'schemaVersion', 'timeZone', 'days'})
        self.assertEqual(len(result['days']), 2)
        for day in result['days']: self.assertEqual(set(day), {'date', 'status', 'seconds'})
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('https:', json.dumps(result))
        self.assertIsNone(result['days'][0]['seconds'])
        self.assertEqual(result['days'][1]['seconds']['coding'], 60)

    def test_demo_offline_unconfigured_or_wrong_timezone_are_refused(self):
        for key, value in [('source', 'demo'), ('timezone', 'UTC'), ('status', {'backend': 'unavailable'}), ('status', {'backend': 'unconfigured'})]:
            data = snapshot(); data[key] = value
            with self.assertRaises(ExportError): export_snapshot(data)

    def test_zero_is_preserved_and_missing_stays_null(self):
        data = snapshot(); day = data['days'][1]; day['categories'] = dict.fromkeys(CATS, 0); day['totalSeconds'] = 0
        self.assertEqual(sum(export_snapshot(data)['days'][1]['seconds'].values()), 0)
        self.assertIsNone(export_snapshot(data)['days'][0]['seconds'])

    def test_inconsistent_or_invalid_durations_fail_closed(self):
        for number in (-1, float('nan'), float('inf'), True, 86401):
            data = snapshot(); data['days'][1]['categories']['coding'] = number
            with self.assertRaises(ExportError): export_snapshot(data)
        data = snapshot(); data['days'][1]['totalSeconds'] = 61
        with self.assertRaises(ExportError): export_snapshot(data)

    def test_duplicates_and_invalid_dates_are_refused(self):
        data = snapshot(); data['days'].append(data['days'][0].copy())
        with self.assertRaises(ExportError): export_snapshot(data)
        data = snapshot(); data['days'][0]['date'] = '20261015'
        with self.assertRaises(ExportError): export_snapshot(data)


class SyncTests(unittest.TestCase):
    def test_origin_requires_https_and_exact_origin_without_credentials(self):
        for origin in ('http://example.com', 'https://example.com/path', 'https://a:b@example.com', 'https://example.com?x=1', 'https://example.com#part', 'https://example.com:9999', 'https://localhost'):
            with self.assertRaises(SyncError): validate_origin(origin)
        self.assertEqual(validate_origin('https://synthetic.example'), 'https://synthetic.example')

    def test_outgoing_payload_and_receipt_are_exact_and_token_is_only_header(self):
        payload = export_snapshot(snapshot())
        class Opener:
            def open(_, request, timeout):
                self.assertEqual(request.full_url, 'https://synthetic.example/api/sync')
                self.assertEqual(request.get_method(), 'POST')
                self.assertEqual(request.get_header('Authorization'), 'Bearer ' + TOKEN)
                self.assertEqual(json.loads(request.data), payload)
                self.assertNotIn(TOKEN.encode(), request.data)
                self.assertNotIn(b'PRIVATE', request.data)
                return Response(b'{"acceptedDays":2,"lastSync":"2026-10-16T10:00:00Z"}')
        receipt = send_payload(payload, 'https://synthetic.example', TOKEN, Opener())
        self.assertEqual(receipt['acceptedDays'], 2)

    def test_errors_do_not_echo_tokens_private_urls_or_server_bodies(self):
        class Opener:
            def open(_, *args, **kwargs): raise URLError('PRIVATE ' + TOKEN)
        with self.assertRaises(SyncError) as error:
            send_payload(export_snapshot(snapshot()), 'https://synthetic.example', TOKEN, Opener())
        self.assertNotIn(TOKEN, str(error.exception)); self.assertNotIn('PRIVATE', str(error.exception))

    def test_unexpected_or_incomplete_receipt_does_not_claim_success(self):
        for body in (b'{"acceptedDays":1,"lastSync":"2026-10-16T10:00:00Z"}', b'{"acceptedDays":2,"lastSync":"naive"}', b'PRIVATE', b'x' * 8193):
            class Opener:
                def open(_, *args, **kwargs): return Response(body)
            with self.assertRaises(SyncError): send_payload(export_snapshot(snapshot()), 'https://synthetic.example', TOKEN, Opener())

    def test_redirects_are_refused(self):
        with self.assertRaises(SyncError): NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example')

    def test_cli_default_dry_run_never_sends(self):
        class FakeDashboard:
            def __init__(self, *args): pass
            def get(self, query): return snapshot()
        output = io.StringIO()
        with patch('sync.Dashboard', FakeDashboard), patch('sync.send_payload') as send, contextlib.redirect_stdout(output):
            self.assertEqual(main(['--year', '2026']), 0)
        send.assert_not_called(); self.assertIn('Nothing uploaded', output.getvalue()); self.assertNotIn('PRIVATE', output.getvalue())


if __name__ == '__main__': unittest.main()
