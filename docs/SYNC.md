# Daily use and manual sync

Keep ActivityWatch running while you want activity recorded. Window and idle watchers plus the Edge extension collect on the Mac; Daymark calculates UTC+7 daily totals from those records whenever opened. There is no midnight job to wait for. Missing coverage stays unknown, and partial totals remain lower bounds.

For the local heatmap, open `launch.command` and visit http://127.0.0.1:8766. This view reads the Mac's collector and needs no cloud credential. It includes the detailed daily timeline.

For the private online dashboard:

1. At the end of your day, open `sync-now.command` yourself from this checkout.
2. Review the fixed destination and count of elapsed/observed dates. The command refuses an offline/demo source and a snapshot with no observed days.
3. Type **SYNC** to send; any other input cancels before reading the private token. You never need to paste the token into a command, chat, or browser field.
4. Wait for **Synced … dates. Server receipt: …**. The command does not automatically retry. Refresh https://daymark-private.vercel.app to see the latest heatmap and period totals.

Only dates, missing/partial/complete coverage status, and six category durations are uploaded. Missing days keep null seconds. The count of uploaded dates includes elapsed dates with no observations; it is not a count of days spent working. Foreground windows and matching browser metadata are classified once, after idle exclusion. URLs, titles, paths, device IDs, exact event timestamps, and detailed intervals stay local.

The command reads the existing write-only token from ignored local setup storage only after the owner confirms. The token goes in the HTTPS authorization header to the fixed approved Daymark origin; it is never included in the aggregate body or output. Signing secrets, database credentials, and the login password are not used or transmitted by sync. The agent must not execute this authenticated user command with live credentials.

`.runtime/sync-receipt.json` contains only origin, accepted-date count, last-sync time, observed-day count, and confirmed status (mode 0600). `.runtime/sync-attempt.json` records a redacted pending/confirmed/uncertain attempt. No activity payload is saved by the sync helper. An unconfirmed outcome may mean the server accepted the upload but the response was lost: check the dashboard's Last sync before trying again.

The hosted dashboard has daily category drilldown, filters, day/week/month/year totals, and a yearly heatmap. Detailed event timelines remain local. Website categories begin when the browser extension starts producing reliable data; installing it cannot reconstruct older browsing history.

Sync is manual. No automatic upload, launch-at-login item, or scheduled service was enabled. ActivityWatch must be started manually after a Mac restart unless the owner separately approves persistence. Orca background execution duration remains unsupported and is never added to human foreground time.
