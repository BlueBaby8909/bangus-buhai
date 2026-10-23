# Device and API contract proposal v1

Date: 2026-10-16. Status: **device-message subset implemented and verified offline in T02; remaining integration/API design proposed**. PRD: R03-R14, R16-R21. Parent: [replacement architecture](rebuild-architecture.md). The [PRD](../PRD.md) remains the product authority. [Decision 0005](../decisions/0005-device-contracts-v1.md) records the accepted device subset; [rebuild/contracts](../../rebuild/contracts/README.md) owns its executable wire rules, schemas and fixtures. Broker, persistence, API, control and deployment behavior below remains a proposal, not implemented integration. Original design baseline: `8ec0183` plus existing cleanup; T02's exact Git/test state is in [its record](../status/tasks/T02.md).

T02 adds explicit per-metric sample/last-valid ages, unknown-age `unverified` handling, strict bounded parsing, nullable unknown relay state and local context/correlation checks. The device section below is design context; use the executable package and its README for exact accepted field names, bounds and validation rules. Generated schemas do not replace raw/semantic checks.

## Identity, ownership and compatibility

T11 update: the [registry guide](../../rebuild/backend/features/registry/README.md)
now specifies the implemented HTTP management/claim/proof/configuration protocol,
accepted in [decision 0008](../decisions/0008-self-service-device-claiming.md).
Existing T02 MQTT schemas remain unchanged; real firmware claiming and MQTT
admission are not established by simulated HTTP device tests.

T13 backend update: [decision 0010](../decisions/0010-mqtt-ingestion-and-quarantine.md)
and the [ingestion guide](../../rebuild/backend/mqtt/README.md) now specify retained
confirmation evidence, binding capture-window admission, commit-before-ACK and
bounded immutable quarantine. Local generated-certificate broker integration does
not establish real ESP32/HiveMQ qualification. MQTT schemas stay unchanged; new
command results await authorized T14 command context. Unknown/uncertain capture
times must never be assigned to the current tank or a guessed time window.

- Preserve the canonical external ID `BB-` followed by 12 uppercase MAC hex characters. It is not an authentication secret. API device paths, MQTT topic and payload agree on it; a database row ID is a different identifier.
- Enrollment binds a broker-authenticated device to this ID and an authorized server-side registry entry. Broker ACLs restrict publication/subscription to that identity's topics; backend subscription messages alone do not expose the publisher's certificate for independent identity checks.
- A server-issued `binding_id` identifies an immutable device/tank/owner assignment. Telemetry cannot assign ownership or create/reassign a tank. Capture queues retain the original binding. Late historical events require a retained authorized binding and an admissible capture window; otherwise quarantine instead of assigning them to the current tank.
- `schema_version: 1` is mandatory for rebuilt messages. Unversioned existing messages are legacy, not silently v1. Use a separate development topic prefix/database during the rebuild. An eventual legacy importer/adapter needs an explicit mapping and preserves uncertainty; it must not fabricate capture times or validity.
- Unknown versions, unknown bindings, malformed/oversized JSON, duplicate keys, nonfinite numbers, invalid types and identity mismatches are rejected or quarantined with a bounded diagnostic reason. Concrete payload limits and exhaustive field constraints belong to executable schemas before implementation.

## MQTT topics

Base: `{prefix}/devices/{device_id}`. Keep legacy suffixes where possible, using explicit schema versioning and environment isolation.

| Suffix | Publisher -> subscriber | Delivery and meaning |
|---|---|---|
| `/telemetry` | Device -> ingest | QoS 1, non-retained; immutable selected reading snapshot |
| `/status` | Device/broker LWT -> ingest | QoS 1, retained; availability hint, never proof of recent valid measurements |
| `/cmd` | Backend publisher -> device | QoS 1, non-retained; persisted expiring command intent |
| `/command-results` | Device -> ingest | QoS 1, non-retained; correlated accepted/applied/rejected/failed report |
| `/acks` | Ingest -> device | QoS 1, non-retained; application acknowledgement after database commit |

The new acknowledgement/result topics require verified broker permissions. Backend service identity must be compatible with the cluster's selected authentication method. Device identity cannot publish acknowledgements/commands for itself or another device.

Status envelopes include schema/device/boot identifiers, a per-connection ID and online/offline state. A retained replay is only a hint; backend availability also needs fresh traffic and its own last-seen policy. Ignore an old connection's LWT when a newer connection is established. Server receipt time of a LWT is not asserted as the physical disconnect time, and its payload creation time is not a disconnect timestamp.

## Telemetry envelope

Example values are illustrative, not validated hatchery thresholds or measured device output:

