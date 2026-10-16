# Private online dashboard status — 2026-10-16

The optional Vercel/Neon app stores only daily dates, coverage status, and six category duration totals. Raw ActivityWatch events stay on the Mac. Owner-only reads and a separate write-only sync token are enforced by the server. Public registration is disabled.

## Completed

- Next.js app, Better Auth owner sessions, strict aggregate API, heatmap, filters, daily drilldown, period totals, and manual Mac sync implemented.
- Dedicated free Neon database created in Singapore. Authentication and aggregate schemas applied. No real or synthetic activity uploaded.
- Database connection, signing secret, and sync token stored in ignored owner-readable local files. No credential values are included in this repository.
- User-approved Vercel CLI login completed. Dedicated `daymark-private` project created in the verified account. The earlier connected-API project creation returned permission denied; the authorized CLI path succeeded.
- Owner setup requires two hidden password entries and explicit CREATE. Invalid length or mismatch now reports a safe reason and retries without printing input.
- User-provided GitHub repository was inspected: public and initially empty. Only sanitized source, documentation, and synthetic tests are intended for it.

## Pending verification

- The owner must finish `setup-owner.command` locally. An earlier attempt stopped before submission; no password is available to the agent.
- Configure Vercel's exact canonical origin, dedicated database connection, signing secret, confirmed owner ID, and sync-token hash as sensitive server environment values.
- Link the GitHub repository with `cloud` as root, deploy, and verify hosted authentication and aggregate sync before calling the online app complete.
- No live dashboard URL or uploaded activity is claimed yet.
- Edge watcher installation remains pending; the local app/window and idle watchers already produce observations. Login auto-start and scheduled sync remain disabled.

## Validation

- 68 Python tests and 11 local UI tests passed previously; fixtures are synthetic.
- 18 cloud tests passed, including real in-memory Better Auth login/session/logout, rejected public signup, unauthorized API calls, token scope, strict payload checks, and owner input retry/cancellation.
- TypeScript typecheck and production build passed. The production build will be repeated if deployed sources change.

Resource IDs, provider credentials, owner identity/enrollment records, and operational logs belong only in ignored local runtime storage. This public setup record deliberately omits their values.
