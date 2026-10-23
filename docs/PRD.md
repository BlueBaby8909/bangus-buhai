# Bangus Buhai product requirements

Revision: 2026-10-21 ownership clarification for T09, following the 2026-10-16 production-software rebuild scope. Authority: this file. Source-review baseline remains 2026-10-15, Git `785e08b` plus the local cleanup reviewed then; this scope revision is not a new runtime or hardware audit and does not certify release readiness.

## 1. Product vision and scope

Help milkfish tank operators, farm technicians, and aquaculture researchers observe temperature, pH, and turbidity and receive useful early warnings through 1-, 2-, 3-, and 4-hour forecasts. Reducing mortality is the intended benefit; field effectiveness has not been measured in this repository. The owner selected hatchery/larvae for the first deployment on 2026-10-16, resolving the earlier hatchery versus grow-out ambiguity for this release. Operating conditions and scientifically appropriate limits remain [Q02](research/open-questions.md#q02-domain-policy).

The owner confirmed ESP-IDF as the active firmware and an unloaded relay used for visual demonstration on 2026-10-15. HiveMQ Cloud is the selected broker; Arduino and self-hosted broker implementations were retired. The existing implementation is a working prototype according to the owner; its production readiness has not been established. The rebuild aims to deliver production-ready software satisfying this PRD, with physical hardware expansion handled in later milestones. Physical pH measurement, connected temperature-control equipment, authenticated multi-user access, and production infrastructure are incomplete or unverified in the current implementation; this describes implementation status, not removal of future requirements.

### First production-software release

Owner-confirmed on 2026-10-16; rationale is in [decision 0003](decisions/0003-first-production-software-release.md).

- Serve a small group of real operators at one milkfish hatchery, targeting the larvae stage. Authentication, operator membership and tank/device ownership remain required under R16-R17. All operators have equal access within their assigned hatcheries; the owner provisions accounts through trusted tooling. Multi-farm rollout is a later milestone; using one farm does not waive access-control verification.
- Keep the current prototype hardware and ESP-IDF baseline while rebuilding the software. Hardware upgrades are outside this release. The relay remains unloaded for visual demonstration under R14; connected temperature-control equipment under R15 is deferred to a later hardware milestone.
- Preserve explicit pH provenance under R03/R07/R08/R10/R12. Default or estimated pH must not be presented as physical measurement or validated prediction evidence. Physical pH integration remains future scope under R22.
- Require evidence for applicable reliability, data integrity, access control, encrypted transport, deployment, monitoring, recovery, and verification requirements under R01-R21. The existing requirement table continues to define their behavior; a software-first milestone is not a waiver of unfinished software requirements.
- Resolve model timing/provenance, domain policy, capacity, and environmental/hardware verification limits before making corresponding production claims. Forecast names, a successful build, or working demonstration screens do not establish release acceptance.

This release boundary does not certify the prototype hardware for unattended operation, establish biological thresholds, or prove forecast accuracy. Concrete hosting, capacity, service targets, model acceptance metrics, and rollout/recovery criteria remain decisions to resolve before release.

The owner does not yet know tank/operator counts or site connectivity conditions (2026-10-16). Keep these as unknown deployment inputs, not assumed farm facts or prerequisites for software design. Under R21, define a reproducible engineering test profile and report measured capacity and recovery behavior; final site suitability must be assessed against that evidence when deployment details are available.

## 2. Current implementation baseline

- [Firmware](../firmware/main/main.c) contains sensor, control, telemetry, and display tasks, physical temperature/turbidity drivers, and default pH. Electrical operation and calibration were not tested in this audit.
- [Backend startup](../backend/main.py) creates SQLModel tables, loads PyTorch/scaler resources, and starts a Paho MQTT client with an asyncio handoff. REST and per-tank WebSocket routes exist. Authentication and ownership models do not exist.
- [Frontend routes](../frontend/src/App.jsx) provide dashboard, tanks, tank detail, alerts, and data export. Several integrations and status rules are inconsistent with the backend.
- [Inference](../backend/ml/inference.py) returns four recursively generated outputs named `hour_1` through `hour_4`. Their hourly interpretation is not verified. A stored model is evidence of an artifact, not validated forecasting performance.

The [implementation assessment](status/implementation.md) owns the detailed, dated evidence and defects. The following requirements remain targets even when the source does not satisfy them.

### T12 reading-history clarification

Owner-confirmed 2026-10-21 for R07/R09/R10; see
[decision 0009](decisions/0009-reading-history-and-manual-measurements.md).
Device captures remain immutable with their original binding and nullable capture
time. Receipt time never substitutes for capture time. Manual entries are actual
operator-reported measurements, with at least one finite temperature/pH/turbidity
value and explicit missing metrics. They do not certify calibration or biological
safety. Require a timezone-aware measurement time with a five-minute future-clock
tolerance. Estimates are not accepted through manual measurement entry.

For rebuild water-log CRUD/history below, correction, deletion and restoration
mean append-only manual revisions with expected version, actor, server time and
reason; there is no permanent reading deletion or device-event editing. Tank,
original author and receipt time remain fixed. All active hatchery operators have
equal rights. Archived tanks allow history reads but block manual writes until
restored. Reading history uses an explicit measured/received time basis and stable
snapshot pagination. T12 supplies protected backend APIs; frontend forms, history
and export retain their later milestones. Historical prototype API descriptions
below do not override these rebuild rules.

### T13 ingestion clarification

Owner-confirmed 2026-10-21 for R05–R09/R16–R18; see
[decision 0010](decisions/0010-mqtt-ingestion-and-quarantine.md). Deliver the backend
slice using generated credentials, simulated devices and an isolated test broker.
Real ESP32/HiveMQ acceptance still requires verified firmware proof, durable runtime
binding/configuration confirmation and dedicated backend broker permissions.
The test broker does not replace HiveMQ as the selected live service.

Readings enter normal history only through verified identity, retained ownership,
confirmed binding and capture-window admission. Closed bindings require synchronized
capture within [assignment start,end); unknown capture time remains null and is
admissible only under an active confirmed binding. Never rewrite queued events to
a current tank or infer capture time. Quarantine uncertain/conflicting validated
events separately, with bounded storage, without sending a success ACK. Device
queue-head retries may delay subsequent readings; no fake ACK may bypass that.

Application stored/duplicate ACKs follow successful database commit. Lost ACKs
recover through immutable event identity and retries; changed content never
overwrites history. New command results lacking authorized command context remain
quarantined until T14. Live ingestion defaults disabled; local checks do not qualify
broker/cloud, hardware, deployed capacity or T07's remaining evidence gaps.

### T13A real-device and quarantine-custody clarification

Owner-confirmed 2026-10-21; see [decision 0011](decisions/0011-real-device-onboarding-and-quarantine-custody.md).
The ESP32 must prove its credential, persist/read back its assigned configuration
and confirm its exact version before newly assigned captures are enabled. Keep
existing queued event attribution immutable. A previously confirmed saved binding
supports offline capture after reboot.

In addition to normal stored/duplicate ACKs, a separate quarantine custody receipt
may release the exact pending device copy after validated content is durably
retained in quarantine. This is not accepted tank history. Require verified device
ownership, a committed quarantine record and an exact payload hash/identity match.
No receipt follows invalid input, capacity refusal or database failure. Qualify
backend-only publication and device-scoped subscription on the actual broker.
Operator Add device screens are explicitly T18; T13A uses trusted test tooling.

### T14 relay command clarification

Owner-approved 2026-10-22; [decision 0012](decisions/0012-relay-command-lifecycle.md).
R14/R17 include protected manual ON/OFF and explicit return to AUTO. API acceptance,
publication, device acceptance/application, rejection/failure and timeout are distinct.
Commands expire after 60 seconds and retry unchanged IDs every five seconds; expiry
limits delivery rather than manual-mode duration. Timeout means unknown outcome;
late legitimate results may resolve it while preserving timeout evidence. Durable
deduplication/result ACKs and correlated relay-owner completion must prevent duplicate
actuation and false success. Reboot does not resume pending remote commands. Preserve
the T06 safety/manual/AUTO policy, unloaded hardware boundary and truthful GPIO-only
state evidence. Browser controls remain T18; T07 declined checks/BOOT deferral remain.

## 3. Requirements and acceptance criteria

**Prototype** means the current demonstration milestone. **Product** means required end-product behavior whose delivery includes unfinished prototype work. **Production** means a deployment/release gate. Stage labels organize work; they do not waive a requirement. Historical prototype account-access wording conflicted; section 1 now explicitly requires accounts and permissions for the first production-software release. Remaining security/hosting choices are tracked in Q05.

| ID | Stage | Requirement and acceptance criterion | Implementation evidence |
|---|---|---|---|
| R01 | Prototype | Use the documented XIAO ESP32-S3 target, DS18B20, analog turbidity sensor, 16x2 I2C LCD, and one active-low relay. Confirm actual wiring/electrical limits before hardware changes. Each peripheral initializes or reports a diagnosable failure. | [S01](status/implementation.md#s01-device-foundation) |
| R02 | Prototype | Maintain ESP-IDF/FreeRTOS task separation, watchdog coverage for critical tasks, independent sensing during network failure, and a boot path that does not wait indefinitely for connectivity. The recorded framework baseline is 6.0.2; compatibility must be build-verified. | [S01](status/implementation.md#s01-device-foundation) |
| R03 | Prototype | Filter temperature/turbidity noise, track validity and staleness, and distinguish failed or default readings from measurements. Detect temperature staleness after 60 seconds without a valid reading. Never imply that prototype pH is physically measured. | [S02](status/implementation.md#s02-reading-quality) |
| R04 | Prototype | Provision Wi-Fi using BLE, retain credentials in NVS, reconnect with capped backoff up to five minutes, recover from authentication failures, and provide an intentional credential-reset path. | [S03](status/implementation.md#s03-network-and-mqtt) |
| R05 | Prototype | Use HiveMQ Cloud with authenticated TLS on port 8883. Use MAC-derived device IDs, device-scoped JSON telemetry/status/command topics, QoS 1 publication, retained online status/LWT, and a 16-reading offline queue. Verify broker permissions rather than assuming them from connection success. | [S03](status/implementation.md#s03-network-and-mqtt) |
| R06 | Product | Retain the intended five-minute telemetry schedule and capture measurement time. Define sensor sampling, transmission, and model-input intervals separately; reconcile the legacy 15-minute model input contract before claiming forecast compliance. The current five-second transmission loop is a documented deviation, not a revised requirement. | [Q01](research/open-questions.md#q01-time-and-forecast-contract) |
| R07 | Prototype | Persist tank identity, device identity, temperature, pH, turbidity, pH provenance, relay state, and reading time. Keep history attributable to its tank/device; malformed data must not silently become a valid zero measurement. | [S04](status/implementation.md#s04-data-and-ingestion) |
| R08 | Prototype | Evaluate reading quality consistently using the policy in section 4. Return `optimal`, `warning`, or `critical`, explanatory warnings, and an estimated-pH flag. Stream evaluated MQTT readings to the correct tank view. | [S05](status/implementation.md#s05-quality-and-alerts) |
| R09 | Prototype | Provide FastAPI/SQLModel tank CRUD, water-log CRUD/history, tank summaries, device inspection, prediction creation/history/latest, health response, CORS configuration, and per-tank WebSocket channels. Do not advertise removed user/feeding endpoints as available. | [Architecture](reference/architecture.md#rest-and-websocket-surface) |
| R10 | Product | Provide a responsive React/Vite interface for tank overview/details, meaningful metric displays, accurate device state, visible pH provenance, historical charts, relay demonstration control, forecasts, and alerts. Manual water-log entry remains required even though the current UI lacks it. CSV export already exists as a supporting capability. | [S06](status/implementation.md#s06-browser-interface) |
| R11 | Product | Forecast only temperature, pH, and turbidity at actual 1-, 2-, 3-, and 4-hour horizons. Use 48 chronological, appropriately spaced observations with scaler normalization; reject insufficient input and define a missing/stale-data policy before release. Changing the training target requires matching artifacts and validation. | [S07](status/implementation.md#s07-forecasting) |
| R12 | Product | Persist forecasts and expose create/history/latest endpoints. Include forecast origin, target time per horizon, pH estimation/provenance, and a documented confidence indicator penalized for estimated pH. Do not present an uncalibrated heuristic as a statistical probability. | [S07](status/implementation.md#s07-forecasting) |
| R13 | Product | Maintain versioned model weights, scaler, metadata, feature order, training assumptions, and reproducible evaluation evidence. PyTorch LSTM is the selected inference family; the current architecture is described in reference material, not a proof of accuracy. | [Q03](research/open-questions.md#q03-model-provenance) |
| R14 | Prototype | Support unloaded relay ON/OFF demonstration, MQTT commands, active-low actuation, and truthful telemetry/UI state. Manual commands and automatic logic must have an explicit ownership policy. Stale temperature must force a reliable OFF state. | [S08](status/implementation.md#s08-relay-control) |
| R15 | Production | Integrate temperature-control equipment with hysteresis, anti-chatter behavior, configurable thresholds, and safe failure behavior. Retain the legacy proposed ON >=32.5 C / OFF <=31.0 C thresholds as a design requiring actuator/domain confirmation before connection; do not interpret them as approved heater behavior. | [Q04](research/open-questions.md#q04-connected-relay-equipment) |
| R16 | Product / Production | Provide owner-provisioned user accounts with one application role, operator, and equal access within each active hatchery membership. Public registration does not provision application access. Each tank/device belongs exclusively to one hatchery. A tank may have several devices; a device has at most one active tank assignment, with historical bindings retained. Operators may claim prepared devices using a private claim code and proof of the trusted device credential; device preparation occurs once before distribution. Track server assignment separately from confirmed device configuration. Archive resources while retaining ownership/history; restoration must not recreate prior assignments. Broker messages must not grant ownership solely through self-reported tank IDs. | [Ownership decision](decisions/0006-database-ownership-and-bindings.md), [Account decision](decisions/0007-operator-authentication.md), [Claiming decision](decisions/0008-self-service-device-claiming.md), [S09](status/implementation.md#s09-production-and-verification) |
| R17 | Production | Require API authentication backed by Supabase email/password and verified asymmetric JWTs, with provider tokens held server-side and opaque protected browser sessions. Enforce eight-hour absolute and 30-minute authenticated-request inactivity limits, immediate local revocation/disable, operator membership authorization, tenant isolation, validation, rate limiting, origin/CSRF protection, HTTPS/WSS, securely managed credentials, and unique per-device MQTT authentication over server-verified TLS, with a separate restricted backend identity. The owner-approved Starter path uses independent random device/backend passwords and distinct roles; certificate MQTT remains an alternative only with verified permission isolation. Device signing keys remain required for HTTPS claiming/configuration proofs. Provider refresh alone must not extend application session limits. See [decision 0011](decisions/0011-real-device-onboarding-and-quarantine-custody.md) for the approved MQTT adjustment. Production provisioning must not rely on a publicly derivable MAC-based secret. | [Account decision](decisions/0007-operator-authentication.md), [Q05](research/open-questions.md#q05-production-security-and-hosting) |
| R18 | Production | Use a containerized backend, static frontend hosting, PostgreSQL with connection pooling, automated tests/deployment, environment configuration, and operational logging/metrics/health checks. HiveMQ Cloud replaces a self-hosted broker requirement. | [S09](status/implementation.md#s09-production-and-verification) |
| R19 | Product / Production | Preserve OTA-capable layout, watchdog reset behavior, coredump capability, network recovery, and offline buffering. Production must implement the update/confirmation/rollback workflow, not just allocate partitions. The documented baseline is 8 MB flash with two 1.5 MiB OTA slots; actual hardware and binary headroom require verification. | [Q06](research/open-questions.md#q06-hardware-and-build-evidence) |
| R20 | Production | Provide durable alert history, acknowledgement, notification channels such as SMS/email, database backup/restore, and tested recovery procedures. These remain future requirements, not claims about the prototype. | [S09](status/implementation.md#s09-production-and-verification) |
| R21 | Prototype / Production | Verify API and MQTT integration using the existing test/simulator utilities after configuring an isolated environment. Add appropriate unit, firmware, end-to-end, and load/recovery tests for release. A script existing or returning success is not evidence of forecast accuracy or field reliability. | [Development guide](operations/development.md#verification-boundaries) |
| R22 | Future | Allow physical pH integration, mobile access, and multi-site management. Dissolved oxygen/ammonia are deferred expansion ideas; they are outside the current three-parameter measurement/prediction scope and need an explicit PRD revision before implementation. | [Roadmap](roadmap.md) |

## 4. Water-quality policy

Retained project policy, matching backend constants; suitability for the selected hatchery/larvae deployment and its operating conditions is unverified (Q02). Selecting that stage does not validate these numerical limits; validate or explicitly revise them before claiming hatchery production suitability.

| Metric | Optimal | Warning | Critical |
|---|---|---|---|
| Temperature | 26-32 C inclusive | Outside optimal range | No separate temperature-critical boundary is currently specified |
| pH | 7.5-8.5 inclusive | Outside optimal, within 6.5-9.0 inclusive | Below 6.5 or above 9.0 |
| Turbidity | <=50 NTU | >50 through 100 NTU | >100 NTU |

Any critical condition takes precedence over warnings. Estimated pH must remain labelled. Sensor physical-validity ranges and biological quality policy are different concepts. The alternative thresholds hard-coded in some frontend pages are implementation inconsistencies, not an additional policy.

## 5. Completion rules and unresolved decisions

Every rebuild slice or repair must identify its requirement IDs, intended behavior, bounded change, and verification evidence. Build checks establish buildability; hardware tests establish device behavior; model evaluation establishes forecast performance. No one type substitutes for another.

Open decisions are maintained in [research/open-questions.md](research/open-questions.md). Until resolved, preserve the uncertainty rather than inventing model timing, electrical calibration, stocking capacity, cloud capabilities, or production readiness. The old training recipe and framework-specific crypto claims are historical prescriptions awaiting evidence, not facts about the shipped artifacts.

The original migration and this scope reconciliation change documentation only. [Decision 0001](decisions/0001-project-baseline.md) records the existing prototype baseline; [decision 0002](decisions/0002-rebuild-direction.md) records the restart direction; [decision 0003](decisions/0003-first-production-software-release.md) records the first-release boundary. [The audit](history/2026-10-15-documentation-audit.md) records where the previous material went.