```json
{
  "schema_version": 1,
  "device_id": "BB-AABBCC112233",
  "binding_id": "97fcde45-4112-41d4-a509-17e5bb1c0d91",
  "boot_id": "2cfaa1ad-48c9-46f3-bd8e-5ebf68790dd1",
  "seq": 7,
  "fw_version": "rebuild-example",
  "measured_at": "2026-10-16T03:00:00Z",
  "time_quality": "synchronized",
  "capture_uptime_ms": 300000,
  "readings": {
    "temperature": {"value": 28.0, "unit": "degC", "source": "sensor", "validity": "valid", "sample_age_ms": 1000, "last_valid_age_ms": 1000},
    "turbidity": {"value": 14.0, "unit": "NTU", "source": "sensor", "validity": "valid", "sample_age_ms": 2000, "last_valid_age_ms": 2000},
    "ph": {"value": 7.0, "unit": "pH", "source": "default", "validity": "unverified", "sample_age_ms": null, "last_valid_age_ms": null}
  },
  "relay": {"on": false, "mode": "demo", "reason": "startup"},
  "diagnostics": {"queue_dropped": 0, "reconnects": 0}
}
```

| Field/rule | Proposed semantics |
|---|---|
| Event identity | Unique `(device_id, boot_id, seq)`; `boot_id` is new per boot, `seq` is a uint32 allocated for the selected snapshot at capture, not serialization/retry. No wrap/reuse within one boot. Clock updates do not change event identity. |
| Capture and receipt time | `measured_at` is the selected snapshot's RFC3339 UTC capture time when synchronized, otherwise null with `time_quality: unsynchronized`. `capture_uptime_ms` is monotonic capture uptime, not send uptime. Backend adds its own `received_at`; it never replaces capture time with receipt time. Each metric also needs its actual sample age/last-valid capture metadata in the executable schema; a held reading's age cannot reset when a snapshot is selected. |
| Metric provenance | `source`: sensor/manual/estimated/default in the canonical API model. Firmware v1 may report sensor/default; manual records require an authenticated API actor. Estimated sources require an identified estimation method before admission. |
| Validity | valid/invalid/stale/missing/unverified. Invalid/missing values are null, never fabricated zeros. A stale held value may remain present but is marked stale. Default pH is unverified and remains distinguishable from an estimate or measurement. No NaN/Infinity. |
| Freshness/policy | Freshness is evaluated from capture/time quality and configured rules. Acquisition validity, biological quality, provenance and availability are separate fields; one cannot substitute for another. |
| Relay snapshot | Report the control owner's applied GPIO state and reason at capture. Mode vocabulary/arbitration must be finalized before implementation; `demo` does not mean physical equipment is connected or functioning. |
| Diagnostics | Cumulative drops/reconnects within the boot, plus bounded optional heap/RSSI/reset details. Do not include credentials or proofs of possession. Exact optional fields and size budget need schemas. |

Snapshot selection follows the intended R06 telemetry interval; acquisition/control run independently. Preserve capture identity, timestamp and value/provenance together through buffering. A disconnected or uncalibrated sensor cannot be presented as a valid biological measurement merely because JSON parses.

## Ingestion, acknowledgements and finite buffering

1. Verify broker trust/permissions and topic/registry/binding agreement; validate message schema and capture eligibility.
2. In one transaction, insert the reading and downstream outbox/job intent. Enforce unique event identity. Identical retransmissions are idempotent; the same identity with different content is a conflict, not a silent overwrite.
3. Only after commit, publish an acknowledgement naming schema version, event kind, `device_id`, `boot_id`, `seq` and `result: stored` or `duplicate`. Database errors never produce success acknowledgements. A lost acknowledgement can be recovered by resending the identical event. Retransmission preserves the entire event content, including diagnostic fields; fresh diagnostics use a fresh event.
4. Firmware keeps a bounded application queue separate from MQTT's transport acknowledgement semantics. Retain the PRD's 16-event bound. The proposed overflow behavior drops the oldest unacknowledged event, increments `queue_dropped`, and reports the loss; no claim of lossless arbitrary outages is made.
5. Queue persistence across reboot is not established by the current RAM queue. Decide/test the permitted loss budget and persistence strategy before firmware acceptance; do not add flash writes or change partitions without endurance/capacity/hardware evidence.

Unsynchronized, invalid or stale samples can remain auditable but are ineligible for forecast windows unless a reviewed preprocessing policy explicitly handles them. An online status message does not make them valid.

## Commands and results

API request body: `{"type":"relay.set","desired_on":true}` with a client idempotency key. Server authenticates actor, checks permission/target/binding and creates a persistent `command_id` and expiry. MQTT command includes schema version, canonical device/binding IDs, command ID, desired state, issue time and expiry. Server retains actor/audit information; devices cannot grant privileges by reporting an actor field.

Scope API idempotency keys to the authenticated actor and operation; reuse with different content is a conflict, not a new command. Result events use the same immutable boot/sequence identity model as telemetry, allocated when each result is created. A shared allocator prevents sequence collisions across telemetry and result events; application acknowledgements identify event kind too.

HTTP `202` means the intent was persisted. Track queued -> published -> accepted -> applied/rejected/failed; transport timeout is an uncertain outcome, not evidence of OFF or ON. Results may arrive out of order; persist receipt history and do not regress terminal state. A late legitimate result can resolve a timed-out command while preserving timeout history.

