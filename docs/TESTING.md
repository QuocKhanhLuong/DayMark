# Verification — 2026-10-16

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
node --test tests/ui.test.mjs
cd cloud
npm test
npm run typecheck
NEXT_TELEMETRY_DISABLED=1 npm run build -- --webpack
```

Latest baselines: **68 Python, 11 local JavaScript UI, and 18 cloud tests passed**. Typecheck and the production build passed. All activity and identity fixtures in tests are synthetic; none are imported into the live collector or database.

Tests cover UTC+7 day/year/leap boundaries, current-time clipping, idle exclusion, overlap and duplicate/conflicting watchers, browser identity, category precedence, missing/zero/future states, cross-year weeks, device isolation, malformed events, source-switch races, localhost Host/Origin restrictions, and aggregate-only export. Cloud tests cover actual in-memory Better Auth sessions, disabled signup, owner authorization, write-only token scope, strict payload bounds, cross-site denial, redacted failures, and password input retry/cancellation.

Local browser smoke checks verified the explicit no-data view and labeled synthetic demo, heatmap, category filters, and responsive layout. HTTP checks verified local HTML, JavaScript, live and demo endpoints. Later checks confirmed fresh real window/AFK observations; browser extension collection remains unverified because native browser-control tooling became unavailable.

Hosted owner login/logout/session and real aggregate sync remain deployment acceptance steps. Do not infer those from unit tests or a successful build.
