## Why

The Bangus Buhai project has reached significant prototype maturity — ESP32 firmware, backend API, frontend dashboard, MQTT telemetry pipeline, and LSTM forecasting are all functional — but it has never had a formal **Product Requirements Document (PRD)**. Without a single source of truth, decisions are scattered across conversations, code comments, and implicit assumptions. This creates risk as the project moves from prototype toward a **commercially ready, cloud-deployable IoT product**. A formal PRD and gap analysis are needed now to:

1. Lock down the system scope (temperature, pH, turbidity monitoring with 1–4 hour forecasting).
2. Distinguish **prototype** from **production** requirements so nothing is forgotten.
3. Identify gaps, incorrect implementations, and technical debt before committing to further development.

## What Changes

- **New capability: Product Requirements Document (PRD)** — A comprehensive PRD covering all system layers: hardware (XIAO ESP32-S3, DS18B20, turbidity sensor, pH stub, relay, LCD), ESP-IDF firmware, MQTT/IoT architecture, Wi-Fi provisioning, backend (FastAPI), frontend (React/Vite), ML forecasting (LSTM), alerts, security, cloud deployment, and scalability.
- **New capability: Codebase Gap Analysis** — A systematic review of every codebase layer against the PRD, identifying: requirements already satisfied, partially implemented, missing, incorrect, architectural problems, security concerns, technical debt, and a prioritized remediation roadmap.
- **New capability: Relay and Control Specification** — Formal specification of the relay control behavior for prototype (ON/OFF verification only) vs. production (temperature-control logic with heater integration).
- **New capability: ML Forecasting Specification** — Formal specification of the 1–4 hour multi-horizon forecasting requirement for temperature, pH, and turbidity (current model predicts only a single 3-hour-ahead point).
- **New capability: Cloud Deployment and Security Specification** — Formal specification of production-grade device provisioning, TLS, authentication, OTA, and cloud hosting requirements.

## Capabilities

### New Capabilities
- `prd/product-requirements`: Comprehensive Product Requirements Document covering all system layers, distinguishing prototype vs. production requirements.
- `prd/gap-analysis`: Codebase gap analysis comparing current implementation against the PRD, with a prioritized remediation roadmap.
- `prd/relay-control`: Relay and temperature control specification for prototype and production.
- `prd/ml-forecasting`: ML forecasting specification for 1–4 hour multi-horizon prediction of temperature, pH, and turbidity.
- `prd/cloud-security`: Cloud deployment, security, and device management specification.

### Modified Capabilities
_(none — no existing specs)_

## Impact

- **All codebase layers** — firmware, backend, frontend, ML pipeline, infrastructure — will be evaluated against the new PRD.
- **Architecture** — The gap analysis may reveal structural changes needed in the MQTT topic design, database schema, ML pipeline, or firmware task architecture.
- **Dependencies** — No code changes in this proposal; this is a planning-only change that produces documentation artifacts.
- **Downstream** — The gap analysis roadmap will drive all subsequent implementation work.
