"""Read-only adapter tests; every watcher and event is synthetic."""
import io
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from activity_dashboard import activitywatch as aw


NOW = datetime(2026, 10, 16, 12, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))


def bucket(kind, host='SYNTHETIC-MAC'):
    return {'type': kind, 'hostname': host, 'client': 'synthetic-test'}


class FakeReader:
    def __init__(self, buckets, events=None):
        self.buckets = buckets
        self.events = events or {}
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        if path == '/buckets/':
            return self.buckets
        for bucket_id, response in self.events.items():
            if path.startswith('/buckets/' + aw.quote(bucket_id, safe='') + '/events?'):
                if isinstance(response, Exception):
                    raise response
                return response
        return []


class DiscoveryTests(unittest.TestCase):
    def test_unknown_identity_requires_explicit_mapping(self):
        reader = FakeReader({
            'unknown-window': bucket('currentwindow', 'unknown'),
            'unknown-web': bucket('web.tab.current', ''),
            'localhost-afk': bucket('afkstatus', 'localhost'),
        })
        buckets, devices, warnings = aw.discover(reader)
        self.assertEqual(buckets, [])
        self.assertEqual(devices, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn('3 watcher bucket(s)', warnings[0])
        buckets, devices, warnings = aw.discover(reader, {
            'bucket_devices': {'unknown-window': 'SYNTHETIC-MAC',
                               'unknown-web': 'SYNTHETIC-MAC'},
        })
        self.assertEqual({b['id'] for b in buckets}, {'unknown-window', 'unknown-web'})
        self.assertEqual(devices, [{'id': 'SYNTHETIC-MAC', 'label': 'SYNTHETIC-MAC'}])
        self.assertIn('1 watcher bucket(s)', warnings[0])

    def test_browser_only_buckets_cannot_nominate_a_device(self):
        reader = FakeReader({'web': bucket('web.tab.current')})
        buckets, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        self.assertEqual(buckets, [])
        self.assertEqual(status['backend'], 'unconfigured')
        self.assertEqual(status['devices'], [])
        self.assertEqual(reader.calls, ['/buckets/'])

    def test_unrelated_bucket_types_and_malformed_metadata_ignored(self):
        reader = FakeReader({
            'window': bucket('currentwindow'),
            'afk': bucket('afkstatus'),
            'private-other': bucket('app.editor.activity'),
            'background-jobs': bucket('orca.background'),
            'broken': None,
        })
        result, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        self.assertEqual({b['id'] for b in result}, {'window', 'afk'})
        self.assertEqual(len(reader.calls), 3)
        self.assertFalse(any('private-other' in call or 'background-jobs' in call for call in reader.calls))

    def test_malformed_bucket_list_rejected(self):
        with self.assertRaises(aw.ActivityWatchError):
            aw.discover(FakeReader([]))


class LoadTests(unittest.TestCase):
    def test_multiple_devices_require_choice_then_read_only_chosen_host(self):
        reader = FakeReader({
            'window-a': bucket('currentwindow', 'SYNTHETIC-A'),
            'afk-a': bucket('afkstatus', 'SYNTHETIC-A'),
            'window-b': bucket('currentwindow', 'SYNTHETIC-B'),
            'afk-b': bucket('afkstatus', 'SYNTHETIC-B'),
            'web-b': bucket('web.tab.current', 'SYNTHETIC-B'),
            'web-unassigned': bucket('web.tab.current', 'unknown'),
        })
        result, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        self.assertEqual(result, [])
        self.assertIsNone(status['selectedDevice'])
        self.assertEqual(status['backend'], 'unconfigured')
        self.assertEqual(reader.calls, ['/buckets/'])
        reader.calls.clear()
        result, status = aw.load(2026, '2026-10-16', device='SYNTHETIC-B', reader=reader, now=NOW)
        self.assertEqual(status['selectedDevice'], 'SYNTHETIC-B')
        self.assertEqual({b['id'] for b in result}, {'window-b', 'afk-b', 'web-b'})
        self.assertEqual(len(reader.calls), 4)
        self.assertFalse(any('/window-a/' in call or '/afk-a/' in call or 'web-unassigned/' in call for call in reader.calls))

    def test_unknown_device_rejected_without_event_reads(self):
        reader = FakeReader({'window': bucket('currentwindow')})
        with self.assertRaises(ValueError):
            aw.load(2026, '2026-10-16', device='NOT-A-DEVICE', reader=reader, now=NOW)
        self.assertEqual(reader.calls, ['/buckets/'])

    def test_query_is_bounded_padded_local_year_and_unlimited(self):
        reader = FakeReader({'window/name + test': bucket('currentwindow')})
        aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        path = reader.calls[1]
        self.assertTrue(path.startswith('/buckets/window%2Fname%20%2B%20test/events?'))
        query = parse_qs(urlsplit(path).query)
        self.assertEqual(query['start'], ['2025-12-25T00:00:00+07:00'])
        self.assertEqual(query['end'], [NOW.isoformat()])
        self.assertEqual(query['limit'], ['-1'])
        self.assertNotIn('offset', query)

    def test_past_year_has_week_padding_and_future_year_has_no_reads(self):
        reader = FakeReader({'window': bucket('currentwindow')})
        aw.load(2025, '2025-01-01', reader=reader, now=NOW)
        query = parse_qs(urlsplit(reader.calls[1]).query)
        self.assertEqual(query['end'], ['2026-01-08T00:00:00+07:00'])
        reader.calls.clear()
        result, _ = aw.load(2028, '2028-01-01', reader=reader, now=NOW)
        self.assertEqual(result[0]['events'], [])
        self.assertEqual(reader.calls, ['/buckets/'])

    def test_second_bucket_failure_aborts_instead_of_returning_partial_totals(self):
        reader = FakeReader({'window': bucket('currentwindow'), 'afk': bucket('afkstatus')}, {
            'window': [{'timestamp': NOW.isoformat(), 'duration': 30, 'data': {'app': 'Code'}}],
            'afk': aw.ActivityWatchError('synthetic read failure'),
        })
        with self.assertRaisesRegex(aw.ActivityWatchError, 'synthetic read failure'):
            aw.load(2026, '2026-10-16', reader=reader, now=NOW)

    def test_malformed_event_response_rejected(self):
        reader = FakeReader({'window': bucket('currentwindow')}, {'window': {'error': 'synthetic'}})
        with self.assertRaisesRegex(aw.ActivityWatchError, 'no partial totals'):
            aw.load(2026, '2026-10-16', reader=reader, now=NOW)

    def test_empty_and_absent_watchers_have_different_status(self):
        reader = FakeReader({'window': bucket('currentwindow')})
        _, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        watchers = {w['kind']: w for w in status['watchers']}
        self.assertEqual(watchers['window']['status'], 'available')
        self.assertIn('no events', watchers['window']['message'])
        self.assertEqual(watchers['afk']['status'], 'missing')
        self.assertEqual(watchers['browser']['status'], 'missing')

    def test_malformed_events_do_not_crash_or_claim_recent_collection(self):
        bad_events = [None, 7, [], {}, {'timestamp': 123, 'duration': 60},
                      {'timestamp': [], 'duration': 60},
                      {'timestamp': 'invalid', 'duration': 60},
                      {'timestamp': '2026-10-16T12:00:00', 'duration': 60}]
        for duration in [None, '60', True, False, 0, -1, float('nan'),
                         float('inf'), float('-inf'), 10 ** 400]:
            bad_events.append({'timestamp': NOW.isoformat(), 'duration': duration})
        reader = FakeReader({'window': bucket('currentwindow')}, {'window': bad_events})
        _, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        watcher = next(w for w in status['watchers'] if w['kind'] == 'window')
        self.assertEqual(watcher['status'], 'available')
        self.assertNotIn('Last observed', watcher['message'])

    def test_valid_event_status_remains_recent_or_stale_among_invalid_records(self):
        reader = FakeReader({'window': bucket('currentwindow'), 'afk': bucket('afkstatus')}, {
            'window': [{'timestamp': 123, 'duration': 60},
                       {'timestamp': '2026-10-16T11:59:00+07:00', 'duration': 30}],
            'afk': [None, {'timestamp': '2026-10-16T09:00:00+07:00', 'duration': 60}],
        })
        _, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        watchers = {w['kind']: w for w in status['watchers']}
        self.assertEqual(watchers['window']['status'], 'recent')
        self.assertEqual(watchers['afk']['status'], 'stale')

    def test_chrome_family_warning_cleared_by_exact_explicit_mapping(self):
        reader = FakeReader({'window': bucket('currentwindow'), 'aw-watcher-web-chrome_SYNTHETIC-MAC': bucket('web.tab.current')})
        _, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW)
        self.assertTrue(any('Edge' in warning for warning in status['warnings']))
        _, status = aw.load(2026, '2026-10-16', reader=reader, now=NOW,
                            config={'rules': {'browser_bucket_map': {'aw-watcher-web-chrome_SYNTHETIC-MAC': 'edge'}}})
        self.assertFalse(any('Edge' in warning for warning in status['warnings']))