The device validates identity, schema, binding, expiry, supported type and safety preconditions, then enqueues work to the sole control owner. Reject commands with unverifiable expiry when clock synchronization is unavailable. Retries keep the same command ID and desired-state semantics; bounded duplicate tracking prevents reapplication within a boot. Across reboot, setting a desired state is intrinsically idempotent, but expiry and safety checks still run; old results cannot bypass a stale-temperature OFF guard.

Return command ID, boot ID, result, reason and observed state; successful application records the control owner's state, not physical load operation. Persist results for bounded retry/acknowledgement using the same application-ack pattern; success and replay behavior must be covered by fixtures. Boot-safe OFF does not wait for broker availability. Manual/automatic precedence, anti-chatter limits and TTL/retry budgets remain explicit design items before control implementation.

## HTTP and live API surface

Propose `/api/v1` with typed request/response schemas and consistent errors. Concrete paths below are replacement proposals; current routes remain documented separately.

| Surface | Proposed operations/behavior |
|---|---|
| Identity | T10 implements POST `/api/v1/auth/login`, GET `/api/v1/me`, POST `/api/v1/auth/logout`, opaque browser cookies and one operator role under decision 0007; the T10 record distinguishes local checks from live-provider verification |
| Tanks | T11 implements hatchery-scoped create/list/detail/rename/archive/restore with version checks; reading summaries remain later tasks |
| Devices | T11 implements trusted preparation, operator claim APIs, device challenge/proof/configuration confirmation, list/detail and retained binding lifecycle; see decision 0008 and the registry protocol guide. Real firmware/client onboarding remains a follow-up |
| Readings | T12 implements hatchery/tank-scoped `/readings` list/detail and `/manual-readings` create/correct/void/restore/revisions, with measured-only manual provenance and signed snapshot cursors; [decision 0009](../decisions/0009-reading-history-and-manual-measurements.md) and [API guide](../../rebuild/backend/features/readings/README.md). Device events stay immutable; quality evaluation remains later work |
| Commands | `POST /devices/{device_id}/commands`; query persistent command/result status by command ID; idempotency key and ownership checks |
| Forecasts | Create/history/latest with origin time, target time per horizon, model/scaler/policy provenance and documented confidence semantics; explicit insufficient/unvalidated states |
| Alerts | Durable history/detail/acknowledgement scoped to accessible tanks; notification dispatch status separate from alert state |
| Export | Authorized filtered history using stable pagination/streaming; explicit completeness/truncation and selected time basis |
| Live updates | Authenticated tank stream with event ID/cursor, schema version, type, tank ID and canonical record payload; catch-up or resync on reconnect |
| Operations | Separate liveness/readiness and protected diagnostics; sanitized public error responses |

Reading history has a deterministic total order, explicit time basis and stable cursor. Default measured-history order is capture time plus immutable ID; unknown-capture records use a separate received-time view/explicit null-time treatment. No mixing guessed timestamps into chronological model inputs. Use bounded pagination; export cannot imply full history when it only fetched a page.

T12 resolves this reading slice: newest-first order is selected time, origin and
immutable reading ID. Signed cursors preserve a committed journal watermark and
the latest manual revision at that point. Partial manual measurements are labelled
operator-reported; device source/validity/age and payload remain unchanged. Unknown
capture times remain null in the explicit receipt-time view. Revisions audit
correction/void/restoration; archived tanks allow reads only until restored.
Broader source proposals above do not authorize estimated manual inputs or server
biological classifications before their own tasks.

Errors use a stable machine code, human-readable message, request ID and safe validation details, with appropriate HTTP status. Never trust caller-supplied owner/farm fields as authorization. Authenticate/authorize live subscriptions before data delivery and re-evaluate access on expiry/revocation. Cursor gaps/retention expiry trigger resynchronization, not silent dropped history. Retention, replay windows, heartbeat, rate/size limits and numerical budgets must be finalized and tested.

R16's hatchery ownership interpretation is accepted in the [T09 database decision](../decisions/0006-database-ownership-and-bindings.md). Supabase/operator browser authentication is accepted in [decision 0007](../decisions/0007-operator-authentication.md), with implementation and live-check status in [T10](../status/tasks/T10.md). MQTT admission remains T13. Proposed defaults do not waive access controls or turn an unavailable forecast into a successful prediction. Numerical hatchery thresholds and model evaluation remain Q02/Q01/Q03 evidence questions.

## Verification matrix before implementation acceptance

T02 now supplies offline fixtures, schemas and local checks for message structure, provenance/time/age, bounded parsing, declared topic/binding context, duplicate/conflicting events, command delivery time and result/acknowledgement correlation. See [the package](../../rebuild/contracts/README.md) and [T02 evidence](../status/tasks/T02.md). Firmware serialization and browser adapters are not integrated yet.

Later verification must still cover real enrollment/inactive binding capture windows, queue overflow/reboot, database commit failure/lost acknowledgement, actual command safety/application/retry and result ordering, broker trust/permissions, denied cross-owner API/stream/export access and stream resynchronization. Local fixture checks do not establish any of those integration properties.
