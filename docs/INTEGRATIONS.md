# Collection and integration notes

Verified 16 October 2026. This dashboard reads ActivityWatch on this Mac. It does not upload activity, query GitHub/ChatGPT accounts, or inspect Orca conversations. Synthetic fixtures are examples only.

## What the numbers mean

The main total is observed human foreground time: an active window intersected with a non-idle interval. Editor and terminal activity belongs to coding; recognized GitHub, ChatGPT, Orca, paper and news activity has its own category. Browser details refine the matching foreground browser, rather than adding a second independent duration. An open app, browser tab, terminal process, or running agent is not evidence that a human is using it.

Coverage gaps remain unknown. A successful connection with no recorded intervals does not prove a zero-activity day. Likewise, no browser extension data does not prove that no reading or ChatGPT use occurred. A category can have an observed zero only within recorded coverage; time outside that coverage is still unknown. Long passive reading can become idle under the collector's timeout. These estimates cannot establish attention or productivity.

## ActivityWatch sources and API

The standard collectors are `aw-watcher-window` (foreground app and window metadata) and `aw-watcher-afk` (idle status). The optional official `aw-watcher-web` supplies the active tab URL, title and related tab state; it supports Edge through the Chrome Web Store. Editor plugins are optional and can expose paths and project names, so they are not necessary for basic editor/terminal totals. See the [official watcher documentation](https://docs.activitywatch.net/en/latest/watchers.html).

API reads target loopback, normally `http://127.0.0.1:5600`:

| Read | Purpose |
|---|---|
| `GET /api/0/info` | Server identity and hostname |
| `GET /api/0/buckets/` | Available bucket metadata |
| `GET /api/0/buckets/{id}/events?start=...&end=...&limit=-1` | Events in a bounded time range |

The examined Python REST implementation accepts `start`, `end`, and `limit`; it has no event offset/cursor parameter. Omitting `limit` means unlimited (`-1`). This is an API detail, not a reason to fetch all historical private data. Use bounded dates and the needed watcher types. See [official REST source](https://github.com/ActivityWatch/aw-server/blob/master/aw_server/rest.py).

The examined Peewee storage returns newest-first events, including events that intersect a requested boundary, and trims their timestamp/duration to that range. Boundary-touching events can have zero duration. Consequently, an event spanning adjacent queries may return the same ID with different clipped pieces: deduplication by ID alone can discard valid time. Clip again to the dashboard's half-open range and union intervals. The storage also uses a 24-hour lookback optimization, so extraordinarily long events require separate verification and must not be assumed complete. These details are from [official datastore source](https://github.com/ActivityWatch/aw-core/blob/master/aw_datastore/storages/peewee.py); other backend/version behavior should be tested before relying on it.

Use bucket `type` and `hostname` metadata to select compatible sources. A web bucket normally has ID `aw-watcher-web-{browser}_{hostname}`, but the hostname suffix may be absent. The web watcher can store hostname `unknown` when detection fails; do not silently pair an unknown host to imported data from another computer. See [official web client source](https://github.com/ActivityWatch/aw-watcher-web/blob/master/src/background/client.ts).

The examined browser detector has a Chrome user-agent branch and no separate Edge branch. Edge can therefore appear as `chrome`; a stored browser name may also override detection. Foreground matching must account for that ambiguity rather than assuming every `chrome` bucket came from Google Chrome. See [official browser detection source](https://github.com/ActivityWatch/aw-watcher-web/blob/master/src/background/helpers.ts).

## macOS setup permissions

Installing ActivityWatch and granting tracking access are separate steps. Before enabling either permission or login persistence, explain the specific scope and obtain the user's approval:

1. **Accessibility for `aw-watcher-window`:** allows the watcher to read the active window's title, which may contain document names or other private text. Grant only the ActivityWatch watcher entry through the macOS dialog/System Settings. Never bypass the dialog.
2. **Browser extension permissions:** allow the official watcher to observe active-tab metadata, including URLs and titles, and send it to the local ActivityWatch server. Review the extension's actual permission prompt before approval. Do not enable private/incognito tracking without a separate explicit request.
3. **Launch at login:** makes future collection automatic whenever the user signs in. This is a separate ongoing behavior and is not enabled merely by installing the app.

ActivityWatch's standard watchers do not require Screen Recording or Full Disk Access. The optional Screen Time importer is separate and is not part of this setup. The standard idle timeout is three minutes; change it only deliberately, because it changes the meaning of passive reading time. See the [official permission and idle FAQ](https://docs.activitywatch.net/en/latest/faq.html).

No permission, extension installation, tracker startup, or login-item change was performed by this integration review. The project's setup record describes what was actually installed or started by the implementation task.

## Orca: foreground supported; background duration unsupported

Local installation inspected: `/Applications/Orca.app`, version **1.4.224**. Inspection was limited to app version metadata, CLI help/schema, and bundled public skill guides. No sessions, terminal output, user run records, accounts, projects, or private logs were read.

Public commands exist for `orchestration run-list`, `orchestration run-show`, `orchestration worker-show`, `orchestration worker-list`, and `automations runs`. Their presence is not a complete execution-time contract. The bundled orchestration guide defines a Run as a durable namespace/inbox and a Dispatch as a task attempt. It separates task status, terminal ownership, and agent liveness: a completed task can retain a terminal, a live terminal can contain a stopped/stuck agent, and an unverifiable observation does not prove exit. The automation guide concerns scheduled prompts, not all interactive agent work.

No verified, general start/end event source for all Orca background work was established within this narrow inspection. The dashboard therefore reports **unsupported**, not `0`, for background run duration. Orca foreground intervals can still count in the ordinary human total after ActivityWatch collection is enabled.

A future integration must establish documented start/end timestamps, stable run IDs, run scope, interruptions, missing endings, and overlap semantics. Its background metric must remain separate from human foreground totals and the human-activity heatmap. App uptime, session creation/update times, terminal lifetime, and namespace lifetime are not acceptable substitutes.

Reproduce the public inspection without reading user data:

```sh
/Applications/Orca.app/Contents/Resources/bin/orca agent-context --json
/Applications/Orca.app/Contents/Resources/bin/orca orchestration run-show --help
/Applications/Orca.app/Contents/Resources/bin/orca automations --help
/Applications/Orca.app/Contents/Resources/bin/orca skills get orchestration
/Applications/Orca.app/Contents/Resources/bin/orca skills get orca-cli --reference automations
```
