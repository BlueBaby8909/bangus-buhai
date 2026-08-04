#ifndef APP_EVENTS_H
#define APP_EVENTS_H

#include "esp_event.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Declare Event Bases
ESP_EVENT_DECLARE_BASE(SENSOR_EVENTS);
ESP_EVENT_DECLARE_BASE(SYSTEM_EVENTS);

// Sensor Event IDs
typedef enum {
    SENSOR_EVENT_DATA_READY,      // Filtered sensor readings are available
    SENSOR_EVENT_TEMP_CRITICAL,   // Temperature outside safe range
    SENSOR_EVENT_READ_ERROR,      // Sensor hardware read failure
} sensor_event_id_t;

// System Event IDs
typedef enum {
    SYSTEM_EVENT_WIFI_CONNECTED,
    SYSTEM_EVENT_WIFI_DISCONNECTED,
} system_event_id_t;

// Payload for SENSOR_EVENT_DATA_READY
typedef struct {
    float    temperature_c;
    float    turbidity_ntu;
    float    ph_estimated;       // Will be filled with CONFIG_BB_PH_DEFAULT / 100.0
    uint32_t timestamp_ms;
    bool     temp_valid;
    bool     turbidity_valid;
} sensor_reading_t;

#ifdef __cplusplus
}
#endif

#endif // APP_EVENTS_H
