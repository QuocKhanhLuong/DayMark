#!/usr/bin/env python3
"""Read an approved database URI privately from stdin; never print its value."""
import json, os, sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

root=Path(__file__).resolve().parents[1]/'.runtime'
previous=None
if sys.stdin.isatty():
    import termios
    previous=termios.tcgetattr(sys.stdin.fileno())
    hidden=termios.tcgetattr(sys.stdin.fileno())
    hidden[3]&=~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,hidden)
print('Ready for private credential transport.',flush=True)
try:
    raw=sys.stdin.readline()
finally:
    if previous is not None:
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,previous)
try:
    uri=json.loads(raw)
    parsed=urlsplit(uri)
    if parsed.scheme not in ('postgres','postgresql') or not (parsed.hostname or '').endswith('.neon.tech') or parse_qs(parsed.query).get('sslmode')!=['require'] or any(ord(c)<32 for c in uri):
        raise ValueError()
    path=root/'database.json'
    if path.exists():
        current=json.loads(path.read_text())
        if current.get('DATABASE_URL_UNPOOLED')!=uri:
            raise ValueError('Existing database connection differs; refused replacement.')
    else:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump({'DATABASE_URL_UNPOOLED':uri},f)
    secrets=json.loads((root/'app-secrets.json').read_text())
    env={'DATABASE_URL':uri,'BETTER_AUTH_SECRET':secrets['BETTER_AUTH_SECRET'],'APP_ORIGIN':'https://daymark.invalid'}
    envpath=root/'cloud.env'
    fd=os.open(envpath,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:
        for key,value in env.items():f.write(key+'='+json.dumps(value)+'\n')
    print('Database connection stored privately. No credential value was printed.')
except Exception:
    print('Private database credential storage failed; no details printed.',file=sys.stderr)
    sys.exit(1)
