# Local dashboard contract
Python stdlib app, root `server.py`; module `activity_dashboard/aggregate.py`.
`aggregate(buckets: list[dict], year: int, selected_date: str, now: datetime | None = None, rules: dict | None = None) -> dict` expects buckets containing `id`, `type`, `hostname`, `events` (ActivityWatch event data). Caller selects one device before aggregation.
Returns `timezone` (`Asia/Ho_Chi_Minh`), `year`, `today`, `selectedDate`, `categories` (list of {id,label,color}), `days` (all dates in year), `selected` (matching day plus `segments`).
Day: `date`, `status` (`missing`, `partial`, `complete`, `future`), `totalSeconds` (number or null), `categories` (category id -> seconds), `observedSeconds`, `idleSeconds`, `unknownSeconds`, `elapsedSeconds`.
Segments: `start`, `end` (ISO timestamps), `category`, `seconds`; only counted foreground active intervals. No URLs/titles returned.
Unknown: unobserved elapsed wall time. Zero only where observation exists. If there is no verifiable active/window intersection and no AFK idle evidence, totalSeconds null. Any gaps mean partial; complete only entire elapsed day observed.
Categories: coding, github, chatgpt, orca, reading, other. Browser metadata refines foreground browser only, with browser identity match. AFK required; idle excludes all time. Window is foreground anchor; never sum editor/browser watchers independently.
GET `/api/dashboard?year=2026&date=2026-10-16&source=live|demo&device=...` returns above + `source` + `status`.
`status`: {backend: 'connected'|'unavailable'|'unconfigured'|'error'|'demo', message, devices:[{id,label}], selectedDevice, watchers:[{kind,status,message}], orcaBackground:{status:'unsupported',message}, warnings:[]}.
Default source live; demo explicit only, synthetic unmistakably labeled. Frontend computes filtered week/month/year sums from days; missing -> unknown, partial sum -> observed qualifier; week Monday-Sunday. API may add `weekDays` for cross-year weekly totals.
