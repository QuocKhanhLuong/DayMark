"""Synthetic fixtures only; these tests never load a user's activity history."""

from datetime import datetime, timedelta, timezone
import json
import random
import unittest

from activity_dashboard.aggregate import aggregate


NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
START = "2026-10-16T10:00:00+07:00"


def event(timestamp=START, duration=60, **data):
    return {"timestamp": timestamp, "duration": duration, "data": data}


def bucket(kind, *events, id=None):
    defaults = {
        "afkstatus": "aw-watcher-afk_synthetic",
        "currentwindow": "aw-watcher-window_synthetic",
        "web.tab.current": "aw-watcher-web-edge_synthetic",
        "app.editor.activity": "aw-watcher-vscode_synthetic",
    }
    return {"id": id or defaults[kind], "type": kind, "hostname": "synthetic", "events": list(events)}


def sample(*extra, duration=60, app="Code", timestamp=START):
    return [
        bucket("afkstatus", event(timestamp, duration, status="not-afk")),
        bucket("currentwindow", event(timestamp, duration, app=app)),
        *extra,
    ]


def run(buckets, selected="2026-10-16", year=2026, now=NOW, **kwargs):
    return aggregate(buckets, year, selected, now=now, **kwargs)


class AggregateTests(unittest.TestCase):
    def test_no_data_is_missing_not_zero(self):
        result = run([])
        day = result["selected"]
        self.assertEqual(result["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(day["status"], "missing")
        self.assertIsNone(day["totalSeconds"])
        self.assertEqual(day["observedSeconds"], 0)
        self.assertEqual(day["unknownSeconds"], 19 * 3600)
        self.assertEqual(day["segments"], [])
        self.assertEqual(len(result["days"]), 365)

    def test_verified_foreground_and_partial_day(self):
        day = run(sample(duration=90))["selected"]
        self.assertEqual(day["status"], "partial")
        self.assertEqual(day["totalSeconds"], 90)
        self.assertEqual(day["categories"]["coding"], 90)
        self.assertEqual(day["unknownSeconds"], 19 * 3600 - 90)

    def test_afk_is_required_and_browser_alone_does_not_count(self):
        for buckets in (
            [bucket("currentwindow", event(app="Code"))],
            [bucket("web.tab.current", event(url="https://github.com", audible=True))],
            [bucket("afkstatus", event(status="not-afk"))],
            [bucket("afkstatus", event(status="not-afk")),
             bucket("web.tab.current", event(url="https://github.com"))],
        ):
            with self.subTest(buckets=buckets):
                self.assertIsNone(run(buckets)["selected"]["totalSeconds"])

    def test_idle_is_observed_zero_without_window(self):
        day = run([bucket("afkstatus", event(status="afk"))])["selected"]
        self.assertEqual(day["totalSeconds"], 0)
        self.assertEqual(day["idleSeconds"], 60)
        self.assertEqual(day["observedSeconds"], 60)
        self.assertEqual(day["status"], "partial")

    def test_idle_dominates_conflicting_active_and_audible_browser(self):
        events = sample(
            bucket("afkstatus", event("2026-10-16T10:00:20+07:00", 20, status="afk"),
                   id="aw-watcher-afk_duplicate"),
            bucket("web.tab.current", event(url="https://github.com", audible=True)),
            app="Microsoft Edge",
        )
        day = run(events)["selected"]
        self.assertEqual(day["totalSeconds"], 40)
        self.assertEqual(day["idleSeconds"], 20)
        self.assertEqual(day["observedSeconds"], 60)
        self.assertEqual(len(day["segments"]), 2)

    def test_duplicates_and_editor_watchers_never_inflate(self):
        original = sample(bucket("web.tab.current", event(url="https://github.com")), app="Microsoft Edge")
        day = run(original + original + [
            bucket("app.editor.activity", event(duration=36000, project="synthetic")),
        ])["selected"]
        self.assertEqual(day["totalSeconds"], 60)
        self.assertEqual(day["observedSeconds"], 60)
        self.assertEqual(day["categories"]["github"], 60)

    def test_latest_window_wins_overlapping_anchor_intervals(self):
        data = sample(duration=100)
        data.append(bucket("currentwindow", event("2026-10-16T10:00:30+07:00", 40, app="ChatGPT"),
                           id="aw-watcher-window_second"))
        day = run(data)["selected"]
        self.assertEqual(day["totalSeconds"], 100)
        self.assertEqual(day["categories"]["coding"], 60)
        self.assertEqual(day["categories"]["chatgpt"], 40)
        self.assertEqual([s["category"] for s in day["segments"]], ["coding", "chatgpt", "coding"])

    def test_overlap_ties_deterministic_under_input_shuffle(self):
        data = sample(duration=100)
        data.extend([
            bucket("currentwindow", event(duration=100, app="ChatGPT"), id="aw-watcher-window_a"),
            bucket("currentwindow", event(duration=100, app="Orca"), id="aw-watcher-window_z"),
        ])
        expected = run(data)["selected"]
        random.Random(42).shuffle(data)
        self.assertEqual(run(data)["selected"], expected)

    def test_browser_only_refines_the_matching_foreground_browser(self):
        tabs = bucket("web.tab.current", event(url="https://github.com"))
        for app, category in (("Google Chrome", "other"), ("Code", "coding"),
                              ("Microsoft Edge", "github")):
            with self.subTest(app=app):
                day = run(sample(tabs, app=app))["selected"]
                self.assertEqual(day["categories"][category], 60)

    def test_unfocused_or_inactive_browser_metadata_is_ignored(self):
        for flag in ("focused", "active"):
            data = sample(bucket("web.tab.current", event(url="https://github.com", **{flag: False})),
                          app="Microsoft Edge")
            self.assertEqual(run(data)["selected"]["categories"]["other"], 60)

    def test_explicit_edge_bucket_mapping(self):
        data = sample(bucket("web.tab.current", event(url="https://github.com"),
                             id="aw-watcher-web-chrome_synthetic"), app="Microsoft Edge")
        self.assertEqual(run(data)["selected"]["categories"]["other"], 60)
        mapped = run(data, rules={"browser_bucket_map": {"aw-watcher-web-chrome_synthetic": "edge"}})
        self.assertEqual(mapped["selected"]["categories"]["github"], 60)

    def test_category_domain_precedence_and_safe_hostname_matching(self):
        examples = {
            "https://github.com/team/report.pdf": "github",
            "https://chatgpt.com/c/synthetic": "chatgpt",
            "https://arxiv.org/abs/2601.00000": "reading",
            "https://news.ycombinator.com/": "reading",
            "https://vnexpress.net/example": "reading",
            "https://example.org/paper.PDF?download=1": "reading",
            "https://github.com.evil.example/": "other",
            "https://github.com@evil.example/": "other",
            "https://api.github.com/repos/": "github",
            "https://EXAMPLE.org/": "other",
            "javascript:github.com": "other",
            "https://[bad": "other",
        }
        for url, expected in examples.items():
            with self.subTest(url=url):
                data = sample(bucket("web.tab.current", event(url=url)), app="Microsoft Edge")
                self.assertEqual(run(data)["selected"]["categories"][expected], 60)

    def test_native_app_category_precedence_over_titles_and_browser_tabs(self):
        for app, category in (("Orca", "orca"), ("ChatGPT", "chatgpt"),
                              ("Terminal", "coding"), ("Preview", "reading")):
            with self.subTest(app=app):
                data = sample(bucket("web.tab.current", event(url="https://github.com")), app=app)
                data[1]["events"][0]["data"]["title"] = "ChatGPT GitHub paper Orca"
                self.assertEqual(run(data)["selected"]["categories"][category], 60)

    def test_custom_rules_longest_domain_and_native_overrides(self):
        data = sample(bucket("web.tab.current", event(url="https://papers.example.org/")),
                      app="Microsoft Edge")
        rules = {"domain_categories": {"example.org": "other", "papers.example.org": "reading"}}
        self.assertEqual(run(data, rules=rules)["selected"]["categories"]["reading"], 60)
        rules["app_categories"] = {"Microsoft Edge": "orca"}
        self.assertEqual(run(data, rules=rules)["selected"]["categories"]["orca"], 60)

    def test_vietnam_midnight_splits_utc_event(self):
        data = sample(timestamp="2026-10-15T16:59:30Z", duration=90)
        result = run(data)
        days = {day["date"]: day for day in result["days"]}
        self.assertEqual(days["2026-10-15"]["totalSeconds"], 30)
        self.assertEqual(days["2026-10-16"]["totalSeconds"], 60)
        self.assertEqual(result["selected"]["segments"][0]["start"], "2026-10-16T00:00:00+07:00")

    def test_year_boundary_and_cross_year_week(self):
        data = sample(timestamp="2025-12-31T16:59:30Z", duration=90)
        result = run(data, selected="2026-01-01")
        self.assertEqual(result["days"][0]["totalSeconds"], 60)
        self.assertEqual([day["date"] for day in result["weekDays"]], [
            "2025-12-29", "2025-12-30", "2025-12-31", "2026-01-01",
            "2026-01-02", "2026-01-03", "2026-01-04",
        ])
        self.assertEqual(result["weekDays"][2]["totalSeconds"], 30)

    def test_leap_day_is_included(self):
        result = run(sample(timestamp="2024-02-29T00:00:00+07:00"),
                     selected="2024-02-29", year=2024)
        self.assertEqual(len(result["days"]), 366)
        self.assertEqual(result["selected"]["totalSeconds"], 60)

    def test_current_intervals_clip_to_now_and_future_stays_unknown(self):
        data = sample(timestamp="2026-10-16T18:59:30+07:00", duration=3600)
        result = run(data)
        self.assertEqual(result["selected"]["totalSeconds"], 30)
        self.assertEqual(result["selected"]["segments"][0]["end"], "2026-10-16T19:00:00+07:00")
        tomorrow = next(day for day in result["days"] if day["date"] == "2026-10-17")
        self.assertEqual(tomorrow["status"], "future")
        self.assertIsNone(tomorrow["totalSeconds"])
        self.assertEqual(tomorrow["elapsedSeconds"], 0)
        self.assertEqual(tomorrow["unknownSeconds"], 0)

    def test_today_uses_vietnam_date_not_utc_date(self):
        result = run([], now=datetime(2026, 10, 16, 18, 30, tzinfo=timezone.utc))
        self.assertEqual(result["today"], "2026-10-17")

    def test_complete_elapsed_day_can_be_zero(self):
        result = run([bucket("afkstatus", event("2026-10-15T00:00:00+07:00", 86400, status="afk"))],
                     selected="2026-10-15")
        self.assertEqual(result["selected"]["status"], "complete")
        self.assertEqual(result["selected"]["totalSeconds"], 0)
        self.assertEqual(result["selected"]["unknownSeconds"], 0)

    def test_contiguous_intervals_merge_and_half_open_edges_do_not_overlap(self):
        data = sample(duration=120)
        data[1]["events"] = [event(duration=60, app="Code"),
                             event("2026-10-16T10:01:00+07:00", 60, app="Terminal")]
        day = run(data)["selected"]
        self.assertEqual(day["totalSeconds"], 120)
        self.assertEqual(len(day["segments"]), 1)
        self.assertEqual(day["segments"][0]["seconds"], 120)

    def test_gaps_are_unknown_not_idle(self):
        data = sample(duration=120)
        data[1]["events"] = [event(duration=30, app="Code"),
                             event("2026-10-16T10:01:30+07:00", 30, app="Code")]
        day = run(data)["selected"]
        self.assertEqual(day["totalSeconds"], 60)
        self.assertEqual(day["idleSeconds"], 0)
        self.assertEqual(day["observedSeconds"], 60)
        self.assertEqual(len(day["segments"]), 2)

    def test_invalid_events_are_ignored_without_crashing(self):
        invalid = [None, [], "bad", {},
                   event(timestamp="bad", app="Code"),
                   event(timestamp="2026-10-16T10:00:00", app="Code"),
                   event(duration=-1, app="Code"), event(duration=0, app="Code"),
                   event(duration=float("nan"), app="Code"),
                   event(duration=float("inf"), app="Code"),
                   event(duration=True, app="Code"), event(duration="60", app="Code"),
                   event(duration=10**1000, app="Code"),
                   {"timestamp": START, "duration": 60, "data": None}, event(app="")]
        data = sample()
        data[1]["events"].extend(invalid)
        data.extend([None, [], {"type": "currentwindow", "events": "bad"},
                     bucket("afkstatus", event(status="unknown"))])
        self.assertEqual(run(data)["selected"]["totalSeconds"], 60)

    def test_fractional_seconds_preserved(self):
        day = run(sample(timestamp="2026-10-16T10:00:00.125+07:00", duration=0.5))["selected"]
        self.assertEqual(day["totalSeconds"], 0.5)
        self.assertEqual(day["segments"][0]["seconds"], 0.5)

    def test_privacy_output_has_no_raw_titles_urls_or_bucket_ids(self):
        data = sample(bucket("web.tab.current", event(url="https://github.com/secret-private-repo",
                                                      title="Private secret title")), app="Microsoft Edge")
        data[1]["events"][0]["data"]["title"] = "Private secret window title"
        serialized = json.dumps(run(data))
        for private in ("secret", "https://", "aw-watcher", "title", "url", "hostname"):
            self.assertNotIn(private, serialized)

    def test_total_never_exceeds_observed_and_daily_conservation(self):
        rng = random.Random(94)
        origin = datetime.fromisoformat(START)
        data = []
        for kind in ("afkstatus", "currentwindow", "web.tab.current"):
            events = []
            for _ in range(200):
                start = (origin + timedelta(seconds=rng.randrange(3600))).isoformat()
                details = ({"status": rng.choice(["afk", "not-afk"])} if kind == "afkstatus"
                           else {"app": rng.choice(["Code", "Microsoft Edge", "ChatGPT"])}
                           if kind == "currentwindow" else {"url": "https://github.com"})
                events.append(event(start, rng.randrange(1, 240), **details))
            data.append(bucket(kind, *events))
        day = run(data)["selected"]
        self.assertLessEqual(day["totalSeconds"], day["observedSeconds"])
        self.assertEqual(day["totalSeconds"] + day["idleSeconds"], day["observedSeconds"])
        self.assertEqual(day["observedSeconds"] + day["unknownSeconds"], day["elapsedSeconds"])
        self.assertEqual(sum(s["seconds"] for s in day["segments"]), day["totalSeconds"])
        self.assertTrue(all(a["end"] <= b["start"] for a, b in zip(day["segments"], day["segments"][1:])))

    def test_invalid_request_arguments_rejected(self):
        for year in (True, "2026", 0, 9999):
            with self.subTest(year=year), self.assertRaises(ValueError):
                run([], year=year)
        for selected in ("invalid", "20261016", "2026-10-32", None):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                run([], selected=selected)
        with self.assertRaises(ValueError):
            run([], now=datetime(2026, 10, 16))


if __name__ == "__main__":
    unittest.main()
