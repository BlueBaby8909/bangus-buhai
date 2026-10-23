# Tank history and manual measurements (T12)

## T17–T18 operator read APIs

Authenticated routes under `/api/v1/hatcheries/{hatchery_id}`:

- `GET /tank-summaries?limit=25&cursor=...&include_archived=false`: page of canonical
  tanks and current assigned devices/configuration,latest delivered telemetry per
  current binding,server_time and the existing60000ms temperature-staleness value.
  Limit1..100; registry pagination rules apply. Devices explicitly say connectivity
  unknown; this is not broker status ingestion or a quality classification.
- `GET /readings/export`: CSV of all-or-one tank,using optional tank_id,origin,
  time_basis,since,until,include_voided filters. Default received time includes null
  capture times; default excludes voided entries. Captures one hatchery journal
  position before download,then traverses short200-row history pages. Manual rows
  use the latest revision at that position. All matches export,not just a UI page.
  Source/validity/actor/version/void/times remain explicit; null is empty,not zero.
  Formula-leading textual cells are prefixed with an apostrophe; CSV uses standard
  quoting. A download interrupted by access/network/database failure is incomplete
  and must be retried. Session/membership are rechecked between batches.

Background browser requests may set `X-BB-Passive: 1`; it only prevents extending
inactivity and grants no access. Default foreground authentication is unchanged.
Origin/CSRF still protect writes; CORS permits that header and Idempotency-Key.
No database migration,firmware or MQTT change accompanies these interfaces.

See [operator frontend](../../../frontend/README.md) and
[T18 evidence](../../../../docs/status/tasks/T18.md).

T15 adds `stream_cursor` to each history response, bound to that exact snapshot
and shared across its pages. See [the stream protocol](../live/README.md) for
lossless history-to-WebSocket handoff, replay, access checks and client deduplication.

All interfaces are backend APIs. No history/form/export UI or MQTT ingestion is
implemented by this feature. Use the existing T10 session cookie, permitted
Origin and X-CSRF-Token on mutations. HTTPS is required outside explicit loopback
development. Active hatchery membership is checked on every request and again
inside each mutation transaction. Authentication, 16 KiB request limits, CORS and
no-store responses use the shared application boundary.

## Routes

Prefix: `/api/v1/hatcheries/{hatchery_id}/tanks/{tank_id}`.

| Method/path | Behavior |
|---|---|
| GET `/readings` | Combined telemetry/manual history |
| GET `/readings/{origin}/{reading_id}` | Current detail; origin is device or manual |
| POST `/manual-readings` | Create; 201 new, 200 identical creation retry |
| PATCH `/manual-readings/{reading_id}` | Append a full content replacement |
| POST `/manual-readings/{reading_id}/void` | Append a void revision |
| POST `/manual-readings/{reading_id}/restore` | Append a restoration revision |
| GET `/manual-readings/{reading_id}/revisions` | Newest revisions first |

Archived tanks remain readable. All manual writes, including retry requests,
are blocked until the tank is restored. Any current operator in the hatchery can
correct its manual entries. There is no hard deletion or device-event editing.
Device command results are excluded from reading history.

## Manual content

Example creation body (all identifiers and values are illustrative):

```json
{
  "request_id": "e71c9a09-4c07-40a6-9389-adb1b1967307",
  "measured_at": "2026-10-21T08:00:00+08:00",
  "temperature_c": 28.5,
  "ph": 7.2,
  "turbidity_ntu": null,
  "instrument": "Thermometer and pH test kit",
  "notes": "Morning sample"
}
```

Units are fixed: temperature_c = degrees Celsius, ph = pH, turbidity_ntu = NTU.
At least one value is required. Null/omitted metrics are explicitly missing;
zero remains a supplied numeric measurement. Values must be finite JSON numbers;
booleans and numeric strings are rejected. Unknown fields, estimates and
client-provided provenance/actor/relay fields are rejected. Finite values do not
establish biological safety or instrument calibration; quality policy is T19.

measured_at must carry a timezone; it is normalized to UTC. Historical values
are allowed, with a five-minute future-clock tolerance. Server received_at is
the original submission time and never changes through corrections. Optional
notes are limited to 2000 characters and instrument to 200 characters.

