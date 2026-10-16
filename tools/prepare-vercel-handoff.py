#!/usr/bin/env python3
"""Owner-run local preparation only. Never uploads or prints secret values."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ORIGIN = 'https://daymark-private.vercel.app'
KEYS = ('APP_ORIGIN', 'DATABASE_URL', 'BETTER_AUTH_SECRET', 'OWNER_USER_ID', 'SYNC_TOKEN_SHA256')


def values_from(runtime):
    database = json.loads((runtime / 'database.json').read_text())
    secrets = json.loads((runtime / 'app-secrets.json').read_text())
    owner = json.loads((runtime / 'owner-id.json').read_text())
    uri = urlsplit(database['DATABASE_URL_UNPOOLED'])
    if (uri.scheme not in ('postgres', 'postgresql') or not uri.hostname
            or not uri.hostname.startswith('ep-') or not uri.hostname.endswith('.neon.tech')
            or uri.path != '/daymark' or not uri.username or not uri.password
            or uri.port not in (None, 5432) or uri.fragment):
        raise ValueError('Unexpected database connection.')
    label, suffix = uri.hostname.split('.', 1)
    if not label.endswith('-pooler'):
        label += '-pooler'
    netloc = uri.netloc.replace(uri.hostname, label + '.' + suffix)
    query = dict(parse_qsl(uri.query))
    query['sslmode'] = 'verify-full'
    signing = secrets['BETTER_AUTH_SECRET']
    token = secrets['DAYMARK_SYNC_TOKEN']
    owner_id = owner['ownerId']
    if (not isinstance(signing, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', signing)
            or not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token)
            or not isinstance(owner_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', owner_id)):
        raise ValueError('Unexpected private setup value.')
    return {
        'APP_ORIGIN': ORIGIN,
        'DATABASE_URL': urlunsplit((uri.scheme, netloc, uri.path, urlencode(query), '')),
        'BETTER_AUTH_SECRET': signing,
        'OWNER_USER_ID': owner_id,
        'SYNC_TOKEN_SHA256': hashlib.sha256(token.encode()).hexdigest(),
    }


def write_handoff(runtime, values):
    if set(values) != set(KEYS) or runtime.is_symlink():
        raise ValueError('Unexpected handoff scope.')
    folder = runtime / 'vercel-handoff'
    if folder.is_symlink():
        raise ValueError('Unexpected output path.')
    folder.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)
    for key in KEYS:
        path = folder / (key + '.txt')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(values[key])
        path.chmod(0o600)
    return folder


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('Open prepare-vercel.command yourself in a private terminal. Nothing was prepared.')
        return 1
    runtime = Path(__file__).resolve().parents[1] / '.runtime'
    if not (runtime / 'owner-id.json').exists():
        print('First finish setup-owner.command: enter your password twice and type CREATE. No account password belongs in Vercel settings.')
        return 1
    try:
        folder = write_handoff(runtime, values_from(runtime))
    except Exception:
        print('Local handoff preparation failed. No private value or upstream details were printed.')
        return 1
    print('Prepared five owner-readable local text files. Nothing was uploaded.')
    print('Folder: ' + str(folder))
    print('Open each file yourself; copy its entire value directly into the matching Vercel project field.')
    print('Use Production only and Secret type (legacy Sensitive). Never send the values in chat or screenshots.')
    print('Keys: ' + ', '.join(KEYS))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
