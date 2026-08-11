## 1. PRD Finalization

- [ ] 1.1 Review and validate the product-requirements spec against all user requirements (24 areas listed in the request)
- [ ] 1.2 Ensure every requirement clearly distinguishes prototype vs. production scope
- [ ] 1.3 Validate water quality thresholds against SEAFDEC/BFAR milkfish aquaculture guidelines
- [ ] 1.4 Confirm hardware pin assignments match XIAO ESP32-S3 physical wiring

## 2. Firmware Gap Analysis

- [ ] 2.1 Verify FreeRTOS task architecture against PRD (priorities, core affinity, intervals, watchdog)
- [ ] 2.2 Verify Wi-Fi provisioning implementation matches PRD (BLE vs. SoftAP, security level, reconnection)
- [ ] 2.3 Verify MQTT implementation against PRD (topic format, QoS, LWT, TLS, auth, ring buffer)
- [ ] 2.4 Verify sensor drivers against PRD (DS18B20, turbidity ADC, pH stub, EMA filtering)
- [ ] 2.5 Verify relay control against PRD (hysteresis thresholds, safe state, GPIO config)
- [ ] 2.6 Verify telemetry payload format against PRD (all required fields present)
- [ ] 2.7 Verify LCD display behavior against PRD
- [ ] 2.8 Verify device identity generation (MAC-based) against PRD
- [ ] 2.9 Check for missing relay status in telemetry payload
- [ ] 2.10 Check for missing relay control command topic subscription
- [ ] 2.11 Check for OTA implementation (partition layout exists but no OTA code)
- [ ] 2.12 Review sdkconfig.defaults and Kconfig for production readiness
- [ ] 2.13 Verify ESP-IDF v6.0.2 compatibility: check that wifi_provisioning, esp-mqtt, and cJSON are migrated to managed components
- [ ] 2.14 Verify legacy driver migration: RMT (DS18B20), ADC (turbidity), I2C (LCD) must use new v6.0 APIs
- [ ] 2.15 Verify TLS/crypto stack compatibility with Mbed TLS v4.x and PSA Crypto API
- [ ] 2.16 Verify Picolibc compatibility (default C library changed from Newlib)

## 3. Backend Gap Analysis

- [ ] 3.1 Verify API endpoints against PRD (CRUD for all resources, predictions, devices)
- [ ] 3.2 Verify MQTT subscriber against PRD (topic subscriptions, payload parsing, error handling)
- [ ] 3.3 Verify WebSocket implementation against PRD (per-tank channels, real-time broadcasts)
- [ ] 3.4 Verify database schema against PRD (all models, relationships, indexes)
- [ ] 3.5 Verify water quality evaluation against PRD thresholds
- [ ] 3.6 Check for missing API authentication (OAuth2/JWT)
- [ ] 3.7 Check for deprecated datetime.utcnow() usage (should use datetime.now(UTC))
- [ ] 3.8 Check for missing MQTT TLS implementation in subscriber
- [ ] 3.9 Check database suitability (SQLite vs. PostgreSQL for production)
- [ ] 3.10 Review device auto-registration security implications
- [ ] 3.11 Check for missing alert history and notification channels
- [ ] 3.12 Check for missing rate limiting on API endpoints

## 4. Frontend Gap Analysis

- [ ] 4.1 Verify dashboard and tank detail views against PRD
- [ ] 4.2 Verify WebSocket real-time updates against PRD
- [ ] 4.3 Verify water quality gauges and status badges against PRD
- [ ] 4.4 Check for missing relay control UI
- [ ] 4.5 Check for missing ML prediction display/visualization
- [ ] 4.6 Check for missing historical chart/trend visualization
- [ ] 4.7 Check for missing alerts page or notification display
- [ ] 4.8 Check for missing device management/administration page
- [ ] 4.9 Review responsive design and mobile compatibility
- [ ] 4.10 Check for missing SEO and accessibility features

## 5. ML Pipeline Gap Analysis

- [ ] 5.1 Verify PyTorch LSTM model architecture against PRD (BangusLSTM: LSTM(3,128)→LSTM(128,64)→Linear(64,32)→Linear(32,3))
- [ ] 5.2 Check prediction horizon: current single 3-hour point (FORECAST_HORIZON=12 at 15-min intervals) vs. required 1–4 hour multi-horizon
- [ ] 5.3 Verify data preprocessing pipeline (MinMaxScaler, 48-step sequence, feature order: Temperature, pH, Turbidity)
- [ ] 5.4 Verify confidence scoring logic (pH estimation penalty)
- [ ] 5.5 Verify training pipeline in teammate's repo (github.com/apaolol/bangus-ml)
- [ ] 5.6 Verify prediction service endpoint and response format
- [ ] 5.7 Check model artifact versioning and management (.pt state dict + scaler.pkl + metadata.json)
- [ ] 5.8 **CRITICAL**: Backend inference migration from Keras/TensorFlow to PyTorch (current backend uses old Keras model)
- [ ] 5.9 Verify alignment between training notebook outputs and backend inference code expectations

## 6. Infrastructure Gap Analysis

- [ ] 6.1 Verify Mosquitto configuration against PRD (ports, auth, TLS, ACL)
- [ ] 6.2 Check for missing MQTT ACL rules
- [ ] 6.3 Verify Docker setup for broker
- [ ] 6.4 Check for missing backend/frontend containerization
- [ ] 6.5 Check for missing CI/CD pipeline
- [ ] 6.6 Check for missing cloud deployment configuration
- [ ] 6.7 Check for missing monitoring/logging infrastructure
- [ ] 6.8 Check for missing database backup strategy

## 7. Security Gap Analysis

- [ ] 7.1 Review firmware credential storage (NVS, Kconfig)
- [ ] 7.2 Review MQTT authentication and TLS configuration
- [ ] 7.3 Check for MQTT password in default sdkconfig (security risk)
- [ ] 7.4 Review Wi-Fi provisioning security level
- [ ] 7.5 Check for missing API authentication
- [ ] 7.6 Check for missing CORS hardening for production
- [ ] 7.7 Review input validation coverage across all endpoints
- [ ] 7.8 Check for sensitive data exposure in logs or responses

## 8. Gap Analysis Report Assembly

- [ ] 8.1 Compile all findings into the 9 categories (satisfied, partially implemented, missing, incorrect, architectural, security, tech debt, redesign needed, prototype limitations)
- [ ] 8.2 Create the prioritized remediation roadmap
- [ ] 8.3 Identify critical-path items that block production readiness
- [ ] 8.4 Document quick wins (easy fixes with high impact)
- [ ] 8.5 Produce the final gap analysis deliverable
