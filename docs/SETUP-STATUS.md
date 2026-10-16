# Mac setup status — 2026-10-16

- Official ActivityWatch 0.14.1 for Apple Silicon installed at `/Applications/ActivityWatch.app`. Installer SHA-256 matched the official release asset: `225916c1e641151638a062c796743ea21ba29c5d1bc162d84fc5591473d822db`.
- Foreground app/window-title and idle tracking approved by the owner. ActivityWatch server and window/AFK watchers are running in foreground terminal sessions. Fresh observations and positive active-time aggregation were verified without printing raw records.
- The native Accessibility settings screen has not been inspected. Permission dialogs were not bypassed. Existing observations confirm collection, not the complete macOS permission state.
- The owner installed and approved the official ActivityWatch Web Watcher in Edge. Fresh browser events are verified. Its Chrome-labeled, same-device bucket was matched to foreground Edge and mapped by exact ID in ignored local `config.json`; the unknown-host startup placeholder remains excluded. Before/after aggregation proved the mapping does not add foreground seconds. The restarted local dashboard reports window, AFK, and browser sources recent. Incognito collection was not enabled by this setup.
- Orca inspection was limited to public CLI help/schema and bundled documentation. Foreground use is supported; reliable general background duration remains unsupported. No private session/run logs were read.
- Local dashboard: `http://127.0.0.1:8766`. No launch-at-login service or automatic sync was installed.
- Collection begins when watchers run; no historical activity was invented. Missing coverage remains unknown. Demo fixtures are synthetic and never inserted into ActivityWatch.
- The separately approved private online extension is tracked in [CLOUD-STATUS.md](CLOUD-STATUS.md). It does not expose the ActivityWatch API or raw records.
