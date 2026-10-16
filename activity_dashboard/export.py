"""Explicit aggregate-only boundary. Never serialize a raw ActivityWatch event."""
from datetime import date
import math

CATEGORIES = ('coding', 'github', 'chatgpt', 'orca', 'reading', 'other')
TIME_ZONE = 'Asia/Ho_Chi_Minh'


class ExportError(Exception):
    pass


def export_snapshot(snapshot):
    if snapshot.get('source') != 'live' or snapshot.get('status', {}).get('backend') != 'connected':
        raise ExportError('Only a connected live source can be synced; demo and offline snapshots are refused.')
    if snapshot.get('timezone') != TIME_ZONE or not isinstance(snapshot.get('days'), list):
        raise ExportError('Unexpected local aggregate format.')
    result = []
    seen = set()
    for day in snapshot['days']:
        if not isinstance(day, dict):
            raise ExportError('Invalid local day.')
        if day.get('status') == 'future':
            continue
        day_date = day.get('date')
        try:
            parsed = date.fromisoformat(day_date)
            if parsed.isoformat() != day_date or not 2000 <= parsed.year <= 2100:
                raise ValueError()
        except (TypeError, ValueError):
            raise ExportError('Invalid local date.') from None
        if day_date in seen or day_date > snapshot.get('today', ''):
            raise ExportError('Duplicate or future local date.')
        seen.add(day_date)
        status = day.get('status')
        if status == 'missing':
            if day.get('totalSeconds') is not None:
                raise ExportError('Missing day has a numeric total.')
            seconds = None
        elif status in ('partial', 'complete'):
            raw = day.get('categories')
            if not isinstance(raw, dict) or set(raw) != set(CATEGORIES):
                raise ExportError('Unexpected local categories.')
            seconds = {}
            for category in CATEGORIES:
                number = raw[category]
                if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not 0 <= number <= 86400:
                    raise ExportError('Invalid local category duration.')
                seconds[category] = number
            total = sum(seconds.values())
            declared = day.get('totalSeconds')
            if total > 86400 or isinstance(declared, bool) or not isinstance(declared, (int, float)) or not math.isfinite(declared) or abs(total - declared) > 0.00001:
                raise ExportError('Local daily totals are inconsistent.')
        else:
            raise ExportError('Invalid local coverage status.')
        result.append({'date': day_date, 'status': status, 'seconds': seconds})
    if not 1 <= len(result) <= 366:
        raise ExportError('Sync requires 1–366 elapsed dates.')
    return {'schemaVersion': 1, 'timeZone': TIME_ZONE, 'days': result}
