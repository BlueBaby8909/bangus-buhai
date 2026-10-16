# Device contracts v1

Offline message models, validation, wire fixtures and JSON Schema snapshots for T02 (PRD R03, R05-R07, R14 and R17). These modules import Pydantic and the standard library only. They do not import the application, read credentials, connect to a broker/database or operate hardware.

## Run the checks in CMD

Use the backend environment prepared by [the rebuild setup guide](../README.md). It already pins Pydantic 2.14.1; T02 adds no dependencies. The verified interpreter is Python 3.14.6.

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild"
backend\.venv\Scripts\python.exe -m unittest discover -s contracts\tests -v
backend\.venv\Scripts\python.exe -m contracts check
```

The first command runs unit and fixture regressions. The second checks every catalog expectation and compares all five schema snapshots with the current models, without rewriting contract artifacts. Normal ignored Python bytecode caches may be created.

After an intentional model change, explicitly regenerate snapshots and rerun the checks:

```cmd
backend\.venv\Scripts\python.exe -m contracts export-schemas
```

`models.py` is the structural source of truth. Generated files under `schemas/` use JSON Schema Draft 2020-12. Do not independently edit snapshots. They describe structure, not the entire protocol: raw-byte limits, duplicate keys, strict integer input, cross-field relationships, topic/binding context and event correlation also require the rules below and the shared fixtures. Passing a generic JSON Schema validator alone is insufficient.

## Messages and common rules

Example topic base: `bangusbuhai-rebuild/devices/BB-AABBCC112233`. The prefix is a local example, not a broker setting or a connection. All payload fields are required, including nullable fields; unknown fields are forbidden at every level.

| Suffix | Model / schema snapshot | Main content |
|---|---|---|
| `/telemetry` | `Telemetry` / `telemetry.v1.schema.json` | Immutable capture, readings, relay and diagnostics |
| `/status` | `Status` / `status.v1.schema.json` | Boot/connection identity and `online` or `offline` |
| `/cmd` | `RelayCommand` / `command.v1.schema.json` | Bound, expiring `relay.set` desired-state command |
| `/command-results` | `CommandResult` / `command_result.v1.schema.json` | Correlated accepted/applied/rejected/failed event |
| `/acks` | `Acknowledgement` / `ack.v1.schema.json` | Reference to a stored/duplicate telemetry or result event |

- Every message contains integer `schema_version: 1` and canonical `device_id` (`BB-` plus 12 uppercase hex digits). No legacy/unversioned adapter is provided.
- UUID fields are lowercase canonical 36-character strings. Format validation does not prove uniqueness, enrollment or authenticity.
- The topic has exactly four components: `{prefix}/devices/{device_id}/{suffix}`. The trusted context prefix is 1-64 ASCII letters/digits/underscores/hyphens; the topic is at most 256 characters. Wildcards and unrelated suffixes are rejected.
- Input is UTF-8 `bytes`, at most 4,096 bytes including whitespace. Root JSON must be an object. Objects/arrays count toward depth, with root depth one and maximum depth eight. Duplicate keys, even escaped or nested duplicates, are rejected before model validation.
- Integer fields accept JSON integers only, not Booleans, strings or floating-point literals. Sequence and diagnostic counters are `0..4294967295`; uptime and age fields are `0..9007199254740991`.
- Measurement values accept finite binary64 numbers, including numeric integers, but not Booleans or numeric strings. NaN, Infinity, floating overflow and nonzero values that underflow to zero are rejected. Real numeric zero is preserved.
- Times use valid UTC `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` text, with zero to six fractional digits. Numeric epochs, offsets, naive/local times, impossible dates and leap-second spellings are not admitted.
- Firmware versions contain 1-64 characters. Reason codes contain 1-64 characters, start with a lowercase letter and continue with lowercase letters, digits or underscores. Diagnostics require exactly `queue_dropped` and `reconnects`; these are cumulative boot counters, not queue-size limits.

The byte/depth/string bounds are engineering defaults accepted for T02. No ESP32 parser/memory compatibility claim follows from Python checks.

## Telemetry and reading age

[The default-pH example](fixtures/valid/telemetry-default-ph.json) is a complete payload. It requires `binding_id`, `boot_id`, `seq`, `fw_version`, `measured_at`, `time_quality`, `capture_uptime_ms`, `readings`, `relay` and `diagnostics`, in addition to the common version/device fields.

`time_quality` is `synchronized` or `unsynchronized`. A synchronized capture requires `measured_at`; an unsynchronized capture requires explicit null. Server receipt time is not part of this message and cannot replace missing capture time. Clock quality and acquisition validity remain different concepts.

Each of the three readings requires `value`, `unit`, `source`, `validity`, `sample_age_ms` and `last_valid_age_ms`:

| Reading | Unit | Allowed source |
|---|---|---|
| `temperature` | `degC` | `sensor` |
| `turbidity` | `NTU` | `sensor` |
| `ph` | `pH` | `sensor` or `default` |

Ages describe the sample at snapshot capture, not at transmission. Nullable ages must be explicitly present, and known ages cannot exceed capture uptime. Retransmission must preserve the original event, including ages and diagnostics.

| Validity / source | Rule |
|---|---|
| Sensor `valid` | Numeric value; both ages known and equal because the sample is itself the last valid sample. Valid temperature must be younger than 60,000 ms (PRD R03). |
| Sensor `invalid` or `missing` | Value must be null. Known age/last-valid metadata may remain for diagnosis. No zero substitution. |
| Sensor `stale` | Value may be null or a held number. A held number requires known sample age. Earlier conservative staleness is allowed; no turbidity/pH stale threshold is invented. |
| Sensor `unverified` | Numeric value; age may be unknown. This preserves the owner's selected unknown-age behavior without asserting freshness or valid measurement. |
| Default pH | Numeric value, `source: default`, `validity: unverified`, and both ages null. A default is not a physical observation. |

Manual and estimated sources are not admitted by this device contract; their actor/method rules belong to later API work. Sensor-pH fixtures illustrate the format, not a physical pH integration. No calibration range or hatchery suitability is inferred from a finite number or `valid` acquisition tag.

The relay snapshot requires `on` (Boolean or null), `mode: demo` and a reason code. Null means unknown state, not OFF. The state describes the unloaded GPIO demonstration, not confirmation that connected equipment operated.

## Status, commands, results and acknowledgements

Status requires `boot_id`, `connection_id` and `state`. It carries no claimed disconnect timestamp. A retained status is an availability hint only. Later transport/ingestion code must distinguish connections and ignore superseded LWT events; this package does not maintain availability state.

Commands require `binding_id`, `command_id`, `type: relay.set`, Boolean `desired_on`, `issued_at` and `expires_at`. Expiry must follow issue time. Historical commands can parse after expiry; the separate delivery helper applies a supplied clock and requires `issued_at <= now < expires_at`. It rejects an unsynchronized clock, a naive/missing `now`, not-yet-issued commands and expired commands. It does not read the clock itself or select a maximum lifetime/retry policy.

Results require `binding_id`, `boot_id`, `seq`, `capture_uptime_ms`, `time_quality`, nullable `created_at`, `command_id`, `result`, `reason` and nullable `observed_on`. Creation time follows the same synchronization rule as telemetry. An `applied` result requires a known observed state. Correlation then requires matching device/binding/command IDs and an applied state equal to the command's desired state. An `accepted` result may still report the previous state. A late result remains auditable; correlation does not reauthorize command execution or change a stored command lifecycle.

Acknowledgements require referenced `boot_id`, `seq`, `event_kind` (`telemetry` or `command_result`) and `result` (`stored` or `duplicate`). Correlation checks device/boot/sequence and event kind. These are application acknowledgements, distinct from MQTT transport acknowledgements. Parsing a `stored` acknowledgement is not proof of a database commit; T13 must enforce the publish-after-commit boundary.

## Python interface and supplied context

From the rebuild directory:

```python
from pathlib import Path
from contracts import ValidationContext, validate_message

