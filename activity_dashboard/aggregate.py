"""Conservative ActivityWatch aggregation. No raw titles or URLs leave this module.

The caller must supply buckets from one device, including events overlapping the
requested dates. Intervals are half-open. A sweep line unions idle evidence and
chooses one foreground window, so duplicate watchers cannot inflate totals.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, time, timedelta, timezone
import heapq
import math
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Ho_Chi_Minh"
TZ = ZoneInfo(TIMEZONE)
CATEGORIES = [
    {"id": "coding", "label": "Coding", "color": "#6478ef"},
    {"id": "github", "label": "GitHub", "color": "#aa81df"},
    {"id": "chatgpt", "label": "ChatGPT", "color": "#35a78c"},
    {"id": "orca", "label": "Orca", "color": "#e6a452"},
    {"id": "reading", "label": "Reading", "color": "#52a9ce"},
    {"id": "other", "label": "Other", "color": "#969ba8"},
]
CATEGORY_IDS = tuple(category["id"] for category in CATEGORIES)

DEFAULT_APP_CATEGORIES = {
    **dict.fromkeys([
        "code", "visual studio code", "code - insiders", "cursor", "zed",
        "xcode", "intellij idea", "pycharm", "webstorm", "sublime text",
        "neovim", "vim", "emacs", "terminal", "iterm2", "iterm", "warp",
        "alacritty", "kitty", "ghostty", "wezterm", "codex",
    ], "coding"),
    "chatgpt": "chatgpt", "orca": "orca", "github desktop": "github",
    **dict.fromkeys(["preview", "skim", "zotero", "adobe acrobat", "books"], "reading"),
}
DEFAULT_BROWSER_APPS = {
    "google chrome": "chrome", "google chrome canary": "chrome",
    "microsoft edge": "edge", "microsoft edge beta": "edge",
    "firefox": "firefox", "firefox developer edition": "firefox",
    "safari": "safari", "safari technology preview": "safari",
    "brave browser": "brave", "chromium": "chromium", "arc": "arc",
    "vivaldi": "vivaldi", "opera": "opera",
}
DEFAULT_DOMAIN_CATEGORIES = {
    "github.com": "github", "gist.github.com": "github",
    "chatgpt.com": "chatgpt", "chat.openai.com": "chatgpt",
    **dict.fromkeys([
        "arxiv.org", "biorxiv.org", "medrxiv.org", "openreview.net",
        "semanticscholar.org", "scholar.google.com", "nature.com", "science.org",
        "sciencedirect.com", "acm.org", "ieee.org", "pubmed.ncbi.nlm.nih.gov",
        "news.ycombinator.com", "bbc.com", "bbc.co.uk", "reuters.com",
        "apnews.com", "nytimes.com", "theguardian.com", "economist.com",
        "vnexpress.net", "tuoitre.vn", "thanhnien.vn", "substack.com", "medium.com",
    ], "reading"),
}


def _mapping(rules: dict, name: str) -> dict:
    value = rules.get(name, {})
    return value if isinstance(value, dict) else {}


def _app_name(value: str) -> str:
    name = value.strip().casefold()
    return name[:-4] if name.endswith(".app") else name


def _rules(rules: dict | None) -> tuple[dict, dict, dict, dict]:
    rules = rules if isinstance(rules, dict) else {}
    apps, domains, browsers = (DEFAULT_APP_CATEGORIES.copy(),
                               DEFAULT_DOMAIN_CATEGORIES.copy(),
                               DEFAULT_BROWSER_APPS.copy())
    for key, value in _mapping(rules, "app_categories").items():
        if isinstance(key, str) and value in CATEGORY_IDS:
            apps[_app_name(key)] = value
    for key, value in _mapping(rules, "domain_categories").items():
        if isinstance(key, str) and value in CATEGORY_IDS and key.strip(" ."):
            domains[key.strip(" .").casefold()] = value
    for key, value in _mapping(rules, "browser_apps").items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            browsers[_app_name(key)] = value.strip().casefold()
    bucket_map = {
        key: value.strip().casefold()
        for key, value in _mapping(rules, "browser_bucket_map").items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }
    return apps, domains, browsers, bucket_map


def _web_category(url: object, domains: dict) -> str:
    if not isinstance(url, str):
        return "other"
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return "other"
    if parsed.scheme not in ("http", "https", "file"):
        return "other"
    # Most specific matching host wins; deceptive suffixes do not match.
    labels = host.split(".")
    for offset in range(len(labels)):
        suffix = ".".join(labels[offset:])
        if suffix in domains:
            return domains[suffix]
    if parsed.path.casefold().endswith(".pdf"):
        return "reading"
    return "other"


def _kind(bucket: dict) -> str | None:
    bucket_type = bucket.get("type")
    bucket_id = bucket.get("id", "")
    if not isinstance(bucket_id, str):
        bucket_id = ""
    if bucket_type == "afkstatus" or bucket_id.startswith("aw-watcher-afk_"):
        return "afk"
    if bucket_type == "currentwindow" or bucket_id.startswith("aw-watcher-window_"):
        return "window"
    if bucket_type == "web.tab.current" or bucket_id.startswith("aw-watcher-web-"):
        return "browser"
    return None  # Editor and background job watchers never add foreground time.


def _browser_id(bucket: dict, bucket_map: dict, browsers: dict) -> str | None:
    bucket_id = bucket.get("id", "")
    if not isinstance(bucket_id, str):
        return None
    if bucket_id in bucket_map:
        return bucket_map[bucket_id]
    # Identity comes from an explicit watcher bucket, never from a page title.
    prefix = "aw-watcher-web-"
    if bucket_id.startswith(prefix):
        name = bucket_id[len(prefix):].split("_", 1)[0].casefold()
        if name in set(browsers.values()):
            return name
    return None


def _timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def _number(value: float) -> float | int:
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def aggregate(buckets: list[dict], year: int, selected_date: str,
              now: datetime | None = None, rules: dict | None = None) -> dict:
    """Aggregate one device's AW buckets into local dates and counted intervals.

    Optional rule maps: app_categories, domain_categories, browser_apps, and
    browser_bucket_map. Rules extend/override defaults. Browser bucket overrides
    are necessary when an Edge extension identifies itself as Chrome.
    """
    if isinstance(year, bool) or not isinstance(year, int) or not 1970 <= year <= 9998:
        raise ValueError("year must be an integer between 1970 and 9998")
    try:
        selected_day = date.fromisoformat(selected_date)
    except (TypeError, ValueError):
        raise ValueError("selected_date must use YYYY-MM-DD") from None
    if selected_day.isoformat() != selected_date or not 1970 <= selected_day.year <= 9998:
        raise ValueError("selected_date must use YYYY-MM-DD within 1970–9998")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_ts = now.timestamp()
    today = now.astimezone(TZ).date()
    year_start, year_end = date(year, 1, 1), date(year + 1, 1, 1)
    year_dates = [year_start + timedelta(days=n) for n in range((year_end - year_start).days)]
    monday = selected_day - timedelta(days=selected_day.weekday())
    week_dates = [monday + timedelta(days=n) for n in range(7)]
    required_dates = sorted(set(year_dates + week_dates + [selected_day]))
    starts = [datetime.combine(day, time.min, TZ).timestamp() for day in required_dates]
    ends = [datetime.combine(day + timedelta(days=1), time.min, TZ).timestamp()
            for day in required_dates]
    daily = {day.isoformat(): {
        "date": day.isoformat(), "status": "missing", "totalSeconds": None,
        "categories": dict.fromkeys(CATEGORY_IDS, 0.0), "observedSeconds": 0.0,
        "idleSeconds": 0.0, "unknownSeconds": 0.0,
        "elapsedSeconds": max(0.0, min(end, now_ts) - start),
    } for day, start, end in zip(required_dates, starts, ends)}
    segments: list[dict] = []
    selected_key = selected_day.isoformat()
    apps, domains, browser_apps, bucket_map = _rules(rules)
    range_start, range_end = starts[0], min(ends[-1], now_ts)

    # Each record is compact metadata only. Raw event values are not retained.
    records: list[tuple] = []
    edges: list[tuple] = []
    for bucket in buckets if isinstance(buckets, list) else []:
        if not isinstance(bucket, dict):
            continue
        kind = _kind(bucket)
        if kind is None or not isinstance(bucket.get("events"), list):
            continue
        browser = _browser_id(bucket, bucket_map, browser_apps) if kind == "browser" else None
        if kind == "browser" and browser is None:
            continue
        bucket_id = bucket.get("id", "")
        bucket_id = bucket_id if isinstance(bucket_id, str) else ""
        for event in bucket["events"]:
            if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
                continue
            start = _timestamp(event.get("timestamp"))
            duration = event.get("duration")
            if (start is None or isinstance(duration, bool)
                    or not isinstance(duration, (int, float))):
                continue
            try:
                duration = float(duration)
            except (ValueError, OverflowError):
                continue
            if not math.isfinite(duration) or duration <= 0:
                continue
            end = start + duration
            if not math.isfinite(end):
                continue
            clipped_start, clipped_end = max(start, range_start), min(end, range_end)
            if clipped_end <= clipped_start:
                continue
            data = event["data"]
            category, identity = None, browser
            if kind == "afk":
                if data.get("status") not in ("afk", "not-afk"):
                    continue
                identity = data["status"]
            elif kind == "window":
                if not isinstance(data.get("app"), str) or not data["app"].strip():
                    continue
                app = _app_name(data["app"])
                category = apps.get(app, "other")
                identity = browser_apps.get(app)
            else:
                if data.get("focused") is False or data.get("active") is False:
                    continue
                category = _web_category(data.get("url"), domains)
            uid = len(records)
            # Later original event wins on overlap; ties are input-order invariant.
            priority = (-start, -end, bucket_id, category or "", identity or "", uid)
            records.append((kind, identity, category, priority))
            edges.append((clipped_start, 1, uid))
            edges.append((clipped_end, 0, uid))

    def add_interval(start: float, end: float, category: str | None) -> None:
        """Attribute a disjoint observed interval to only the requested days."""
        index = max(0, bisect_right(starts, start) - 1)
        while index < len(starts) and starts[index] < end:
            left, right = max(start, starts[index]), min(end, ends[index])
            seconds = right - left
            if seconds > 0:
                key = required_dates[index].isoformat()
                day = daily[key]
                day["observedSeconds"] += seconds
                if category is None:
                    day["idleSeconds"] += seconds
                else:
                    day["categories"][category] += seconds
                    if key == selected_key:
                        start_iso = datetime.fromtimestamp(left, TZ).isoformat()
                        end_iso = datetime.fromtimestamp(right, TZ).isoformat()
                        if (segments and segments[-1]["end"] == start_iso
                                and segments[-1]["category"] == category):
                            segments[-1]["end"] = end_iso
                            segments[-1]["seconds"] += seconds
                        else:
                            segments.append({"start": start_iso, "end": end_iso,
                                             "category": category, "seconds": seconds})
            index += 1

    active: set[int] = set()
    windows: list[tuple] = []
    browser_heaps: dict[str, list] = {}
    afk_counts = {"afk": 0, "not-afk": 0}

    def current(heap: list) -> tuple | None:
        while heap and heap[0][-1] not in active:
            heapq.heappop(heap)
        return records[heap[0][-1]] if heap else None

    edges.sort()
    index = 0
    while index < len(edges):
        left = edges[index][0]
        while index < len(edges) and edges[index][0] == left:
            _, entering, uid = edges[index]
            kind, identity, _, priority = records[uid]
            if entering:
                active.add(uid)
                if kind == "window":
                    heapq.heappush(windows, priority)
                elif kind == "browser":
                    heapq.heappush(browser_heaps.setdefault(identity, []), priority)
            else:
                active.discard(uid)
            if kind == "afk":
                afk_counts[identity] += 1 if entering else -1
            index += 1
        if index == len(edges):
            break
        right = edges[index][0]
        if afk_counts["afk"]:
            add_interval(left, right, None)
        elif afk_counts["not-afk"]:
            window = current(windows)
            if window:
                _, browser, category, _ = window
                # Native app rules win; only an unclassified foreground browser
                # may be refined by its own current-tab watcher.
                if browser and category == "other":
                    tab = current(browser_heaps.get(browser, []))
                    if tab:
                        category = tab[2]
                add_interval(left, right, category)

    for key, day in daily.items():
        observed, elapsed = day["observedSeconds"], day["elapsedSeconds"]
        day["unknownSeconds"] = max(0.0, elapsed - observed)
        if key > today.isoformat():
            day["status"] = "future"
        elif observed > 0:
            day["status"] = "complete" if day["unknownSeconds"] < 0.000001 else "partial"
            day["totalSeconds"] = _number(sum(day["categories"].values()))
        for field in ("observedSeconds", "idleSeconds", "unknownSeconds", "elapsedSeconds"):
            day[field] = _number(day[field])
        day["categories"] = {key: _number(value) for key, value in day["categories"].items()}
    for segment in segments:
        segment["seconds"] = _number(segment["seconds"])
    return {
        "timezone": TIMEZONE, "year": year, "today": today.isoformat(),
        "selectedDate": selected_key, "categories": [category.copy() for category in CATEGORIES],
        "days": [daily[day.isoformat()] for day in year_dates],
        "weekDays": [daily[day.isoformat()] for day in week_dates],
        "selected": {**daily[selected_key], "segments": segments},
    }