Creation request_id is unique per hatchery/operator. Reusing it with normalized
identical original content and tank returns the current entry, even if later
corrected/voided. Changed content or tank returns 409. Distinct request IDs are
distinct observations; the backend does not guess duplicate measurements.

Correction uses the same content fields plus expected_version (positive integer)
and reason (trimmed 1..500 characters), without request_id. It replaces the full
content: omitted optional metrics/notes/instrument become null. Tank, author and
received_at cannot change. A stale version returns 409. Voiding/restoring take
only expected_version and reason. Restore before correcting a voided entry.
Restoration copies its last values; earlier revisions remain accessible.

Manual responses include origin=manual, provenance=operator_reported_measurement,
missing_metrics, id, hatchery/tank, created_by, received_at, revision_id, version,
actor_id, changed_at, reason, voided and measurement content. These are reported
measurements, not sensor-verified or calibrated evidence. Device responses include
origin=device, event id, canonical device_id, original binding_id, measured_at,
received_at and the complete validated T02 telemetry object. Device source,
validity, ages, relay and diagnostics are preserved without normalization loss.

## Filtering and pagination

GET /readings accepts:

- limit: default 50, range 1..200; cursor: opaque signed continuation, max 4096.
- time_basis: measured (default) or received; origin: all (default), manual, device.
- since inclusive and until exclusive, with explicit timezone, since < until.
- include_voided: false by default; true includes the selected void revision.

Order is descending (selected time, origin, immutable reading UUID). The measured
view excludes unknown-capture events and reports unknown_capture_times=excluded.
The received view includes them and reports included; measured_at remains null.
Receipt ordering must never be presented as evidence of capture time or used to
invent model-window timestamps. Default/unverified pH remains clearly labelled.

Responses include items, next_cursor, time_basis and snapshot_position. The first
page captures a committed per-hatchery journal watermark; subsequent pages see
only changes up to that position and the latest manual revision at that point.
Corrections, voids, backdated records and uncommitted transactions cannot change
that page sequence. Start again without a cursor to see newer changes. Continue
with the same tank, time basis, origin, void filter and time range; limit may vary.
Authorization is checked afresh for every page. Cursor integrity uses a dedicated
HMAC domain derived from the existing private deployment token key; restart does
not invalidate it, but rotating that key does. No separate secret is needed.

Revisions use limit (50/default, 200/max) and optional before_version (exclusive).
The response includes items and next_before_version. Append-only descending
revision numbers keep continuation stable when newer revisions are added.

## Storage and verification

Migration 0004_t12 adds four tables:

- manual_readings: immutable identity, tank, author, creation request and receipt.
- manual_reading_revisions: immutable values, version, status, actor/time/reason.
- reading_history_state: transactional last position per existing/new hatchery.
- reading_changes: append-only references to telemetry or manual revisions.

Restrictive/composite FKs retain attribution. Database triggers initialize state,
append telemetry/revision journal references atomically, enforce contiguous manual
versions and forbid rewriting/deleting history. The counter row serializes journal
writers until commit: a larger committed position never overtakes an uncommitted
smaller one. Updates and rollbacks include counter, journal and measurement.
Device duplicates allocate no position; command results allocate none. Existing
telemetry is indexed during migration without changing its payload/timestamps.
The per-hatchery counter is intentionally a serialization point; production fleet
capacity still requires later load testing. No accounts, tanks or sample data seed.

Run from rebuild:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -t . -v
.\check.cmd
```

PostgreSQL tests create/remove only random schemas in the dedicated test database.
Existing API errors remain 401 authentication, 403 membership/CSRF/origin, 404
unavailable scoped resource, 409 stale/lifecycle/request conflict, 422 validation,
503 temporary infrastructure failure. Error bodies do not echo input or SQL.
Missing auth configuration fails closed; health remains database-free.

Migration is explicit: `python -m backend.database.migrate`. Never downgrade a
development/production database to exercise tests; rollback tests own their empty
disposable schemas. Local and hosted-CI evidence are separate in the T12 handoff.
