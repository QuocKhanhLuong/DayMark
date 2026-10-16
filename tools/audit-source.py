#!/usr/bin/env python3
"""Check candidate or staged source without printing sensitive matches.

This is a publication check, not a guarantee against every possible secret.
--check-local-runtime also compares against this checkout's private setup values.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'.runtime', '.vercel', 'node_modules', '.next', '__pycache__'}
FORBIDDEN_SUFFIXES = {'.log', '.db', '.sqlite', '.sqlite3', '.dmg', '.pyc', '.tsbuildinfo'}
TOKEN = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|npg_[A-Za-z0-9]{16,}|sk_live_[A-Za-z0-9]{16,})')
PRIVATE_KEY = re.compile(rb'-{5}BEGIN [A-Z ]*PRIVATE KEY-{5}')
CONNECTION = re.compile(rb'postgres(?:ql)?://[^\s\x22\x27<>]+')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def private_values():
    values = set()
    keys = {'DATABASE_URL', 'DATABASE_URL_UNPOOLED', 'BETTER_AUTH_SECRET',
            'DAYMARK_SYNC_TOKEN', 'email', 'ownerId'}
    for name in ('database.json', 'app-secrets.json', 'owner-settings.json', 'owner-id.json'):
        path = ROOT / '.runtime' / name
        if path.exists():
            data = json.loads(path.read_text())
            for key, value in data.items():
                if key in keys and isinstance(value, str) and len(value) >= 8:
                    values.add(value.encode())
    path = ROOT / '.runtime' / 'cloud.env'
    if path.exists():
        for line in path.read_text().splitlines():
            key, separator, value = line.partition('=')
            if separator and key in keys:
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
                if isinstance(value, str) and len(value) >= 8:
                    values.add(value.encode())
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--check-local-runtime', action='store_true')
    args = parser.parse_args()
    listing = git('ls-files', '-z') if args.staged else git('ls-files', '-z', '--cached', '--others', '--exclude-standard')
    paths = sorted({name.decode() for name in listing.split(b'\0') if name})
    secrets = private_values() if args.check_local_runtime else set()
    findings = []
    for name in paths:
        path = ROOT / name
        parts = Path(name).parts
        if (FORBIDDEN_PARTS.intersection(parts) or Path(name).name.startswith('.env')
                or Path(name).suffix in FORBIDDEN_SUFFIXES
                or name in ('config.json', 'docs/CONTINUATION.md') or path.is_symlink()):
            findings.append((name, 'forbidden generated/private path'))
            continue
        data = git('show', ':' + name) if args.staged else path.read_bytes()
        if b'\0' in data or len(data) > 2 * 1024 * 1024:
            findings.append((name, 'unexpected binary/large file'))
        if any(value in data for value in secrets):
            findings.append((name, 'matches a private local setup value'))
        if TOKEN.search(data) or PRIVATE_KEY.search(data):
            findings.append((name, 'credential-shaped content'))
        for match in CONNECTION.finditer(data):
            # The only allowed URI is an explicitly synthetic error-redaction fixture.
            if name != 'cloud/tests/security.test.ts' or match.group() != b'postgres:' + b'//SECRET':
                findings.append((name, 'database URI'))
        if re.search(b'/' + rb'Users/[^/\s]+/|[A-Za-z0-9_.+-]+@gmail\.com', data):
            findings.append((name, 'personal account path or email'))
    if findings:
        for name, reason in sorted(set(findings)):
            print(f'FAIL {name}: {reason}; matched values withheld')
        return 1
    print(f'PASS: {len(paths)} source files checked; no forbidden paths, local setup values, credential patterns, database URIs, private keys, or personal account paths/emails found.')
    print('Synthetic fixtures remain source-only. No raw ActivityWatch files are included.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
