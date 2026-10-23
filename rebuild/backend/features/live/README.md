# Tank reading streams (T15)

Protected server-push WebSocket:
`/api/v1/hatcheries/{hatchery_id}/tanks/{tank_id}/stream?cursor={stream_cursor}`.
Use the existing browser session cookie and a configured allowed Origin.
Production requires WSS; explicit development permits loopback WS only.
The device-only HTTPS service does not expose this route. Relay commands/status
remain on their T14 HTTP API. No browser screens or quality policy are added.

## Snapshot, connect, resume

1. Fetch `/readings` and save its `stream_cursor`. Complete any history pagination
   using `next_cursor`; every page keeps the original snapshot's stream cursor.
2. Connect with that stream cursor. Commits after the snapshot replay in ascending
   journal position, including changes committed before the connection opened.
3. Save each processed message's cursor. Reconnect with the last processed cursor.
   Treat cursors as opaque tokens: do not parse, increment or compare their text.
4. On `resync_required`, fetch a fresh history snapshot and replace local state,
   then reconnect. Never resume using a cursor from a partially applied message.

Stream cursors are deterministic, domain-separated HMAC-SHA256 signed tokens
bound to hatchery, tank and journal position. They convey no access permission
and contain no credentials; their encoding is not encryption. Retaining the
existing private signing key permits replay after an API restart. Key replacement
invalidates cursors and requires a fresh snapshot. A missing, malformed, modified
or wrong-tank cursor is rejected before upgrade. An ahead-of-journal cursor
requires resynchronization. No migration, new worker or in-memory event journal.

The stream covers **all future changes for the tank**, independent of history
filters. Clients apply their selected display filters themselves. Measured-time
history can exclude unknown capture times; live device readings still truthfully
include `measured_at: null` and the canonical telemetry/time-quality provenance.
Manual changes include the exact immutable revision, including void/restore state,
actor, reason, version and measurement provenance. No reading is reclassified.

## Messages, version 1

All messages carry `v: 1` and `type`:

| type | Additional fields | Meaning |
|---|---|---|
| `ready` | `cursor` | Authenticated subscription accepted at the supplied position; replay may follow. |
| `reading.changed` | `cursor`, `reading` | Canonical reading response, with the exact committed device capture/manual revision. |
| `heartbeat` | `cursor` | All matching changes through this position have been sent. |
| `resync_required` | `reason: "fresh_history_required"` | Cursor is ahead or more than 1,000 tank changes are pending; socket closes normally. |

Delivery is at least once. Deduplicate by cursor and by reading identity/version
(`origin + id + version` for manual; immutable `origin + id` for device). A device
event duplicate does not add a journal entry. Positions may legitimately skip
because the journal watermark belongs to the hatchery, not a single tank.
Heartbeat cursors may advance over other tanks' changes, only after all matching
changes through that position were sent. Never infer missing tank data from gaps.

## Access and resource bounds

The WebSocket explicitly checks Origin, scheme, session, active operator membership
and tank ownership, independently of HTTP middleware. Before each batch, even
when idle, it revalidates session revocation, disable, membership and the existing
8-hour absolute/30-minute inactivity deadlines. Passive authentication may refresh
provider tokens but never updates `last_seen_at`; messages and heartbeats cannot
keep an inactive operator logged in. Regular authenticated HTTP activity retains
its existing behavior. Revocation is observed on the next poll/batch, subject to
bounded in-flight authentication/database/send work.

Defaults: poll once per second, at most 100 reading events per batch, heartbeat
every 15 seconds, 4 connections per browser session, 32 per API application process,
five seconds per message send. Backlog is measured only for the subscribed tank;
exactly 1,000 changes may replay. SQL queries run in threads with short transactions
that end before waiting/sending. No queue grows with a slow receiver. The endpoint
is server push only; client application messages close it. Transport input is
limited to 4,096 bytes by the local launcher.

Before upgrade, failed access/cursor checks and full connection limits return
HTTP 403 (Uvicorn's WebSocket denial). After upgrade, access loss closes with 1008,
temporary database failure or send timeout with 1013, and resync with 1000.
Clients should back off on failures and use history to recover an invalid cursor.
These are engineering defaults, not measured production capacity claims.

`backend/run.cmd` selects pinned `wsproto==1.3.2` through Uvicorn and disables
forwarded-header trust. A future production TLS/proxy launcher must preserve a
trustworthy ASGI `wss` scheme and allow only explicitly trusted proxies (T24).

## Verification

From `rebuild`, use the existing test database, never live data:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest backend.tests.unit.test_live backend.tests.integration.test_live -v
```

Integration cases use disposable PostgreSQL schemas, generated provider keys and
both ASGI and real loopback TCP WebSockets with Uvicorn/wsproto. They exercise
commits/rollback, duplicate/reordered capture times, concurrent journal ordering,
snapshot handoff, manual lifecycle, disconnect/restart, authorization/revocation,
limits and resynchronization. Send-timeout testing injects ASGI transport
backpressure on a real TCP connection; it is not a natural OS-buffer saturation
or production throughput benchmark. Timers are shortened only in test app state.
