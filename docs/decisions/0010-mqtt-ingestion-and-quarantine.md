# 0010: MQTT ingestion and quarantine

- Date: 2026-10-21
- Status: accepted by owner through the T13 implementation plan
- Requirements: PRD R05–R09, R16–R18

## Decision

Deliver T13 backend first, with simulated devices and a disposable MQTT broker.
Keep real ESP32/HiveMQ acceptance pending verified firmware identity proof,
durable runtime binding/configuration confirmation and dedicated backend broker
access. HiveMQ remains selected; the test-only Mosquitto fixture does not restore
a self-hosted production broker. Do not resume deferred BOOT-button Wi-Fi work.

MQTT ingestion is a separate process from the API. It validates bounded T02 wire
content, qualified-broker topic identity and verified registry relationships.
Traffic never creates ownership. Accepted telemetry retains original binding,
capture time and provenance, including unknown capture times where admissible.

Publish stored only after commit; identical retries receive duplicate. Conflicting
content/kind is never overwritten or success-acknowledged. A lost ACK recovers
through device retries against persistent event identity, not an in-memory cache.
Broker PUBACK and application ACK remain distinct.

## Admission and uncertain history

Current active/confirmed bindings permit telemetry, including explicit unknown
capture time. Synchronized captures must be at/after assignment start and no more
than five minutes ahead of server receipt. Closed bindings require retained
confirmation and a synchronized capture within [start,end). Later reassignment
or archival does not change attribution of admitted historical captures.

Preserve schema-valid uncertain/conflicting events in bounded immutable quarantine,
outside tank history, without a success ACK. Deduplicate by content/identity and
keep variants. Capacity is 1000/device and 10000 overall; at capacity reject new
uncertain storage without blocking admissible events. No automatic deletion,
release, rebinding or timestamp reconstruction. Current firmware may keep retrying
an uncertain queue-head event; resolving that requires separate scoped work.

Retain successfully proved configuration documents per revision so confirmation
evidence survives future desired changes. Backfill only supported current
confirmations; absent historical proof remains absent. New command results wait
in quarantine for T14's authorized command context; existing committed identical
results can be acknowledged without changing a command lifecycle.

## Trust, operation and evidence

Use dedicated backend client credentials, strict TLS and qualified broker ACLs.
The subscriber cannot independently retrieve a publisher's certificate from an
ordinary subscribed message. Topic/client-ID strings alone are not credentials.
Live qualification flags remain explicit owner gates, not simulator certification.

Use bounded queues, transaction timeouts, manual broker acknowledgements,
generation fencing and a database/prefix singleton advisory lock. Loss of the
reserved lock connection stops the worker, including a pre-ACK lease check; no
silent reconnect/reacquisition. Capacity and deployed supervision still require
later qualification. No fleet-size or production-availability claim is made.

Protocol/configuration/inspection details: [MQTT guide](../../rebuild/backend/mqtt/README.md).
Actual execution, preservation and local/hosted/live limits belong to the T13
task record. No cloud changes, real key reuse, firmware/flash, Git publication or
deployment are included in this backend decision.
