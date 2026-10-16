# Aggregate export boundary

Manual aggregate export is implemented in `sync.py` and `activity_dashboard/export.py`. Its default is dry-run; `--send` and an exact approved HTTPS origin are required to upload. No widget or automatic scheduling is enabled. See [cloud status](CLOUD-STATUS.md) for deployment verification.

The opt-in export contains calendar dates in Asia/Ho_Chi_Minh and six daily category totals in seconds. It omits hostname/device identifiers, bucket IDs, exact event timestamps, window titles, URLs, paths, and session records. Missing dates retain null totals. Partial observations carry an explicit completeness marker.

Proposed minimal record after confirmed destination/scope:

```json
{
  "date": "2026-10-16",
  "status": "partial",
  "seconds": {
    "coding": 3600,
    "github": 600,
    "chatgpt": 900,
    "orca": 1200,
    "reading": 1800,
    "other": 0
  }
}
```

This example is synthetic. A missing date has `status: "missing"` and `seconds: null`. These totals still reveal daily behavior; remote transmission requires a confirmed destination and scope. Publishing the current dashboard server or exposing ActivityWatch's raw local API is not an export mechanism.