class ReadJsonTests(unittest.TestCase):
    def test_fixed_loopback_json_read_with_no_proxy(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"synthetic": true}'
        opener = Mock()
        opener.open.return_value = response
        with patch.object(aw, 'build_opener', return_value=opener) as builder:
            self.assertEqual(aw.read_json('/buckets/'), {'synthetic': True})
        proxy_handler, redirect_handler = builder.call_args.args
        self.assertEqual(proxy_handler.proxies, {})
        self.assertIsInstance(redirect_handler, aw.NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:5600/api/0/buckets/')
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 12)

    def test_connection_or_json_failure_is_explicit(self):
        opener = Mock()
        opener.open.side_effect = URLError('synthetic offline')
        with patch.object(aw, 'build_opener', return_value=opener):
            with self.assertRaises(aw.ActivityWatchError):
                aw.read_json('/buckets/')
        opener.open.side_effect = None
        opener.open.return_value = io.BytesIO(b'not json')
        with patch.object(aw, 'build_opener', return_value=opener):
            with self.assertRaises(aw.ActivityWatchError):
                aw.read_json('/buckets/')

    def test_oversized_response_and_redirect_are_rejected(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'123456')
        with patch.object(aw, 'MAX_RESPONSE', 5), patch.object(aw, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(aw.ActivityWatchError, 'no partial totals'):
                aw.read_json('/buckets/')
        with self.assertRaisesRegex(aw.ActivityWatchError, 'redirect'):
            aw.NoRedirect().redirect_request(None, None, 302, 'Redirect', {}, 'https://example.invalid')


if __name__ == '__main__':
    unittest.main()
