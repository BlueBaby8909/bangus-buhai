## Purpose
This document defines the Product Requirements for the Bangus Hatchery Monitoring and Prediction System, serving as the single source of truth for both prototype and production phases.

## ADDED Requirements

### Requirement: Product Overview
The system SHALL monitor temperature, pH, and turbidity in bangus (milkfish) hatchery tanks and MUST predict these parameters 1-4 hours ahead using ML to provide early warning of unfavorable conditions, thereby reducing larvae mortality.

#### Scenario: Monitoring and Prediction
WHEN the system is operational
THEN it MUST monitor temperature, pH, and turbidity AND predict future values 1-4 hours ahead.

### Requirement: Target Users & Multi-Tenancy
The system MUST support individual user accounts for hatchery operators, farm technicians, and aquaculture researchers. The system MUST strictly enforce multi-tenant authorization: users MUST only be able to view and control tanks and devices that they explicitly own.

#### Scenario: User Access
WHEN users interact with the system
THEN it MUST provide authenticated interfaces and strictly isolate their data from other users' data.

### Requirement: Hardware Components
The hardware MUST consist of a Seeed Studio XIAO ESP32-S3 microcontroller, DS18B20 temperature sensor (OneWire), turbidity sensor (analog, ADC), 16×2 I²C LCD display (PCF8574 backpack), and a 1-channel relay module (active-low). In the prototype, pH is estimated, but the production version SHALL include a physical pH sensor. The system SHALL measure ONLY temperature, pH, and turbidity.

#### Scenario: Hardware Initialization
WHEN the device powers on
THEN it MUST initialize the microcontroller, sensors, display, and relay module successfully.

### Requirement: ESP32 Firmware
The ESP32 firmware MUST use ESP-IDF framework (v6.0.2) and a FreeRTOS task architecture (sensor_task, control_task, telemetry_task, display_task). It SHALL implement a Task Watchdog Timer on critical tasks, EMA filtering for sensor noise, sensor staleness detection (>60s), and a non-blocking boot sequence.

#### Scenario: Firmware Execution
WHEN the firmware is running
THEN tasks MUST execute according to their priorities and frequencies AND critical tasks MUST be monitored by the watchdog timer.

### Requirement: Wi-Fi Provisioning
The device SHALL use ESP-IDF Unified Provisioning via BLE (prototype uses SoftAP/network_prov) and store credentials in NVS. It MUST support exponential backoff reconnection (up to 5 min), re-enter provisioning on auth failure, and provide factory reset capability.

#### Scenario: Network Connection Failure
WHEN the device loses Wi-Fi connection
THEN it MUST attempt to reconnect using exponential backoff up to 5 minutes.

### Requirement: MQTT and IoT Architecture
The device MUST publish telemetry with QoS 1 to `{prefix}/devices/{device_id}/telemetry` and status to `.../status` using the MAC address as Device ID. It SHALL implement Last Will and Testament, an offline ring buffer (16 messages), JSON payload format, TLS support, and username/password authentication.

#### Scenario: Offline Telemetry Storage
WHEN the MQTT broker is unreachable
THEN the device MUST buffer up to 16 telemetry messages in a ring buffer to be sent upon reconnection.

### Requirement: Device Identity & Claiming
The prototype SHALL auto-register on the first message, while the production system MUST require pre-registration with certificates/API keys. Furthermore, the production system MUST provide a secure Device Claiming workflow where a user claims a physical device by providing its MAC address and BLE Proof of Possession (PoP) PIN, thereby mapping the device to the user's account.

#### Scenario: Device Registration and Claiming
WHEN a user purchases a new device
THEN they MUST claim it using the BLE PoP PIN to establish exclusive ownership before they can view its telemetry or send it commands.

### Requirement: Telemetry and Data
The device MUST send telemetry every 5 minutes with a timestamp. The backend SHALL store records containing temperature, pH, turbidity, ph_source, device_id, and recorded_at. Thresholds MUST be defined (Temp 26-32°C optimal, pH 7.5-8.5 optimal, Turbidity ≤50 NTU optimal) and status classified as optimal, warning, or critical.

#### Scenario: Threshold Evaluation
WHEN a telemetry reading is received
THEN the system MUST classify the reading as optimal, warning, or critical based on predefined thresholds.

### Requirement: Backend System
The backend MUST use FastAPI with an async MQTT subscriber, SQLModel ORM (SQLite for prototype, PostgreSQL for production), and provide REST API endpoints and WebSocket real-time updates per tank, with CORS configuration and a health check endpoint.

