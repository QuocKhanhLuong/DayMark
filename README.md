# Daymark — a local daily activity journal

A small, dependency-free dashboard for coding (editors and terminals), GitHub, ChatGPT, Orca foreground use, and reading. ActivityWatch stores the source events on your Mac; Daymark reads its local API and builds daily logs, weekly/monthly/yearly totals, and an interactive GitHub-style heatmap.

## Open it

Requires Python 3.10+. Double-click `launch.command`, or run from your checkout:

```sh
cd DayMark
python3 server.py
```

Open **http://127.0.0.1:8766**. Keep that terminal open; Ctrl+C stops Daymark. If already running, just open the URL. If another program uses that port, choose `python3 server.py --port 8767` and use the matching URL. The local server binds only to `127.0.0.1` and never uploads activity. The optional private online app is described below.

The default **My activity** view shows real ActivityWatch data only. An unavailable collector produces **No data**, never invented values. Select **Synthetic demo** to inspect the design with clearly marked test fixtures. Demo data is generated in memory and is never imported into ActivityWatch.

## Actual setup on this Mac

See [SETUP-STATUS.md](docs/SETUP-STATUS.md) for verified installation and pending permissions. ActivityWatch 0.14.1 for Apple Silicon is installed at `/Applications/ActivityWatch.app`. Its official installer SHA-256 matched GitHub release metadata. Installing the app does not mean collection is running or approved.

## Finish collection setup after approval

1. Open ActivityWatch from Applications. Approve the normal macOS application launch prompt if presented. Do not disable Gatekeeper or bypass a security warning; resolve any warning with the official installer/vendor instead.
2. ActivityWatch's `aw-watcher-window` needs **Accessibility** to observe the foreground application and window title. Approve only after reviewing this scope in System Settings → Privacy & Security → Accessibility. The bundled idle watcher records active/idle status from time since input. This setup does not require Screen Recording, Full Disk Access, screenshots, or keystroke contents.
3. For reliable website categories in Edge, install the official [ActivityWatch Web Watcher](https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi) from Chrome Web Store in Edge. Its permissions allow access to active-tab URLs/titles and browser activity metadata, stored in local ActivityWatch. Review and approve Edge's exact permission prompt. Keep incognito collection disabled unless separately requested. Do not grant browser tracking merely to preview the dashboard.
4. Visit http://127.0.0.1:5600 and confirm Window and AFK watchers produce records. Then refresh Daymark. Its data cache lasts at most 30 seconds, and the view refreshes periodically while open.
5. **Do not enable launch-at-login without separate approval.** Until then, start ActivityWatch manually when you want collection. Closing Daymark stops only this dashboard; use ActivityWatch's tray menu to stop its watchers or quit it. Revoke Accessibility or disable/remove the Edge extension to stop their respective access.

No historical activity can be recovered from before collection started. Leave ActivityWatch running during the days you want recorded. Daymark does not need to run all day: opening it later recomputes past days from ActivityWatch's persisted database. No midnight cron job is needed.

### Edge identity and device mapping

Some versions of the browser watcher label Edge's bucket as `chrome`. Daymark does not guess, because another browser's background tab could be counted incorrectly. If your browsing remains **Other**, inspect your own bucket IDs in ActivityWatch's local UI, copy `config.example.json` to `config.json`, and add an exact mapping:

```json
{
  "rules": {
    "browser_bucket_map": {
      "aw-watcher-web-chrome_YOUR_ACTUAL_HOSTNAME": "edge"
    }
  }
}
```

Use the actual ID; the example is a placeholder. If a browser bucket has `unknown`/missing hostname, also set `"bucket_devices": {"ACTUAL_BUCKET_ID": "ACTUAL_WINDOW_BUCKET_HOSTNAME"}`. Map only a bucket you have verified belongs to this Mac. Restart Daymark after configuration edits. With more than one device, choose one explicitly; events from different machines are never combined.

## How time is counted