context = ValidationContext(
    device_id="BB-AABBCC112233",
    binding_ids=frozenset({"97fcde45-4112-41d4-a509-17e5bb1c0d91"}),
)
event = validate_message(
    "bangusbuhai-rebuild/devices/BB-AABBCC112233/telemetry",
    Path("contracts/fixtures/valid/telemetry-default-ph.json").read_bytes(),
    context,
)
```

Use `validate_message(topic, payload, context)` for wire input. Direct model APIs bypass raw JSON protections and topic/binding checks. The returned typed models are frozen, including nested readings. The supplied context is frozen and contains the expected device, prefix and allowed binding IDs. Unknown/mismatched bindings fail for telemetry, commands and results. Status and acknowledgements have no binding claim.

| Function | Behavior |
|---|---|
| `validate_message(topic, payload, context)` | Bounded raw parse, family-specific model validation, topic/device agreement and binding allowlist check; returns the typed message. |
| `classify_event(candidate, previous)` | `new` for no retained event/different device-boot-sequence identity; `duplicate` for identical normalized event content; raises `event_conflict` for changed content or event kind under the same identity. |
| `validate_command_delivery(command, *, now, clock_synchronized)` | Pure delivery-time check using the caller's aware datetime. |
| `validate_command_result(result, command)` | Correlates identity and successful application state. |
| `validate_acknowledgement(ack, event)` | Correlates the event reference and kind. |

Telemetry and results share the device/boot/sequence identity namespace. Object-key order and whitespace are ignored; measurements use normalized finite numeric values. Capture time, ages, binding, relay state and every diagnostic remain part of event comparison. The caller must look up the appropriate retained event; no replay cache, global sequence allocator or persistent deduplication is implemented here.

Failures raise `ContractError`. Its `as_dict()` contains only `code` and `field_path`; paths are sanitized and limited to 128 characters. Values and raw payloads are not included.

| Code group | Stable codes |
|---|---|
| Raw input | `invalid_payload`, `payload_too_large`, `nesting_too_deep`, `invalid_json`, `invalid_number`, `duplicate_key` |
| Structure/routing | `unsupported_version`, `invalid_schema`, `invalid_topic` |
| Context | `invalid_context`, `identity_mismatch`, `binding_mismatch` |
| Relationships/time | `event_conflict`, `correlation_mismatch`, `clock_unsynchronized`, `command_not_yet_valid`, `command_expired` |

Context is test/caller-supplied data, not authentication. Real broker identity/ACLs, registry lookup, binding capture windows and permission decisions remain later integration responsibilities.

## Portable fixture catalog

[fixtures/catalog.json](fixtures/catalog.json) declares the shared default context and 97 cases over 84 independent wire payload files. Every file is referenced. Fixtures are illustrative, not captured device evidence or validated biological readings.

Each case names `id`, `operation`, `file` and `topic`. A complete optional `context` replaces the catalog default. Successful message cases specify `expected_result` as the message kind; failures specify `expected_error` as the stable code. Relationship cases add `reference` and `reference_topic`; retry success is `new` or `duplicate`. Delivery cases supply `now` and `clock_synchronized`. Other successful helpers return null. Reference payloads are validated with the same context before correlation.

Supported operations are `message`, `retry`, `delivery`, `result` and `ack`. Invalid fixtures intentionally include malformed JSON, duplicate keys, invalid UTF-8 and semantic conflicts; read the raw bytes and do not globally reformat these examples. The `.bin` fixture preserves invalid UTF-8 exactly. Firmware/browser adapters can later consume this catalog and the rules as acceptance inputs; neither adapter is integrated by T02.

Verification evidence, original working-tree state and follow-up are recorded in [the T02 handoff](../../docs/status/tasks/T02.md). T03 will automate these commands. Device execution, relay safety enforcement, broker trust, buffering, persistence and release readiness require their own later evidence.
