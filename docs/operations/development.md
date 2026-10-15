# Development and verification guide

Source-reviewed: 2026-10-15. Run commands from the repository, which is the nested `bangus-buhai` folder, not its parent workspace. Existing dependency folders are local artifacts; fresh installation reproducibility is unverified. These commands document existing entry points and were not run during this migration.

## Backend

Existing Windows environment:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

For a new environment, install a compatible Python runtime first, then:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

No Python version constraint or pinned backend dependency lock is declared. Model metadata records an older training environment, which is not a runtime compatibility guarantee. Startup imports models, creates missing tables, loads the checkpoint/scaler, and connects to MQTT. Keep the trusted local artifacts present; do not import the application merely to inspect documentation in a read-only audit. `create_all` does not migrate existing tables.

Run from `backend/` so [settings](../../backend/config.py) reads that directory's ignored `.env`. Configure these keys locally; do not copy credentials into documentation:

```dotenv
MQTT_BROKER_HOST=<your HiveMQ Cloud hostname>
MQTT_BROKER_PORT=8883
MQTT_USE_TLS=true
MQTT_USERNAME=<broker username>
MQTT_PASSWORD=<broker password>
MQTT_TOPIC_PREFIX=bangusbuhai
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Those are configuration examples, not checked-in credentials or claims that all code paths honor TLS. The device-command route has a recorded TLS gap. `DATABASE_URL` is optional; when unset, [db.py](../../backend/database/db.py) uses `backend/database/bangusbuhai.db`. A supplied relative SQLite URL resolves relative to the process working directory. Preserve existing data; use an isolated database for mutation tests.

API docs: <http://127.0.0.1:8000/docs>. Health response: <http://127.0.0.1:8000/health>. The health handler is not a dependency-readiness probe. Existing API paths are listed in [architecture](../reference/architecture.md#rest-and-websocket-surface).

## Frontend

From a separate terminal at the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Skip `npm ci` when using an existing working dependency installation. It replaces `node_modules`; do not use it while relying on a running development server. The manifest declares no Node engine constraint; select a runtime compatible with the locked build tools and verify it before claiming a reproducible fresh setup.

The [API client](../../frontend/src/api/client.js) reads `VITE_API_URL`, or defaults to the browser's protocol/hostname on port 8000. Set it in an ignored `frontend/.env` when needed; [the example](../../frontend/.env.example) uses localhost. WebSocket scheme selection follows the page protocol. A production HTTPS deployment needs reviewed API/WSS routing; this default is not a production deployment design.

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run preview
```

These scripts exist in [package.json](../../frontend/package.json). Build recreates ignored `dist/`. Passing lint/build alone does not establish UI functionality, accessibility, or model validity.

## Firmware

Use the configured ESP-IDF environment; verify `idf.py --version` succeeds before building. The documented baseline is ESP32-S3/ESP-IDF 6.0.2, supported by source configuration and a local ignored dependency lock. The toolchain was not executed or compatibility-certified during migration.

```powershell
cd firmware
idf.py build
```

Confirm board revision, GPIO wiring, voltage limits, flash/partition configuration, and serial port before any flash/monitor step. Keep `sdkconfig`, `sdkconfig.old`, `dependencies.lock`, model resources, and existing binaries until the baseline is reproducible. Do not infer actual hardware from a generated configuration alone.

Configure the broker URI, topic prefix, credentials, and TLS through the existing Kconfig/sdkconfig mechanism. Checked-in defaults target a local non-TLS broker, so defaults alone do not configure HiveMQ. Preserve `components/telemetry_service/certs/mosquitto_ca.crt`: the build embeds it despite its historical name. Its suitability for the configured broker still needs certificate verification.

Provisioning behavior is described by [wifi_manager.c](../../firmware/components/wifi_manager/src/wifi_manager.c): BLE security 1; default device name prefix `BB-SETUP` plus the last three MAC bytes; PoP from the last four MAC bytes; credentials retained in NVS. The source logs instructions for the ESP BLE Provisioning app. Mobile-app compatibility and the actual provisioning flow were not tested here. The MAC-derived PoP is a prototype mechanism, not a production security guarantee.

The reset function exists but no verified user-facing reset control is documented. The previous `idf.py erase-flash` instruction erases flash broadly, not only Wi-Fi credentials; it is not an ordinary startup or cleanup step.

## Verification boundaries

- [mass_test.py](../../backend/mass_test.py) sends mutating HTTP requests, creates a tank/logs/prediction, and checks response/count behavior. It is not a model-accuracy test and was not run for migration.
- [mock_device.py](../../backend/mock_device.py) publishes MQTT traffic with local-broker defaults and subscribes to `/command`, while the active command topic is `/cmd`. Its configuration and behavior need repair before it is treated as a faithful simulator. Do not publish it to the real broker as a read-only check.
- No configured automated unit/E2E/firmware runner was found. Backend package requirements are unpinned; the requirements comment incorrectly describes an exclusively aiomqtt subscriber. This migration documents that discrepancy without changing code/manifests.
- Future validation should use isolated data/broker resources and clearly distinguish source review, successful build, runtime integration, hardware tests, and model evaluation. See the [roadmap](../roadmap.md).
