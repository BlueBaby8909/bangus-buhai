# Bangus Buhai backend

FastAPI + SQLModel backend for tanks, devices, water logs, summaries, predictions, and per-tank WebSocket updates. Startup loads PyTorch/scaler resources and starts a Paho MQTT subscriber with an asyncio handoff. The device-command route uses a separate aiomqtt publisher.

- [Product requirements](../docs/PRD.md)
- [Run/configuration instructions](../docs/operations/development.md#backend)
- [Current routes and architecture](../docs/reference/architecture.md#rest-and-websocket-surface)
- [Verified source limitations](../docs/status/implementation.md)

## Entry points

- [main.py](main.py): lifecycle, router registration, CORS, application health response.
- [config.py](config.py): environment settings, including a working-directory-relative `.env`.
- [database/db.py](database/db.py): engine/session and table creation; default SQLite data location.
- [services/mqtt_subscriber.py](services/mqtt_subscriber.py): device ingestion, evaluated readings, automatic prediction attempts, WebSocket broadcasts.
- [services/water_quality.py](services/water_quality.py): implemented status evaluation. Normative policy is maintained only in the PRD.
- [ml/inference.py](ml/inference.py): model/scaler loading and recursive forecast generation.

User/feeding routes and ownership fields described in older READMEs were removed. This API currently has no authentication or device-claiming workflow. Source presence does not establish reliable command transport, correct hourly forecast semantics, or production readiness. The status document records these gaps.

The existing `mass_test.py` and `mock_device.py` utilities create data or publish messages. Read the development guide before running them; this migration did not execute them.