#### Scenario: API Request
WHEN a client requests tank data via REST API
THEN the backend MUST return the appropriate data from the database.

### Requirement: Frontend Interface
The frontend MUST be a React + Vite SPA featuring a dashboard with tank cards, real-time tank details, water quality range gauges, device status, pH source badge, and manual logs. Production MUST also include relay control UI, ML prediction display, alerts page, and chart history.

#### Scenario: Dashboard Viewing
WHEN a user accesses the dashboard
THEN they MUST see real-time tank data, device status, and water quality gauges.

### Requirement: ML Forecasting
The system MUST predict temperature, pH, and turbidity 1, 2, 3, and 4 hours ahead using a PyTorch LSTM model taking the 48 most recent water logs (SEQ_LENGTH=48). It SHALL use scaler-based normalization, calculate a confidence score (penalized for estimated pH), store predictions, and avoid predicting additional parameters.

#### Scenario: Prediction Generation
WHEN 48 sequential readings are available
THEN the ML model MUST generate predictions for 1, 2, 3, and 4 hours ahead.

### Requirement: Alerts and Monitoring
The backend MUST evaluate thresholds on every reading and broadcast real-time warnings via WebSockets. Production SHALL add alert history, notification channels (SMS/email), and alert acknowledgment.

#### Scenario: Alert Broadcasting
WHEN a reading exceeds optimal thresholds
THEN the backend MUST broadcast a warning via WebSocket to all connected clients.

### Requirement: Relay Control
The prototype SHALL support ON/OFF control and status verification. Production MUST implement temperature-control with hysteresis (ON ≥32.5°C, OFF ≤31.0°C), fail to a safe OFF state when sensors are stale, and support MQTT status reporting and control commands.

#### Scenario: Temperature Hysteresis Control
WHEN the temperature reaches 32.5°C in production
THEN the relay MUST turn ON and stay ON until the temperature drops to 31.0°C.

### Requirement: Security
The prototype MUST support MQTT username/password and be TLS-ready. Production SHALL implement mutual TLS (mTLS) with unique per-device X.509 certificates for secure MQTT communication, secure provisioning (Curve25519 + AES-CTR), API authentication (OAuth2/JWT), multi-tenant data isolation, RBAC, and NVS credential storage.

#### Scenario: Secure Communication
WHEN the device sends data in production
THEN the communication MUST be encrypted and authenticated using mutual TLS (mTLS) with its unique X.509 client certificate.

### Requirement: Cloud Deployment
The system MUST use a dockerized Mosquitto broker (ports 1883 dev, 8883 production TLS) with Docker Compose. Production SHALL include containerized backend/frontend, CI/CD, cloud provider config, and monitoring/logging infrastructure.

#### Scenario: Service Deployment
WHEN deploying the system
THEN Docker Compose MUST start the Mosquitto broker with appropriate ports for dev or production.

### Requirement: Reliability
The firmware MUST implement OTA partition layout (ota_0/ota_1, 1.5MB each), bootloader rollback on bad firmware, a coredump partition, task watchdog with panic reset, MQTT reconnection with backoff, and offline telemetry buffering.

#### Scenario: Firmware Rollback
WHEN a new firmware update crashes repeatedly
THEN the bootloader MUST rollback to the previous working partition.

### Requirement: Scalability
The system MUST support multi-device deployments via wildcard MQTT subscriptions, map devices to tanks, and use per-tank WebSocket channels.

#### Scenario: Multi-Device Telemetry
WHEN multiple devices publish telemetry concurrently
THEN the backend MUST process them accurately via wildcard MQTT subscriptions.

### Requirement: Testing
The system MUST be tested using the mass_test.py integration script and mock_device.py MQTT simulator. Production SHALL require unit tests, firmware tests, E2E tests, and load tests.

#### Scenario: Integration Testing
WHEN running the integration test script
THEN the mock device MUST successfully simulate MQTT telemetry and the backend MUST process it.

### Requirement: Future Expansion
The system architecture SHALL allow for physical pH sensor integration (OTA), additional sensors (dissolved oxygen, ammonia), a mobile application, and multi-site management.

#### Scenario: Adding a New Sensor
WHEN a dissolved oxygen sensor is added in the future
THEN the firmware and backend architectures MUST accommodate the new parameter without major refactoring.
