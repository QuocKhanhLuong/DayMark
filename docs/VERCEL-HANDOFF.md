# Owner-controlled Vercel configuration

The production deployment is Ready at **https://daymark-private.vercel.app**. The owner completed the steps below, confirmed successful login, and performed a real aggregate sync. This guide remains for fresh setup or recovery; existing-owner enrollment refuses duplicates. No synthetic activity has been uploaded.

The earlier ordinary consent question about the agent uploading credentials is superseded. The agent must not submit database/password-bearing URLs, signing/authentication secrets, or enrollment passwords through its tools. The owner enters and submits production settings directly in Vercel. Do not paste values into chat or send screenshots of them.

1. Open `setup-owner.command` on your Mac yourself. Choose a password of 14–128 characters, enter it again, and type CREATE. Input is hidden. Invalid input reports a safe reason and retries. This password is only for Daymark login; it does not belong in Vercel environment settings.
2. Open `prepare-vercel.command` yourself. This offline-only helper reads the existing private setup files and creates five text files under `.runtime/vercel-handoff/` (folder 0700, files 0600). It prepares the pooled Neon URL with full certificate verification and the sync-token hash. It never uploads anything or prints values. It refuses to prepare files until the owner's enrollment receipt exists. The agent must not run it with live private setup values.
3. Open [Daymark's Vercel environment settings](https://vercel.com/quockhanhluongs-projects/daymark-private/settings/environment-variables) yourself. Confirm project **daymark-private**, then add the following exact keys. Select **Production only**, with type **Secret** (called **Sensitive** in older UI). Do not select Preview or Development. All names are server-only, with no `NEXT_PUBLIC_` prefix. Vercel documents the [Secret type here](https://vercel.com/docs/environment-variables/sensitive-environment-variables).

| Key | Value to enter directly in Vercel |
|---|---|
| `APP_ORIGIN` | Entire contents of `APP_ORIGIN.txt`; exact origin `https://daymark-private.vercel.app`, no trailing slash |
| `DATABASE_URL` | Entire contents of `DATABASE_URL.txt`; dedicated pooled Daymark database URL |
| `BETTER_AUTH_SECRET` | Entire contents of `BETTER_AUTH_SECRET.txt`; existing signing secret |
| `OWNER_USER_ID` | Entire contents of `OWNER_USER_ID.txt`; confirmed enrollment ID |
| `SYNC_TOKEN_SHA256` | Entire contents of `SYNC_TOKEN_SHA256.txt`; 64-character hash, not the original token |

4. In Finder, use Go → Go to Folder and enter this checkout's `.runtime/vercel-handoff` path. Open each text file locally in TextEdit; select and copy its entire value into the matching Vercel Value field, then click Save yourself. Each file has no surrounding quotes or trailing newline. Never import the whole `.runtime` folder, upload these files to GitHub, or copy the raw sync token into Vercel.
5. After all five settings are saved, go to Daymark → Deployments → latest production deployment → Redeploy. Keep existing deployment protection enabled. The new deployment must finish Ready before login testing. Settings do not modify the previously built deployment.
6. Report only **“Vercel settings saved and redeployed”**. Do not send any values. Then sign in at the production URL yourself so owner login, logout, session restoration, and actual aggregate sync can be verified. No owner-password recovery or account enrollment is performed by the agent.

The handoff files remain local, ignored by Git, and readable only by the Mac owner. They may be removed after successful configuration; keep the original private setup files for local sync. Automatic login launch and scheduled upload remain disabled.

## Edge collection

In Edge, install the official [ActivityWatch Web Watcher](https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi), reviewing its active-tab URL/title permissions yourself. Leave incognito disabled. The tracking scope was already approved, but installation is not yet confirmed. After installation, return to the local dashboard; if Edge still appears as Other, follow the exact bucket-mapping instructions in the main README. Do not upload browser history, activity exports, URLs, or window-title screenshots to troubleshoot.
