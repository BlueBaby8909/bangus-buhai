## Purpose
This specification defines the requirements for the relay and temperature control mechanisms, covering both prototype and production implementations for the Bangus Buhai project.

## ADDED Requirements

### Requirement: Prototype Relay Control
The prototype MUST support relay ON/OFF control via GPIO, status reporting, and MQTT integration.
#### Scenario: Operating Prototype Relay
WHEN the prototype relay is operated
THEN it MUST support control via GPIO, report its status, and integrate with MQTT

### Requirement: Production Temperature Control
The production system MUST automatically control temperature with hysteresis, turning the relay ON when temperature is ≥32.5°C and OFF when ≤31.0°C.
#### Scenario: Automatic Temperature Control
WHEN the production system monitors temperature
THEN the relay MUST turn ON at ≥32.5°C and OFF at ≤31.0°C

### Requirement: Safe State Enforcement
The system MUST enforce a safe state by turning the relay OFF when the temperature sensor data is stale (>60 seconds).
#### Scenario: Stale Sensor Data
WHEN the temperature sensor data is older than 60 seconds
THEN the relay MUST be turned OFF to maintain a safe state

### Requirement: MQTT Telemetry Payload
The relay status MUST be included in the MQTT telemetry payload.
#### Scenario: Sending Telemetry
WHEN telemetry is sent via MQTT
THEN the relay status MUST be included in the payload

### Requirement: MQTT Control Commands
The system MUST support relay control commands via a dedicated MQTT topic.
#### Scenario: Receiving Control Commands
WHEN a control command is sent via the MQTT topic
THEN the system MUST support and act on the relay control command

### Requirement: Frontend Display and Control
The frontend MUST display the relay status and allow manual override.
#### Scenario: Frontend Interaction
WHEN a user interacts with the frontend
THEN they MUST see the relay status and be able to manually override the state

### Requirement: Anti-chatter Dead-band
The system MUST implement an anti-chatter hysteresis dead-band.
#### Scenario: Anti-chatter Prevention
WHEN the temperature fluctuates near threshold limits
THEN the anti-chatter hysteresis dead-band MUST prevent rapid relay toggling

### Requirement: Active-low Logic
The relay MUST use active-low logic.
#### Scenario: Relay Actuation
WHEN the relay is actuated
THEN it MUST operate using active-low logic

### Requirement: Configurable Thresholds
The relay thresholds MUST be configurable via Kconfig.
#### Scenario: Configuring Thresholds
WHEN setting system parameters
THEN the relay thresholds MUST be configurable via Kconfig
