"""Read-only ActivityWatch adapter. Only contacts the fixed IPv4 loopback endpoint."""
from datetime import datetime, timedelta
import json
import math
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from zoneinfo import ZoneInfo

BASE_URL = 'http://127.0.0.1:5600/api/0'
MAX_RESPONSE = 128 * 1024 * 1024
KINDS = {'currentwindow': 'window', 'afkstatus': 'afk', 'web.tab.current': 'browser'}


class ActivityWatchError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ActivityWatchError('ActivityWatch returned a redirect; refused to leave localhost.')


def read_json(path):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(Request(BASE_URL + path, headers={'Accept': 'application/json'}), timeout=12) as response:
            payload = response.read(MAX_RESPONSE + 1)
        if len(payload) > MAX_RESPONSE:
            raise ActivityWatchError('ActivityWatch response exceeded the local safety limit; no partial totals shown.')
        return json.loads(payload)
    except ActivityWatchError:
        raise
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ActivityWatchError('Cannot read ActivityWatch at 127.0.0.1:5600. Start ActivityWatch and check its local web UI.') from exc


def discover(reader=read_json, config=None):
    raw = reader('/buckets/')
    if not isinstance(raw, dict):
        raise ActivityWatchError('ActivityWatch returned an unexpected bucket list.')
    mapping = (config or {}).get('bucket_devices', {})
    buckets = []
    ignored = 0
    for bucket_id, info in raw.items():
        if not isinstance(info, dict) or info.get('type') not in KINDS:
            continue
        host = str(mapping.get(bucket_id) or info.get('hostname') or '')
        if host.lower() in ('unknown', 'localhost', ''):
            ignored += 1
            continue
        buckets.append({**info, 'id': bucket_id, 'hostname': host})
    # Require a real window/idle source to nominate a device; never pool machines.
    devices = sorted({b['hostname'] for b in buckets if b['type'] in ('currentwindow', 'afkstatus')})
    warnings = []
    if ignored:
        warnings.append(f'{ignored} watcher bucket(s) have no reliable device identity. Assign exact IDs in config.json bucket_devices to include them.')
    return buckets, [{'id': d, 'label': d} for d in devices], warnings


def load(year, selected_date, device=None, config=None, reader=read_json, now=None):
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    now = now or datetime.now(tz)
    buckets, devices, warnings = discover(reader, config)
    if device and device not in {d['id'] for d in devices}:
        raise ValueError('The selected device is not present in ActivityWatch.')
    # A single machine may be selected automatically. Multiple machines require explicit selection.
    selected_device = device or (devices[0]['id'] if len(devices) == 1 else None)
    status = {
        'backend': 'connected' if selected_device else 'unconfigured',
        'message': 'Reading this device from local ActivityWatch.' if selected_device else ('Choose a device to avoid combining machines.' if devices else 'No window or idle watcher buckets yet. Finish ActivityWatch setup.'),
        'devices': devices, 'selectedDevice': selected_device, 'watchers': [], 'warnings': warnings,
    }
    if not selected_device:
        return [], status
    selected = [b for b in buckets if b['hostname'] == selected_device]
    start = datetime(year, 1, 1, tzinfo=tz) - timedelta(days=7)
    end = min(datetime(year + 1, 1, 1, tzinfo=tz) + timedelta(days=7), now)
    if end <= start:
        end = start
    for bucket in selected:
        query = urlencode({'start': start.isoformat(), 'end': end.isoformat(), 'limit': -1})
        events = reader('/buckets/' + quote(bucket['id'], safe='') + '/events?' + query) if end > start else []
        if not isinstance(events, list):
            raise ActivityWatchError('ActivityWatch returned an unexpected event response; no partial totals shown.')
        bucket['events'] = events
    for kind in ('window', 'afk', 'browser'):
        matching = [b for b in selected if KINDS[b['type']] == kind]
        ends = []
        for bucket in matching:
            for event in bucket['events']:
                try:
                    if not isinstance(event, dict) or not isinstance(event.get('timestamp'), str):
                        continue
                    duration = event.get('duration')
                    if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or duration <= 0:
                        continue
                    dt = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    if dt.tzinfo is not None:
                        ends.append(dt + timedelta(seconds=duration))
                except (ValueError, KeyError, TypeError, OverflowError):
                    continue
        last_end = max(ends, default=None)
        state = 'missing' if not matching else 'available'
        message = 'No bucket found.' if not matching else 'Bucket present; no events in this period.'
        if last_end:
            state = 'recent' if (now - last_end).total_seconds() < 600 else 'stale'
            message = f'Last observed event end: {last_end.astimezone(tz).isoformat(timespec="seconds")}.'
        status['watchers'].append({'kind': kind, 'status': state, 'message': message})
    if any(b['type'] == 'web.tab.current' and 'chrome' in b['id'].lower() and b['id'] not in (config or {}).get('rules', {}).get('browser_bucket_map', {}) for b in selected):
        warnings.append('Chromium extension buckets can be named chrome in Edge. If this is Edge, map its exact bucket ID to edge in rules.browser_bucket_map; unmatched browser time stays Other.')
    return selected, status
