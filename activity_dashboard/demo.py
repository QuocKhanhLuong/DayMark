"""Deterministic synthetic fixtures. These are never stored in ActivityWatch."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Ho_Chi_Minh')


def demo_buckets(year, now=None):
    now = now or datetime.now(TZ)
    buckets = [
        {'id': 'aw-watcher-window_SYNTHETIC', 'type': 'currentwindow', 'hostname': 'SYNTHETIC', 'events': []},
        {'id': 'aw-watcher-afk_SYNTHETIC', 'type': 'afkstatus', 'hostname': 'SYNTHETIC', 'events': []},
        {'id': 'aw-watcher-web-edge_SYNTHETIC', 'type': 'web.tab.current', 'hostname': 'SYNTHETIC', 'events': []},
    ]
    def event(bucket, start, seconds, data):
        bucket['events'].append({'timestamp': start.isoformat(), 'duration': seconds, 'data': data})
    # Include adjacent weeks for week totals crossing a year boundary.
    day = date(year, 1, 1) - timedelta(days=7)
    end = min(date(year + 1, 1, 1) + timedelta(days=7), now.astimezone(TZ).date() + timedelta(days=1))
    while day < end:
        midnight = datetime.combine(day, time(), TZ)
        seed = day.toordinal()
        if seed % 13 == 0:  # Deliberately missing collection days.
            day += timedelta(days=1)
            continue
        if day.weekday() == 6:
            event(buckets[1], midnight, 86400, {'status': 'afk'})
        else:
            start = midnight + timedelta(hours=9)
            cursor = start
            event(buckets[1], midnight, 9 * 3600, {'status': 'afk'})
            tasks = [
                ('Visual Studio Code', None, 45 + seed % 50),
                ('Microsoft Edge', 'https://github.com/synthetic/example', 15 + seed % 25),
                ('ChatGPT', None, 10 + seed % 30),
                ('Orca', None, 25 + seed % 35),
                ('Microsoft Edge', 'https://arxiv.org/abs/synthetic', 30 + seed % 35),
                ('Terminal', None, 20 + seed % 40),
            ]
            for index, (app, url, minutes) in enumerate(tasks):
                seconds = minutes * 60
                # One collection gap makes some otherwise complete days partial.
                if not (seed % 5 == 0 and index == 2):
                    event(buckets[1], cursor, seconds, {'status': 'not-afk'})
                    event(buckets[0], cursor, seconds, {'app': app, 'title': 'Synthetic example'})
                    if url:
                        event(buckets[2], cursor, seconds, {'url': url, 'title': 'Synthetic example', 'incognito': False})
                cursor += timedelta(seconds=seconds)
                event(buckets[1], cursor, 10 * 60, {'status': 'afk'})
                cursor += timedelta(minutes=10)
            event(buckets[1], cursor, (midnight + timedelta(days=1) - cursor).total_seconds(), {'status': 'afk'})
        day += timedelta(days=1)
    return buckets
