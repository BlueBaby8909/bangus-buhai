# Bangus Buhai

An ESP32 tank-monitoring prototype for bangus (milkfish), with a FastAPI backend, a React dashboard, and PyTorch forecasting code. The active firmware is ESP-IDF; the selected MQTT broker is HiveMQ Cloud. The relay is an unloaded demonstration device, as confirmed by the project owner on 2026-10-15.

The **[PRD](docs/PRD.md)** is the authoritative product specification. Start at **[CONTEXT.md](CONTEXT.md)** for the rebuild workspace, or the **[documentation index](docs/README.md)** for existing architecture, current limitations, and development instructions. The owner has chosen a rebuild; the source described below remains the existing implementation, not an approved replacement design. Features present in source are not automatically verified or production-ready.

For Obsidian and the shared AI workflow, follow the **[workspace guide](docs/operations/ai-workspace.md)**.

## Run the current application

Run these in separate PowerShell terminals, starting in this repository:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173/>; API documentation is at <http://127.0.0.1:8000/docs>. These commands assume dependencies and the backend environment are already configured. See the [development guide](docs/operations/development.md) for installation and configuration. Backend startup creates database tables and connects to the configured broker; this is not a read-only operation.

## Source map

- [firmware/](firmware/README.md): FreeRTOS tasks, sensors, BLE provisioning, LCD, relay, MQTT.
- [backend/](backend/README.md): REST API, persistence, MQTT ingestion, WebSockets, inference.
- [frontend/](frontend/README.md): dashboard, tanks, tank detail, alerts, CSV export.
- [3D_models/](3D_models/): enclosure STL assets; physical fit is not verified by the software audit.

User and feeding endpoints described in earlier documentation no longer exist. Current gaps are recorded in the [implementation assessment](docs/status/implementation.md), rather than presented as completed functionality.
