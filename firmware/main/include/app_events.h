/**
 * @file app_events.h
 * @brief Application-level event bases and payloads for the Bangus Buhai firmware.
 *
 * Using the ESP-IDF event loop for inter-task communication is preferred over
 * polling shared variables because:
 *  - Tasks block efficiently instead of burning CPU in tight loops.
 *  - Event payload carries structured data without global variables.
 *  - Components remain decoupled — the sensor service doesn't need to know
 *    about the telemetry service; it just posts an event.
 *
 * Event bases:
 *   SENSOR_EVENTS  — posted by sensor_service when readings are ready
 *   SYSTEM_EVENTS  — posted by wifi_manager for connection state changes
 */

#pragma once

#include "esp_event.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Event bases ────────────────────────────────────────────────────────────── */
ESP_EVENT_DECLARE_BASE(SENSOR_EVENTS);
ESP_EVENT_DECLARE_BASE(SYSTEM_EVENTS);

/* ── Sensor event IDs ──────────────────────────────────────────────────────── */
typedef enum {
    SENSOR_EVENT_DATA_READY,      /**< A new filtered reading is available     */
    SENSOR_EVENT_TEMP_CRITICAL,   /**< Temperature is outside safe range       */
    SENSOR_EVENT_READ_ERROR,      /**< Both sensors failed in the same cycle   */
} sensor_event_id_t;

/* ── System event IDs ──────────────────────────────────────────────────────── */
typedef enum {
    SYSTEM_EVENT_WIFI_CONNECTED,       /**< STA got IP                          */
    SYSTEM_EVENT_WIFI_DISCONNECTED,    /**< STA lost IP or disconnected         */
    SYSTEM_EVENT_MQTT_CONNECTED,       /**< MQTT client connected to broker     */
    SYSTEM_EVENT_MQTT_DISCONNECTED,    /**< MQTT client disconnected from broker*/
} system_event_id_t;

#ifdef __cplusplus
}
#endif
