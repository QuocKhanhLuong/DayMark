# Private online dashboard status — 2026-10-16

The production app is **Ready** at https://daymark-private.vercel.app. The owner confirmed successful login and visible real activity after a manual aggregate sync. Local window, idle, and Edge browser watchers all have recent observations.

## Completed

- Next.js app, Better Auth owner sessions, strict aggregate API, yearly heatmap, category filters, daily drilldown, day/week/month/year totals, missing/partial states, and manual Mac sync implemented.
- Dedicated free Neon database in Singapore, with pinned authentication and aggregate schemas. No purchase or paid feature was enabled.
- The owner entered and confirmed their own password in the local enrollment script. No password was available to the agent or saved in a local file.
- The owner entered five Production-only Secret settings directly in the dedicated Vercel project and redeployed. Tool verification read names/targets only; secret values were not retrieved. The earlier attempted agent credential transfer was rejected and never retried. Its ordinary consent question was superseded by [owner-controlled handoff](VERCEL-HANDOFF.md).
- Vercel CLI login completed through the user's approved official flow. The dedicated project uses the user-provided GitHub repository, `main`, `cloud` root, Node.js 24, and reviewed build/install commands. Production functions run in Singapore.
- Configured deployment smoke passed: root redirects to login (307), login renders (200), unauthenticated activity/sync deny (401), session returns null/no-store (200), public signup is unavailable (404), and cross-site activity requests deny (403).
- The owner ran `sync-now.command` and explicitly submitted SYNC. A server-generated success receipt was verified in ignored local storage; the owner confirmed the web shows the uploaded data after refresh. No synthetic activity was inserted in the live database.
- The owner installed the official Edge extension. The unique same-device Chrome-labeled bucket was verified against foreground Edge and mapped locally by exact ID. The unknown startup placeholder remains excluded. Before/after comparison preserved all daily foreground totals.

## Data and operation boundaries

Raw ActivityWatch events stay on the Mac. Cloud activity storage accepts only daily dates, coverage status, and six category duration totals. Every activity read checks the exact owner session. Sync uses a separate write-only token and cannot read activity. No public registration or sharing is enabled. Unknown days are never filled with zeros.

Keep ActivityWatch running during use. Open `launch.command` for the local dashboard; open `sync-now.command` yourself and type SYNC when you want to update the web. See [daily usage](SYNC.md). No login auto-start or scheduled upload is enabled. Orca background duration remains unsupported; foreground Orca use is categorized normally.

## Verification

- **80 Python, 11 local UI, and 18 cloud tests passed**. Typecheck and production build passed. Test activity, identities, tokens, and setup files are synthetic and never imported into production.
- Source audit checks all candidate/staged files against private setup values, forbidden generated/private paths, credential patterns, database URIs, private keys, and personal account paths/emails. Real credentials, owner IDs/emails, device/bucket IDs, event records, receipts, and runtime logs remain ignored local data.
- Successful hosted login, refresh with real data, manual sync receipt, and recent live browser collection are verified. The owner also confirmed Sign out, refresh returning to login, and successful login again with data preserved. Synthetic auth tests independently verify session revocation.

Provider resource IDs and personal operational details belong in ignored local runtime storage, not in this public source record.
