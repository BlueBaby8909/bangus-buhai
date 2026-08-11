## Context

The Bangus Buhai project is a working prototype with ESP32-S3 firmware (ESP-IDF), a FastAPI backend with async MQTT subscriber, a React/Vite frontend, and an LSTM forecasting model. See [proposal.md](proposal.md) for motivation. The codebase is functional end-to-end: sensor data flows from hardware → MQTT → backend → database → WebSocket → frontend in real time. However, no formal PRD existed prior to this change, and several areas need strengthening before the system can be considered production-ready.

### Current State Summary

| Layer | Status | Key Technology |
|-------|--------|----------------|
| Firmware | Production-grade architecture | ESP-IDF v6.0.2, FreeRTOS, 4 tasks |
| Wi-Fi | Working (BLE provisioning) | `network_provisioning` |
| MQTT | Working with TLS support | `esp-mqtt` (managed), QoS 1, LWT |
| Sensors | Temperature + Turbidity working | DS18B20 (1-Wire), ADC turbidity |
| pH | Stub (constant default 7.80) | Kconfig-configurable, `ph_source` tracked |
| Relay | Working with hysteresis | GPIO active-low, safe-state on stale sensor |
| Backend | Working | FastAPI, SQLModel, SQLite, aiomqtt |
| Frontend | Working (partial) | React 19, Vite 8, vanilla CSS |
| ML | Working (limited) | PyTorch LSTM, single 3-hour prediction |
| Mosquitto | Dockerized | Password auth, TLS-ready |

## Goals / Non-Goals

**Goals:**
- Produce the formal PRD as the authoritative source of truth for the project
- Perform a rigorous codebase gap analysis against the PRD across all layers
- Identify every gap, deficiency, and piece of technical debt
- Produce a prioritized remediation roadmap
- Clearly distinguish prototype vs. production requirements

**Non-Goals:**
- Implementing any code changes (this is planning-only)
- Rewriting or refactoring any component
- Adding new features
- Changing the existing architecture (analysis only)
- Evaluating commercial viability or pricing

## Decisions

### D1: PRD Structure — Single comprehensive spec per capability area

**Decision**: Create five spec files organized under `specs/prd/`:
- `product-requirements/spec.md` — the main PRD
- `gap-analysis/spec.md` — gap analysis methodology and findings
- `relay-control/spec.md` — relay/temperature control specification
- `ml-forecasting/spec.md` — ML prediction system specification
- `cloud-security/spec.md` — cloud, security, and deployment specification

**Rationale**: The user explicitly listed 24+ requirement areas. A single monolithic spec would be unwieldy. Splitting by capability area (per OpenSpec convention) keeps each spec focused and reviewable while maintaining the PRD as the umbrella document.

**Alternatives considered**:
- Single massive `prd/spec.md` — too large to review effectively
- Per-component split (firmware-spec, backend-spec, etc.) — cross-cutting concerns like security span multiple components; organizing by capability is better

### D2: Gap Analysis Methodology — Systematic layer-by-layer review

**Decision**: The gap analysis evaluates every file in every codebase layer against the PRD, categorizing findings into 9 categories (satisfied, partially implemented, missing, incorrect, architectural problems, security concerns, technical debt, needs redesign, prototype limitations) plus a prioritized roadmap.

**Rationale**: The user explicitly requested these exact categories. A thorough file-by-file review was conducted via subagent research of every source file in firmware, backend, frontend, and infrastructure.

### D3: ML Prediction Horizon — Multi-output model for 1–4 hours

**Decision**: The PRD specifies that the ML model MUST predict at 1, 2, 3, and 4 hour horizons. The current PyTorch LSTM model predicts only a single point 3 hours ahead. This is flagged as a gap requiring model retraining with multi-output architecture.

**Rationale**: The user explicitly requires 1–4 hour forecasting. A single 3-hour prediction doesn't satisfy the "early warning" goal — operators need to see how conditions will evolve over a range of timeframes.

