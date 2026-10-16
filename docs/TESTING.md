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

Latest baselines: **80 Python, 11 local JavaScript UI, and 18 cloud tests passed**. Typecheck and the production build passed. All activity and identity fixtures in tests are synthetic; none are imported into the live collector or database. Local handoff tests use temporary synthetic setup files only and verify exact key scope, pooled certificate-verified URI construction, missing-owner refusal, input validation, file permissions, and symlink refusal. Owner-sync tests verify noninteractive refusal, explicit confirmation/cancellation, live-source restrictions, unknown/zero distinctions, token redaction, private receipt scope/permissions, and uncertain outcome without automatic retry; all network calls are mocked.

Tests cover UTC+7 day/year/leap boundaries, current-time clipping, idle exclusion, overlap and duplicate/conflicting watchers, browser identity, category precedence, missing/zero/future states, cross-year weeks, device isolation, malformed events, source-switch races, localhost Host/Origin restrictions, and aggregate-only export. Cloud tests cover actual in-memory Better Auth sessions, disabled signup, owner authorization, write-only token scope, strict payload bounds, cross-site denial, redacted failures, and password input retry/cancellation.

Local browser smoke checks verified the explicit no-data view and labeled synthetic demo, heatmap, category filters, and responsive layout. HTTP checks verified local HTML, JavaScript, live and demo endpoints. Fresh real window/AFK observations are verified. The owner installed the Edge extension; recent browser events and exact foreground/browser identity mapping are verified without logging raw values. Before/after mapping with the same live inputs preserved every daily foreground total.

The configured production deployment reached Ready. Unauthenticated checks passed: root redirects to login (307), login renders (200), activity/sync deny (401), session is null with no-store (200), signup is unavailable (404), and cross-site activity requests deny (403). The owner confirmed successful hosted login and visible data after refreshing following a real manual sync. The server-generated receipt was verified locally without reading credentials or raw activity. Live logout/relogin confirmation remains pending; the real in-memory auth test already covers session revocation.
