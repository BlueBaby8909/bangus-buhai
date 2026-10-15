# Implementation assessment

Rebuild context (2026-10-16): this is the existing-code assessment, not rebuild progress or a reuse decision. See [decision 0002](../decisions/0002-rebuild-direction.md) and the [active roadmap](../roadmap.md).

Source review: 2026-10-15. Baseline: `785e08b` plus existing cleanup. No application code, hardware, broker configuration, or data was changed for this assessment. Source links establish implementation presence and identified mismatches, not successful end-to-end validation. Related requirements are defined only in the [PRD](../PRD.md).

## S01 Device foundation

**Present in source; build/hardware unverified.** Four tasks, critical-task watchdog registration, peripheral initialization, non-blocking network orchestration, GPIO relay driver, and LCD output exist in [main.c](../../firmware/main/main.c). [Dependencies](../../firmware/main/idf_component.yml) and the local ignored dependency lock record managed components/ESP-IDF 6.0.2; a clean build and electrical compatibility were not tested. No production-grade claim is justified by source structure alone. PRD: R01-R02, R19.

## S02 Reading quality

**Partial.** [Sensor service](../../firmware/components/sensor_service/src/sensor_service.c) implements filtering, validity flags, held values on failure, and staleness. Its internal timestamp/flags are not serialized by [telemetry](../../firmware/components/telemetry_service/src/telemetry_service.c). Uninitialized readings can be represented by zero/held values without downstream validity. The turbidity conversion multiplies voltage by 2.28; the comment about a measured clear-water baseline is not independently verified calibration. Physical pH is absent and firmware reports a default source. Frontend source has no explicit `ph_source`/`ph_is_estimated` presentation. PRD: R03, R07, R10.

## S03 Network and MQTT

**Present with gaps.** [Wi-Fi manager](../../firmware/components/wifi_manager/src/wifi_manager.c) uses BLE security 1, MAC-derived name/PoP, NVS, reconnect backoff, and a reset function. User-facing invocation of reset, security of the PoP, and reconnection behavior need testing. [Device MQTT](../../firmware/components/telemetry_service/src/telemetry_service.c) has authenticated TLS options, retained status/LWT, a command subscriber, QoS 1 telemetry, and a 16-reading RAM queue; oldest data is overwritten at capacity. Queue ordering under failures and loss across reboot remain limitations to assess.

[Backend subscriber](../../backend/services/mqtt_subscriber.py) uses Paho with `loop_start()` and asyncio handoff, not an exclusively aiomqtt subscriber. Its first-connect failure is caught before starting the network loop; do not assume initial-failure recovery. Subscribe calls do not request QoS 1 explicitly. [Command route](../../backend/routes/device_routes.py) creates a separate aiomqtt client without applying `mqtt_use_tls`/a TLS context, unlike the subscriber. The subscriber's separate publish helper is not called by this route. HiveMQ account ACLs, certificate trust, and device connection success are unverified in this audit. PRD: R04-R06, R17.

## S04 Data and ingestion

**Present with correctness gaps.** Models, CRUD, summaries, and default SQLite exist. [Ingestion](../../backend/services/mqtt_subscriber.py) accepts raw dictionaries, substitutes missing temperature/turbidity with zero, overwrites device/tank association from payloads, and timestamps records at receipt. Sequence numbers are ignored; duplicate protection and capture-time preservation are absent. Exceptions in coroutines scheduled through `run_coroutine_threadsafe` are not inspected by the callback.

[Database setup](../../backend/database/db.py) calls `create_all`; no schema migration framework or explicit SQLite foreign-key pragma is present. [Tank deletion](../../backend/services/tank_services.py) deletes water logs and predictions but does not clear/remove associated devices. Its capacity calculation also contradicts the nearby comment; the intended units/formula are unresolved in Q07. [Log listing](../../backend/services/waterlog_services.py) has pagination without explicit chronological order.

[WebSocket manager](../../backend/services/websocket_manager.py) has a device-to-tank registration method with no callers in source, so status broadcasts have no populated routing map. Connections are in process memory; multi-worker delivery is not established. Manual REST log creation does not broadcast or trigger inference. PRD: R07-R09, R16.

## S05 Quality and alerts