**Alternatives considered**:
- Separate models per horizon — simpler but 4× training/inference cost
- Iterative/recursive prediction — lower accuracy at longer horizons due to error accumulation
- Single multi-output model — preferred; one inference call returns all 4 horizons

### D4: pH Handling — Maintain current stub architecture

**Decision**: The PRD formalizes the existing `ph_source` architecture (sensor/default/manual) as the correct approach. The pH sensor is deferred to production but the data model, telemetry format, and ML pipeline already handle it correctly.

**Rationale**: The existing implementation is architecturally sound. The `ph_source` field, confidence penalties, and frontend badges all work correctly. No redesign is needed — only hardware integration when the sensor is available.

### D5: Prototype vs. Production Distinction

**Decision**: Every requirement in the PRD is tagged as either Prototype or Production scope. The gap analysis evaluates the current codebase against Prototype requirements as "must fix now" and against Production requirements as "roadmap items."

**Rationale**: The user repeatedly emphasized distinguishing prototype from production. This prevents scope creep while ensuring nothing is forgotten.

### D6: ESP-IDF v6.0.2 Migration

**Decision**: The firmware will be migrated to ESP-IDF v6.0.2. Several components must be fetched from the ESP Component Registry (including `network_provisioning`, `esp-mqtt`, and `espressif/cjson`). Legacy drivers for I2C, RMT, ADC, and Timer Group are removed and must use new APIs. The default C library changes to Picolibc and the security stack updates to Mbed TLS v4.x and PSA Crypto.

**Rationale**: ESP-IDF v6.0.2 introduces significant breaking changes and removes legacy drivers, requiring a comprehensive migration.

### D7: PyTorch Migration for Backend Inference

**Decision**: The backend inference must migrate from Keras/TensorFlow to PyTorch. The model file will change from `.keras` to `.pt`. The PyTorch model is a BangusLSTM with a (batch, 48, 3) input and (batch, 3) output.

**Rationale**: The training pipeline uses PyTorch, so the backend must align to consume the PyTorch `.pt` state dict instead of the outdated Keras model.

## Risks / Trade-offs

### R1: ML Model Retraining Required
**Risk**: Changing from single-point to multi-horizon prediction requires retraining the LSTM model.
→ **Mitigation**: The training pipeline and data collection infrastructure already exist. The model architecture change (multi-output head) is well-understood.

### R2: Authentication Retrofitting
**Risk**: Adding OAuth2/JWT authentication to an existing API requires touching every route.
→ **Mitigation**: FastAPI's dependency injection makes this relatively clean. Use `Depends(get_current_user)` pattern.

### R3: Database Migration (SQLite → PostgreSQL)
**Risk**: Moving from SQLite to PostgreSQL may surface schema or query incompatibilities.
→ **Mitigation**: SQLModel/SQLAlchemy abstracts most differences. The schema is simple (no complex queries or stored procedures). Test with PostgreSQL early.

### R4: Gap Analysis Completeness
**Risk**: Despite thorough research, some issues may only be discovered during implementation.
→ **Mitigation**: The gap analysis includes a "prototype limitations" category specifically for items that require runtime testing to fully evaluate.

### R5: ESP-IDF v6.0.2 Breaking Changes
**Risk**: ESP-IDF v6.0.2 removes many legacy drivers and changes the default C library, causing compilation errors since compiler warnings are treated as errors by default.
→ **Mitigation**: Perform a step-by-step migration using the new driver APIs (e.g., `driver/i2c_master.h`) and add managed components via the IDF Component Manager.

### R6: PyTorch Backend Migration
**Risk**: Switching the backend inference engine from Keras to PyTorch might introduce new dependency requirements and latency changes.
→ **Mitigation**: Update the Dockerfile/requirements and validate inference time with the PyTorch model.

## Open Questions

_None — all questions were resolved through codebase research and the user's detailed requirements specification._