- Days use **Asia/Ho_Chi_Minh (UTC+7)**, including midnight and year boundaries. Weeks run Monday–Sunday. Category filters affect the heatmap, period totals, and daily details.
- A second counts as human foreground time only when a foreground window and an explicit `not-afk` interval overlap. Any overlapping `afk` evidence excludes that second. Browser audio never overrides idle in this dashboard.
- Window activity anchors the timeline. Matching browser metadata refines that foreground interval; duplicate browser/editor/window records do not add independent time. Editor plugins are optional and not required for coding totals.
- Native Orca, ChatGPT, editor/terminal, reader, and GitHub Desktop matches take priority over browser metadata. For browsers, a matching domain determines category; the most specific configured domain wins. A PDF URL counts as reading. Unrecognized apps/sites are **Other**, not silently discarded.
- App categories are estimates: Terminal foreground time means terminal use, not a measurement of individual git commands; Preview may contain non-paper documents. Reading without input can become idle after ActivityWatch's default idle timeout. Review the timeout if this matters; changes affect collection interpretation and should be deliberate.
- **No data** means no usable observation. **0** means observed time with no selected-category activity (including observed idle). **Partial** means some elapsed time was unobserved. Totals for partial days/periods are lower bounds; the uncovered time is shown separately. A powered-off Mac is unknown, not assumed idle. Future time is not zero.
- **Orca background duration is unsupported** until an authoritative general start/end event source is available. App uptime, terminal lifetime, and orchestration namespace lifetime are not agent execution time. Background time is never added to human totals. See [integration findings](docs/INTEGRATIONS.md).

## Customize categories

Optional `config.json` contains `rules.app_categories`, `rules.domain_categories`, `rules.browser_apps`, and `rules.browser_bucket_map`. Maps extend defaults. App names match exactly (case-insensitive, optional `.app` suffix); domains match themselves and subdomains, most specific first. Valid category IDs: `coding`, `github`, `chatgpt`, `orca`, `reading`, `other`. Add the news/paper domains you use without reading browser history. See defaults in `activity_dashboard/aggregate.py`.

## Privacy and storage

Daymark reads only window/AFK/browser buckets for the selected device from the fixed `http://127.0.0.1:5600` endpoint. It rejects redirects and disables proxy use. Raw URLs and window titles are used only in memory to classify events and are not sent to the browser, written to Daymark files, or logged. Responses contain category/time intervals. Host and Origin checks, no CORS, and a local content policy protect the read-only server from cross-site requests.

ActivityWatch itself retains raw app/window/browser metadata locally. Its own UI supports viewing/exporting/deleting data. Keep any backup local unless you explicitly decide otherwise. This app does not read Screen Time, shell history, private Orca session logs, repository contents, accounts, or messages. Demo fixtures are entirely synthetic.

## Tests

```sh
python3 -m unittest discover -s tests -v
node --test tests/ui.test.mjs
```

Fixtures cover UTC+7 midnight/year/leap-day boundaries, ongoing interval clipping, idle exclusion, conflicting/duplicate watchers, matching browser identity, category precedence, missing vs zero vs future UI, cross-year weeks, device isolation, and HTTP protections. No real activity data is used in tests.

## Files

- `server.py`: read-only localhost HTTP service and memory cache.
- `activity_dashboard/activitywatch.py`: narrowly scoped ActivityWatch reader.
- `activity_dashboard/aggregate.py`: interval union and daily categorization.
- `activity_dashboard/demo.py`: synthetic fixtures.
- `activity_dashboard/static/`: standalone HTML/CSS/JS dashboard.
- `tests/`: Python and JavaScript tests.

Official references: [FAQ](https://docs.activitywatch.net/en/latest/faq.html), [watchers](https://docs.activitywatch.net/en/latest/watchers.html), [downloads](https://activitywatch.net/downloads/).

## Private online dashboard

The approved Vercel/Neon extension is in `cloud/`; local ActivityWatch and this localhost dashboard remain available. See [cloud status](docs/CLOUD-STATUS.md) for actual provisioning and required user actions. Hosted login and aggregate sync remain incomplete until verified after owner configuration.

The source build is now Ready at https://daymark-private.vercel.app with a setup-in-progress page. Complete [owner-controlled Vercel configuration](docs/VERCEL-HANDOFF.md) before using hosted login or sync. The agent does not transmit production credentials.