**Backend policy present; UI inconsistent.** [Backend evaluation](../../backend/services/water_quality.py) implements the PRD's retained quality policy, severity precedence, warnings, and an estimated-pH flag. [Tanks](../../frontend/src/pages/Tanks.jsx) and [Alerts](../../frontend/src/pages/Alerts.jsx) independently apply different thresholds. Alerts constructs an on-load list from summaries/devices/forecasts; no alert table, acknowledgement endpoint, notification service, or alert-history persistence was found. Biological authority of any thresholds is unverified. PRD: R08, R20.

## S06 Browser interface

**Present with integration defects.** [Router](../../frontend/src/App.jsx) exposes five pages. Dashboard displays the first tank rather than a full tank-grid overview. Tank listing, create/edit/delete modals, tank-detail charts/forecasts, prediction history, alert summaries, and CSV export exist. Responsive classes exist, but accessibility and viewport behavior were not tested.

[Dashboard](../../frontend/src/pages/Dashboard.jsx) and [Alerts](../../frontend/src/pages/Alerts.jsx) match device row IDs against nonexistent `tank.device_id`; tank detail/list instead use `Device.tank_id`. [Tank detail](../../frontend/src/pages/TankDetail.jsx) sends numeric `device.id` to a string-ID command endpoint. Its initial 48-log history reverses an unsorted API result, which does not establish latest chronological history. Dashboard/detail sockets have no explicit reconnect logic. No manual log-entry form or visible estimated-pH treatment is present.

[Export](../../frontend/src/pages/DataExport.jsx) fetches at most 100 rows in one request and exports those loaded rows. Backend ordering does not guarantee the advertised "100 most recent". Do not call it a complete-history export. PRD: R09-R10, R14.

## S07 Forecasting

**PyTorch integration present; horizon accuracy unverified.** [Inference](../../backend/ml/inference.py) loads a bundled checkpoint/scaler, normalizes 48 observations, and generates four recursive outputs. It does not use elapsed timestamps to determine a step or read metadata to enforce horizon 12. [Prediction service](../../backend/services/prediction_service.py) checks count, sorts by time, persists four named horizons, and assigns 0.8 confidence when any pH source is not `sensor`, otherwise 1.0. This is an uncalibrated heuristic.

[Response model](../../backend/models/prediction.py) lacks per-horizon target timestamps and an estimated-pH flag requested by the old specification. Metadata-reported metrics cannot establish performance on this prototype. Training code/data, sampling interval, hyperparameters, artifact provenance, retraining needs, and 1-4-hour validity require external evidence. The earlier session observed a scaler-version warning at startup; no compatibility experiment was repeated in this audit. PRD: R06, R11-R13.

## S08 Relay control

**Demonstration confirmed by owner; source paths disagree.** [Control task](../../firmware/main/main.c) stores a task-local relay state; [MQTT command handling](../../firmware/components/telemetry_service/src/telemetry_service.c) changes [driver state](../../firmware/components/relay_driver/src/relay_driver.c) directly. A manual ON can leave the task-local state false, bypassing the conditional stale-state OFF branch. Automatic hysteresis remains active despite the demonstration scope, and no explicit manual/automatic mode arbitration exists. Thresholds are constants in `main.c`, not Kconfig options as the old relay spec required. GPIO and telemetry paths exist; the browser/API issues in S03/S06 block a claim of working end-to-end control. No actuator is connected to the load side. PRD: R14-R15.

## S09 Production and verification

**Not implemented or not verified.** [Current models](../../backend/models/) and [route registration](../../backend/main.py) contain no users, owners, login, RBAC, or claiming flow. Input typing/pagination constraints exist, but comprehensive domain validation, rate limiting, and authorization are absent. CORS permits broad private-network origins. The health endpoint returns a constant response.

[Partitions](../../firmware/partitions.csv) reserve OTA/coredump/storage regions and [defaults](../../firmware/sdkconfig.defaults) enable rollback/watchdog-related options; no OTA download/confirmation/rollback application workflow was found. Partition comments are not proof of rollback behavior or actual flash capacity.

No backend/frontend container definitions, CI pipeline, production deployment manifest, backup/restore procedure, or configured automated unit/E2E runner was found. [mass_test.py](../../backend/mass_test.py) and [mock_device.py](../../backend/mock_device.py) are manual utilities with mutations/external messaging. Tests were not run, devices were not flashed, and production cloud capability/security settings were not inspected. PRD: R16-R22.
