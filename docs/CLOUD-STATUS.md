# Private online dashboard status — 2026-10-16

The optional Vercel/Neon app stores only daily dates, coverage status, and six category duration totals. Raw ActivityWatch events stay on the Mac. Owner-only reads and a separate write-only sync token are enforced by the server. Public registration is disabled.

## Completed

- Next.js app, Better Auth owner sessions, strict aggregate API, heatmap, filters, daily drilldown, period totals, and manual Mac sync implemented.
- Dedicated free Neon database created in Singapore. Authentication and aggregate schemas applied. No real or synthetic activity uploaded.
- Database connection, signing secret, and sync token stored in ignored owner-readable local files. No credential values are included in this repository.
- User-approved Vercel CLI login completed. Dedicated `daymark-private` project created in the verified account. The earlier connected-API project creation returned permission denied; the authorized CLI path succeeded.
- Owner setup requires two hidden password entries and explicit CREATE. Invalid length or mismatch now reports a safe reason and retries without printing input.
- User-provided [GitHub repository](https://github.com/QuocKhanhLuong/DayMark) was inspected: public and initially empty. Sanitized source, documentation, and synthetic tests were pushed to `main` in commit `ccc319f`. All 61 files passed checks against private local setup values, credential patterns, database URIs, private keys, private paths, and generated files. The Git commit uses a GitHub no-reply address.
- Vercel's dedicated project is connected to that repository, with `cloud` as root and the reviewed Next.js build/install commands. Assigned production origin: `https://daymark-private.vercel.app`.

## Pending verification

- The owner must finish `setup-owner.command` locally. An earlier attempt stopped before submission; no password is available to the agent.
- Automatic approval review rejected sending the database connection, signing secret, and sync-token hash to Vercel. No transfer occurred. The ordinary approval question is superseded: the owner must enter/submit those values directly in Vercel, not through agent tools. Do not retry the rejected transfer or treat a general consent answer as permission to transmit secrets.
- The source deployment finished **Ready** at https://daymark-private.vercel.app. Root/login returned 200; root clearly shows setup-in-progress. Unauthenticated GET activity, POST sync, GET session, and POST signup requests returned 503 with a fixed setup-incomplete error and private/no-store headers. No activity or authentication data was disclosed.
- Follow [owner-controlled configuration instructions](VERCEL-HANDOFF.md): finish local enrollment, run the offline preparation helper yourself, enter five Production-only Secret settings directly in the dedicated Vercel project, and redeploy. Hosted owner login/logout/session and aggregate sync remain unverified.
- No working hosted login or uploaded activity is claimed yet.
- Edge watcher installation remains pending; the local app/window and idle watchers already produce observations. Login auto-start and scheduled sync remain disabled.

## Validation

- 73 Python tests and 11 local UI tests passed; fixtures are synthetic, including all local handoff tests.
- 18 cloud tests passed, including real in-memory Better Auth login/session/logout, rejected public signup, unauthorized API calls, token scope, strict payload checks, and owner input retry/cancellation.
- TypeScript typecheck and production build passed. The production build will be repeated if deployed sources change.
- Expanded source audit: 65 files checked with no detected private setup values, generated/private paths, credential patterns, database URIs, private keys, or personal account paths/emails. No real credentials were used in handoff-helper tests.

Resource IDs, provider credentials, owner identity/enrollment records, and operational logs belong only in ignored local runtime storage. This public setup record deliberately omits their values.
