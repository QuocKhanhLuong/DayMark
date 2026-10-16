#!/usr/bin/env python3
"""Local-only daily activity dashboard. Run: python3 server.py"""
import argparse
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from activity_dashboard.aggregate import aggregate
from activity_dashboard.activitywatch import ActivityWatchError, load
from activity_dashboard.demo import demo_buckets

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'activity_dashboard' / 'static'
TZ = ZoneInfo('Asia/Ho_Chi_Minh')
ORCA_STATUS = {'status': 'unsupported', 'message': 'Background run duration is unsupported: Orca has no verified general run start/end feed. Foreground Orca time is counted separately by ActivityWatch. App uptime and terminal lifetime are never used as execution time.'}


class Dashboard:
    def __init__(self, config=None, loader=load):
        self.config = config or {}
        self.loader = loader
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, query):
        now = datetime.now(TZ)
        try:
            source = query.get('source', ['live'])[0]
            year = int(query.get('year', [str(now.year)])[0])
            selected = query.get('date', [now.date().isoformat() if year == now.year else f'{year}-01-01'])[0]
            chosen_date = date.fromisoformat(selected)
        except (ValueError, TypeError):
            raise ValueError('Use a valid year and ISO date (YYYY-MM-DD).')
        if source not in ('live', 'demo') or not 2000 <= year <= 2100 or chosen_date.year != year or chosen_date.isoformat() != selected:
            raise ValueError('Source must be live or demo; date must belong to selected year (2000–2100).')
        device = query.get('device', [None])[0] or None
        if source == 'demo':
            buckets = demo_buckets(year, now)
            status = {'backend': 'demo', 'message': 'Synthetic demonstration only — these are invented examples, not your activity.', 'devices': [], 'selectedDevice': None, 'watchers': [], 'warnings': []}
        else:
            key = (year, device)
            with self.lock:
                entry = self.cache.get(key)
                if entry and time.monotonic() - entry[0] < 30:
                    buckets, status = entry[1:]
                else:
                    try:
                        buckets, status = self.loader(year, selected, device, self.config, now=now)
                        self.cache[key] = (time.monotonic(), buckets, status)
                        # Bound memory when browsing many years/devices.
                        if len(self.cache) > 4:
                            del self.cache[next(iter(self.cache))]
                    except ActivityWatchError as exc:
                        buckets = []
                        status = {'backend': 'unavailable', 'message': str(exc), 'devices': [], 'selectedDevice': None, 'watchers': [], 'warnings': ['No saved dashboard copy is substituted. Missing collection is shown as unknown.']}
        payload = aggregate(buckets, year, selected, now=now, rules=self.config.get('rules', {}))
        payload.update(source=source, status={**status, 'orcaBackground': ORCA_STATUS})
        return payload


class Handler(BaseHTTPRequestHandler):
    server_version = 'LocalActivity/1.0'

    def log_message(self, format, *args):
        # Do not log URLs, titles, selected device names, or request query strings.
        pass

    def send_bytes(self, code, body, mime='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        origin = self.headers.get('Origin')
        if (self.headers.get('Host') not in allowed or
            (origin and origin not in {f'http://{host}' for host in allowed}) or
            self.headers.get('Sec-Fetch-Site') == 'cross-site'):
            self.send_bytes(403, b'{"error":"Only same-origin localhost requests are allowed."}')
            return
        parsed = urlsplit(self.path)
        if parsed.path == '/api/dashboard':
            try:
                data = self.server.dashboard.get(parse_qs(parsed.query))
                self.send_bytes(200, json.dumps(data, allow_nan=False).encode())
            except ValueError as exc:
                self.send_bytes(400, json.dumps({'error': str(exc)}).encode())
            except Exception:
                self.send_bytes(500, b'{"error":"Dashboard could not compute this period. Check local setup and event data."}')
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/styles.css': ('styles.css', 'text/css; charset=utf-8'), '/app.mjs': ('app.mjs', 'text/javascript; charset=utf-8'), '/model.mjs': ('model.mjs', 'text/javascript; charset=utf-8')}
        if parsed.path in files:
            name, mime = files[parsed.path]
            try:
                self.send_bytes(200, (STATIC / name).read_bytes(), mime)
            except FileNotFoundError:
                self.send_bytes(404, b'{"error":"Static file missing."}')
        else:
            self.send_bytes(404, b'{"error":"Not found."}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config.exists() else {}
    if not isinstance(config, dict):
        raise SystemExit('Configuration must be a JSON object.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.dashboard = Dashboard(config)
    print(f'Daily activity dashboard: http://127.0.0.1:{server.server_port}', flush=True)
    print('Local only. Ctrl+C stops the dashboard. ActivityWatch is a separate collector.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
