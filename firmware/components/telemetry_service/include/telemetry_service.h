/**
 * @file telemetry_service.h
 * @brief MQTT telemetry service for Bangus Buhai firmware.
 *
 * Responsibilities:
 *  - Connects to the configured MQTT broker (TLS, username/password auth).
 *  - Publishes sensor telemetry as structured JSON.
 *  - Subscribes to the device command topic for remote control.
 *  - Publishes a Last Will Testament (LWT) so the backend detects unexpected
 *    disconnects without a separate heartbeat.
 *  - Buffers up to TELEMETRY_QUEUE_DEPTH readings locally when MQTT is
 *    disconnected, and drains the queue on reconnection.
 *
 * The JSON payload schema for telemetry is:
 * {
 *   "device_id":  "BB-AABBCC112233",      ← derived from MAC
 *   "tank_id":    1,
 *   "seq":        42,                      ← monotonic sequence counter
 *   "fw_version": "1.0.0",
 *   "uptime_s":   86400,
 *   "readings": {
 *     "temperature": 29.5,
 *     "turbidity":   12.3,
 *     "ph":          7.80,                 ← fixed estimate (no physical sensor)
 *     "ph_source":   "default",            ← "sensor" | "default" | "manual"
 *     "relay_on":    true                  ← true if the relay is on, false if off
 *   },
 *   "system": {
 *     "free_heap":       180000,
 *     "wifi_rssi":       -45,
 *     "mqtt_reconnects": 0
 *   }
 * }
 *
 * pH design note:
 *   The prototype omits the pH sensor. The firmware sends the fixed Kconfig
 *   default (CONFIG_BB_PH_DEFAULT / 100.0f) with ph_source = "default".
 *   When a real sensor is added later, only this file needs to change:
 *   read the sensor, pass the value in, and set ph_source = "sensor".
 */

#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Maximum number of telemetry readings buffered while MQTT is offline. */
#define TELEMETRY_QUEUE_DEPTH 16

/**
 * @brief Initialise the MQTT client and connect to the broker.
 *
 * Must be called AFTER Wi-Fi is connected (i.e., after
 * SYSTEM_EVENT_WIFI_CONNECTED has been received).
 * Does NOT call wifi_manager_init() — that is the caller's responsibility.
 *
 * @return ESP_OK on successful client creation (not yet connected to broker).
 */
esp_err_t telemetry_service_init(void);

/**
 * @brief Enqueue a sensor reading for MQTT publish.
 *
 * If the MQTT client is connected, the message is published immediately.
 * If it is disconnected, the reading is stored in a local ring buffer and
 * replayed once the connection is restored.
 *
 * @param temperature  Filtered temperature in °C.
 * @param turbidity    Filtered turbidity in NTU.
 * @param ph           pH value (estimated from Kconfig default for prototype).
 * @param ph_source    Source string: "sensor", "default", or "manual".
 * @param relay_state  The current state of the heating relay (true=on, false=off).
 * @return ESP_OK on success, ESP_ERR_NO_MEM if the queue is full.
 */
esp_err_t telemetry_service_send_data(float temperature, float turbidity,
                                      float ph, const char *ph_source, bool relay_state);

/**
 * @brief Return true if the MQTT client is currently connected to the broker.
 */
bool telemetry_service_is_mqtt_connected(void);

#ifdef __cplusplus
}
#endif
