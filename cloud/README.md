# Daymark private web app

This app hosts daily aggregates on Vercel with a dedicated Neon PostgreSQL database. The existing local ActivityWatch dashboard remains in the parent folder.

## Data boundary

The upload body has exactly `schemaVersion`, `timeZone`, and `days`. Every day contains exactly `date`, `status`, and `seconds`. Known days have numeric seconds for coding, github, chatgpt, orca, reading, and other. Missing days have null seconds. Future dates, extra fields, duplicate dates, nonfinite/negative durations, and totals above 86400 seconds are rejected.

No window titles, URLs, paths, detailed intervals, or device identifiers are accepted or stored by the activity API. Coverage status preserves missing/partial/complete observations. The server records the sync receipt time.

## Authentication and authorization

Better Auth 1.7.10 runs inside this app with Neon as its database. A single owner is enrolled through an offline script excluded from deployment. Runtime public registration is disabled both in Better Auth and in the auth route allowlist. No social OAuth, email service, or public signup is enabled.

Every activity read validates the server-side session and compares its immutable user ID with OWNER_USER_ID. Every sync write needs a separate write-only bearer token; the cloud stores its SHA-256 hash. The token cannot read activity. The owner ID comes from server configuration, never an upload parameter. All activity responses use private/no-store headers.

Sessions use signed secure cookies over HTTPS, database validation, 12-hour maximum lifetime, and sign-in with `rememberMe:false`. Login attempts use a database-backed rate limit. Login IP and user-agent fields are not retained by the authentication hooks. No analytics or app telemetry is configured.

## Credential setup

1. Create a dedicated free Neon project/database, including its database credential; use it only for this app and store the runtime connection in Vercel sensitive server environment variables.
2. Generate this app's authentication signing secret and write-only Mac sync token. Store secrets locally under ignored `.runtime/` with owner-only file permissions; upload only the signing secret and the sync-token hash to Vercel.
3. The owner runs the offline setup script, enters and confirms their own password without terminal echo, and types CREATE to submit it. The agent must not run this step or generate/set the password. The database receives the library's password hash; the password is not saved in a local file.

Provider authentication and credential creation require the owner's approval. No launch-at-login or scheduled sync service is included. See [current setup status](../docs/CLOUD-STATUS.md) for what has actually completed.

Database URLs carrying passwords and signing/authentication credentials must be submitted by the owner directly in Vercel, not transmitted through agent tools or chat. The earlier ordinary consent question for agent transmission is superseded. Follow [the exact owner-controlled handoff](../docs/VERCEL-HANDOFF.md); the offline helper prepares private local files only and never uploads them.

For a fresh checkout, install Node.js 24 and run `npm ci` here. Create the private `.runtime/` directory in the project root with mode 0700. Its `cloud.env` needs DATABASE_URL, BETTER_AUTH_SECRET and APP_ORIGIN; `owner-settings.json` has the shape `{"email":"owner@example.test"}` (replace this placeholder locally). Set both files to mode 0600 and never commit them. Apply the schema with `node --env-file ../.runtime/cloud.env --import tsx scripts/migrate.ts`, then have the owner open `setup-owner.command` themselves. Password input is hidden, requires 14–128 characters and matching confirmation, and retries invalid input before the final CREATE submission. Do not pass a password through an environment variable, shell argument, chat, or file.

In Vercel, use the `cloud` root directory when importing this repository. Use the `nextjs` framework, the checked-in build/install commands, and server-only sensitive environment settings. Exclude local scripts, database scripts, and tests from deployment using `.vercelignore`. GitHub contains source and synthetic tests only; it must never contain collected activity, private runtime configuration, or credentials.

## Server environment

- APP_ORIGIN: exact canonical HTTPS origin.
- DATABASE_URL: dedicated Neon database connection, server only.
- BETTER_AUTH_SECRET: random authentication signing secret, server only.
- OWNER_USER_ID: confirmed stable owner ID.
- SYNC_TOKEN_SHA256: SHA-256 digest of the separately stored Mac sync token.

No secret uses a NEXT_PUBLIC_ prefix. Values are not included in source files or deployment metadata.

## Build and test

```sh
npm ci --no-audit --no-fund
npm test
npm run typecheck
NEXT_TELEMETRY_DISABLED=1 npm run build -- --webpack
```

Tests use synthetic in-memory identities and payloads. They do not write fixtures into the live database.

`db/002-activity.sql` defines the activity table. `scripts/migrate.ts` uses the pinned Better Auth migration API, saves its generated auth SQL, then applies the aggregate schema. `scripts/create-owner.ts` refuses enrollment if any user already exists. Both scripts are excluded from deployments.

## Local sync

From the parent project, `python3 sync.py` validates the live snapshot without uploading. Explicit upload requires `--send --origin https://YOUR_VERIFIED_DEPLOYMENT` and DAYMARK_SYNC_TOKEN injected from the private local credential file. No background or login persistence is configured.

The hosted dashboard offers yearly heatmap, daily category drilldown, filters, selected day/week/month/year totals, last-sync time, and missing-data states. Detailed timelines remain in the localhost dashboard because they require event timestamps.

Owner setup refuses noninteractive input and password environment variables. The confirmed email is read from ignored local owner settings; it is not hardcoded in deployed source.
