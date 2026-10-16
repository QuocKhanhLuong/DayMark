#!/usr/bin/env python3
"""Manual daily aggregate sync. Default is dry-run; --send explicitly uploads."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from zoneinfo import ZoneInfo

from activity_dashboard.export import ExportError, export_snapshot
from server import Dashboard

ROOT = Path(__file__).resolve().parent


class SyncError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError('The sync server redirected the request. No redirected upload was allowed.')


def validate_origin(origin):
    try:
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
            raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9.-]+', parsed.hostname) or '.' not in parsed.hostname:
            raise ValueError()
    except (TypeError, ValueError):
        raise SyncError('Use the exact configured HTTPS origin, without a path, query, or credentials.') from None
    return origin


def send_payload(payload, origin, token, opener=None):
    validate_origin(origin)
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise SyncError('DAYMARK_SYNC_TOKEN is missing or invalid.')
    body = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(body) > 128 * 1024:
        raise SyncError('Aggregate payload exceeds 128 KiB.')
    request = Request(origin + '/api/sync', data=body, method='POST', headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'Accept': 'application/json',
    })
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise SyncError('The server did not confirm the sync. No automatic retry was made.')
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError()
        receipt = json.loads(raw)
        if (not isinstance(receipt, dict) or set(receipt) != {'acceptedDays', 'lastSync'}
                or isinstance(receipt['acceptedDays'], bool) or receipt['acceptedDays'] != len(payload['days'])
                or not isinstance(receipt['lastSync'], str)):
            raise ValueError()
        timestamp = datetime.fromisoformat(receipt['lastSync'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError()
        return {'acceptedDays': receipt['acceptedDays'], 'lastSync': timestamp.astimezone(timezone.utc).isoformat()}
    except SyncError:
        raise
    except (OSError, URLError, ValueError, KeyError, TypeError):
        raise SyncError('Sync outcome is unconfirmed. Check the dashboard last-sync time before retrying. No server body or credentials were logged.') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, default=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).year)
    parser.add_argument('--device', help='Exact local ActivityWatch device identity; never uploaded')
    parser.add_argument('--origin', help='Exact approved HTTPS dashboard origin')
    parser.add_argument('--send', action='store_true', help='Explicitly upload the whitelisted daily aggregates')
    args = parser.parse_args(argv)
    try:
        config_path = ROOT / 'config.json'
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
        selected = now.date().isoformat() if args.year == now.year else f'{args.year}-01-01'
        query = {'year': [str(args.year)], 'date': [selected], 'source': ['live']}
        if args.device:
            query['device'] = [args.device]
        payload = export_snapshot(Dashboard(config).get(query))
        known = sum(day['seconds'] is not None for day in payload['days'])
        if not args.send:
            print(f'Dry run: {len(payload["days"])} dates, {known} observed days. Nothing uploaded.')
            return 0
        if not args.origin:
            raise SyncError('--send requires the exact --origin.')
        receipt = send_payload(payload, args.origin, os.environ.get('DAYMARK_SYNC_TOKEN'))
        print(f'Synced {receipt["acceptedDays"]} dates. Server receipt: {receipt["lastSync"]}.')
        return 0
    except (SyncError, ExportError, ValueError):
        # Config or upstream exception messages may contain private values; keep the CLI output fixed.
        print('Sync could not be completed. Verify the live source, configured HTTPS origin, and token. No raw records or credentials were logged.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
