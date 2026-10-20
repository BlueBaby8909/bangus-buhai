# 0005: Offline version 1 device contracts

Date: 2026-10-16. Status: accepted for T02 under the owner's explicit request to implement the plan. PRD references: R03, R05-R07, R14, R17. This is a software contract decision, not a new product specification or hardware/transport acceptance.

## Decision

Implement the device-message subset of [the proposal](../research/device-and-api-contracts.md) under [rebuild/contracts](../../rebuild/contracts/README.md): typed Pydantic v1 wire models, generated JSON Schema snapshots, independent raw fixtures and pure local validation/correlation. Reuse the pinned Pydantic dependency and standard-library unittest runner. Keep topic/version/device/binding and event correlation checks explicit; do not treat test context as authenticated identity.

The owner selected preservation of sensor values with unknown age as explicitly `unverified`, rather than rejecting the whole message. Such values cannot claim valid/fresh measurement. Store explicit nullable sample/last-valid ages at capture, separate from wall-clock synchronization; valid samples require known matching ages. Invalid/missing values are null. Default pH is unverified with no physical sample ages. The existing R03 60-second temperature staleness boundary remains in force; no biological or calibration limits are introduced.

Require schema version 1 and canonical IDs. Strict field/type rules reject coercion from strings/Booleans, extra fields, invalid JSON/UTF-8, duplicate keys and unrepresentable numbers. Engineering defaults are 4,096 payload bytes, depth eight, bounded 64-character firmware versions/reason codes, uint32 sequence/diagnostic counters and JavaScript-safe millisecond integers. These limits require future device compatibility evidence.

The relay remains an unloaded `demo`; unknown observed state is null. Acceptance and application are distinct. Applied results require a known state matching the correlated command. Commands carry issue/expiry times, with a pure delivery check against an explicitly supplied synchronized clock. Lifetime/retry/control arbitration policy is not selected here.

Telemetry and command results share the device/boot/sequence identity namespace. Retransmission includes unchanged age/diagnostic data; key ordering/whitespace do not change meaning. Changed event content or event kind under the same identity is a conflict. Callers retain events and enforce persistence/lifecycle behavior in later tasks.

## Authority and consequences

- The [contract README](../../rebuild/contracts/README.md), executable models/validators and shared fixtures define the accepted local contract. Generated JSON Schema alone cannot express every raw/semantic/context rule; all consumers must honor the documented rules and examples.
- The broader architecture, HTTP/API, security integration, broker ACL/certificate, binding lifecycle, buffering, control and deployment proposals remain provisional. No complete-proposal acceptance, production claim or legacy adapter is implied.
- No application service is imported or started by contract checks. No broker, database, credentials, prototype source or hardware is changed by this implementation.
- T03 can automate the recorded commands; later firmware/browser adapters can reuse the examples. Passing Python checks does not establish device, cross-language, broker, persistence or scientific correctness.
- Subsequent wire changes must be reviewed against existing consumers and fixtures. Do not silently expand strict v1 fields/vocabularies for an incompatible change.

The [T02 record](../status/tasks/T02.md) owns actual test evidence, limits and uncommitted state.
