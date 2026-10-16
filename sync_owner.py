#!/usr/bin/env python3
"""Owner-run manual aggregate sync; never run with live credentials by an agent."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

from sync import collect_payload, send_payload

ROOT = Path(__file__).resolve().parent
ORIGIN = 'https://daymark-private.vercel.app'


def private_json(name, data):
    path = ROOT / '.runtime' / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream)
        stream.write('\n')
    path.chmod(0o600)


def run_interactive():
    try:
        year = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).year
        payload = collect_payload(year)
        observed = sum(day['seconds'] is not None for day in payload['days'])
        if not observed:
            print('No observed days to sync. Keep ActivityWatch running, then try later. Nothing uploaded.')
            return 1
    except Exception:
        print('Live activity could not be prepared. Check ActivityWatch and the selected device. Nothing uploaded.')
        return 1
    print('Daymark manual sync to ' + ORIGIN)
    print(f'{len(payload["days"])} elapsed dates; {observed} observed days. Missing days remain unknown.')
    print('Only dates, coverage status, and six category durations are sent. No URLs, window titles, device IDs, or detailed intervals.')
    try:
        if input('Type SYNC to upload this aggregate snapshot (anything else cancels): ') != 'SYNC':
            print('Cancelled. Nothing uploaded.')
            return 0
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled. Nothing uploaded.')
        return 0
    try:
        secrets = json.loads((ROOT / '.runtime' / 'app-secrets.json').read_text())
        token = secrets['DAYMARK_SYNC_TOKEN']
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
            raise ValueError()
        attempt = {'origin': ORIGIN, 'attemptedAt': datetime.now(timezone.utc).isoformat(),
                   'dates': len(payload['days']), 'observedDays': observed, 'status': 'pending'}
        private_json('sync-attempt.json', attempt)
    except Exception:
        print('Private sync setup is missing or invalid. Nothing uploaded. No credential values were printed.')
        return 1
    try:
        receipt = send_payload(payload, ORIGIN, token)
    except Exception:
        attempt['status'] = 'uncertain'
        try:
            private_json('sync-attempt.json', attempt)
        except Exception:
            pass
        print('Sync outcome is unconfirmed. Check Last sync on the web dashboard before trying again. No automatic retry was made.')
        return 1
    saved = {'origin': ORIGIN, 'acceptedDays': receipt['acceptedDays'], 'lastSync': receipt['lastSync'],
             'observedDays': observed, 'status': 'confirmed'}
    try:
        private_json('sync-receipt.json', saved)
        private_json('sync-attempt.json', {**attempt, 'status': 'confirmed'})
    except Exception:
        print('Server confirmed the upload, but the local receipt could not be saved.')
    print(f'Synced {receipt["acceptedDays"]} dates. Server receipt: {receipt["lastSync"]}.')
    print('Refresh Daymark in your browser to see the heatmap and daily totals. Partial days remain partial.')
    return 0


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('Open sync-now.command yourself in a private terminal. Nothing uploaded.')
        return 1
    return run_interactive()


if __name__ == '__main__':
    raise SystemExit(main())
