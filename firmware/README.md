# Bangus Buhai ESP-IDF firmware

The active prototype firmware targets ESP32-S3 and uses ESP-IDF/FreeRTOS. The owner confirmed ESP-IDF and an unloaded demonstration relay on 2026-10-15. Board wiring, calibration, clean-build compatibility, and device behavior still require verification.

- [Product requirements](../docs/PRD.md)
- [Build/configuration/provisioning guide](../docs/operations/development.md#firmware)
- [Architecture and telemetry](../docs/reference/architecture.md)
- [Device/network/relay findings](../docs/status/implementation.md)
- [Hardware and build questions](../docs/research/open-questions.md#q06-hardware-and-build-evidence)

## Source map

- [main/main.c](main/main.c): sensor, control, telemetry, and display tasks; watchdog registration; startup.
- [components/](components/): sensor drivers/service, active-low relay driver, LCD, BLE Wi-Fi provisioning, MQTT.
- [main/Kconfig.projbuild](main/Kconfig.projbuild): board/broker/provenance configuration options.
- [sdkconfig.defaults](sdkconfig.defaults), [partitions.csv](partitions.csv): intended target/configuration and partition baseline.

Wi-Fi provisioning uses BLE in source, not SoftAP. Credentials persist in NVS. The source provides a credential-reset function, but an end-user invocation has not been verified. Broad flash erasure is not an ordinary credential-reset instruction.

Keep `components/telemetry_service/certs/mosquitto_ca.crt`; it is embedded by the ESP-IDF build despite its historical filename. The retired Arduino implementation and self-hosted broker configuration are no longer active alternatives.
