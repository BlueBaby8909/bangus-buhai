# 0009: Reading history and audited manual measurements

- Date: 2026-10-21
- Status: accepted by owner through the approved T12 implementation plan
- Requirements: PRD R07, R09, R10

## Decision

Device captures stay immutable with their original tank, binding, provenance and
nullable capture time. Reading history includes telemetry, not command results.
Receipt-time browsing is explicit and never substitutes receipt for capture time.

Operators may record measured temperature/pH/turbidity values, including partial
observations with at least one actual measurement. Missing values are missing,
not zero. Inputs are finite numbers, not booleans/strings or estimated values.
Manual provenance means operator-reported measurement; it does not certify a
sensor, test kit, calibration or biological interpretation. Measurement time is
explicit and timezone-aware, with a five-minute future-clock tolerance.

Only manual content may be corrected, voided or restored. Each change requires
an expected version and reason; append-only revisions preserve all values,
statuses, actors and server times. Every active operator in the hatchery has
equal rights. Tank/author/initial receipt stay fixed. Archived tanks allow reads
but block all manual mutations until restoration. There is no hard deletion.

Creation uses an operator/hatchery-scoped request UUID for safe retries. A
conflicting retry fails rather than overwriting. A corrected entry still retains
the original request content for comparison.

## Implementation consequences

T12 adds versioned migration 0004_t12 and a readings feature, without replacing
earlier migrations or device contracts. Composite ownership FKs and immutable
database history protect attribution. Atomic triggers journal only newly stored
telemetry and manual revisions; retries/rollbacks do not leave phantom records.

A per-hatchery transactional counter gives signed pagination cursors a committed
watermark. Continuations select manual revisions as of that watermark, keeping
the page sequence stable through concurrent corrections, voids or late arrivals.
The counter serializes journal writers; production throughput remains a later
measured deployment gate. It is not a claimed capacity result.

Default history orders newest capture time first; captures without synchronized
time appear in the explicit receipt-time view with null capture time. No capture
times, calibration or model eligibility are inferred. HTTP details and examples:
[readings guide](../../rebuild/backend/features/readings/README.md).

## Boundaries

T12 is protected backend history/manual measurement work. UI/export, MQTT
admission/ACK, water-quality policy and forecasting retain their own milestones.
Real ESP32 proof/runtime binding/configuration confirmation remains a prerequisite
before live T13; T07 verification gaps and BOOT-button deferral remain unchanged.
The prototype, existing data/private settings, hardware and unrelated work are
preserved. This decision does not authorize publication, deployment or firmware.
