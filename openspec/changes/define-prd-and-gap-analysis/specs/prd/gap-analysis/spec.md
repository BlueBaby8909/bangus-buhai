## Purpose
This specification defines the requirements for the comprehensive codebase gap analysis process against the Product Requirements Document (PRD) for the Bangus Buhai project.

## ADDED Requirements

### Requirement: Layer Comparison
The gap analysis MUST compare every layer of the codebase against the PRD.
#### Scenario: Codebase Evaluation
WHEN the gap analysis is performed
THEN every codebase layer MUST be evaluated against the PRD

### Requirement: Finding Categorization
The gap analysis MUST categorize findings into specific categories: satisfied, partially implemented, missing, incorrect, architectural problems, security concerns, technical debt, needs redesign, or prototype limitations.
#### Scenario: Categorizing Gaps
WHEN a gap is identified
THEN it MUST be categorized into one of the predefined categories

### Requirement: Remediation Roadmap
The gap analysis MUST produce a prioritized remediation roadmap.
#### Scenario: Generating Roadmap
WHEN the gap analysis concludes
THEN it MUST produce a prioritized remediation roadmap

### Requirement: Subsystem Evaluation
The gap analysis MUST evaluate the firmware (ESP-IDF, FreeRTOS tasks, Wi-Fi, MQTT, sensors, relay, LCD, telemetry), backend (FastAPI, database, routes, services, MQTT subscriber, WebSocket), frontend (React, components, real-time, API), ML pipeline (LSTM, training, inference, data), and infrastructure (Docker, Mosquitto, deployment).
#### Scenario: Comprehensive Subsystem Evaluation
WHEN the subsystems are evaluated
THEN firmware, backend, frontend, ML pipeline, and infrastructure components MUST be included

### Requirement: Best Practices Verification
The gap analysis MUST verify each component against current best practices (e.g., ESP-IDF v6.0.2, MQTT 5.0 readiness).
#### Scenario: Checking Best Practices
WHEN components are verified
THEN they MUST be checked against current best practices

### Requirement: Document Known Gaps
The gap analysis MUST document the following known gaps as requirements for the remediation roadmap:
1. ML only predicts single 3-hour point, needs 1-4 hour horizons.
2. No API authentication (OAuth2/JWT missing).
3. No relay control UI in frontend.
4. No ML prediction display in frontend.
5. No chart/history visualization.
6. No alert history or notification channels.
7. SQLite not suitable for production (need PostgreSQL).
8. Device auto-registration is insecure for production.
9. No CI/CD pipeline.
10. No containerization for backend/frontend.
11. No unit tests, only integration tests.
12. datetime.utcnow() deprecated, should use datetime.now(UTC).
13. No MQTT ACL rules configured.
14. Relay status not included in MQTT telemetry payload.
15. No relay control command topic.
16. WiFi provisioning docstrings say SoftAP but code uses BLE.
17. No OTA implementation (only partition layout ready).
18. Backend inference code still uses Keras/TensorFlow, but the model is now PyTorch.
19. ESP-IDF v6.0.2 requires migrating several components (network_provisioning, esp-mqtt, espressif/cjson, i2c_master) to managed components.
#### Scenario: Documenting Identified Gaps
WHEN known gaps are analyzed
THEN all specified 19 gaps MUST be documented as requirements
