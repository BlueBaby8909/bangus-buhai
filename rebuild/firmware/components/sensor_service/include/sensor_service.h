#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

typedef enum {
    SENSOR_VALID,
    SENSOR_INVALID,
    SENSOR_MISSING,
    SENSOR_STALE,
    SENSOR_UNVERIFIED,
} sensor_validity_t;

typedef struct {
    /* Read value only when has_value is true. Invalid/missing/stale have no value. */
    float value;
    bool has_value;
    sensor_validity_t validity;
    const char *source;
    const char *unit;
    /* Boot-relative times in milliseconds; -1 means unknown (map to JSON null).
     * After failure, sample time/age still describe the last accepted sample.
     * Unverified turbidity has no known last-valid NTU age.
     */
    int64_t sample_uptime_ms;
    int64_t sample_age_ms;
    int64_t last_valid_age_ms;
    esp_err_t error;
} sensor_value_t;

typedef struct {
    /* This is uptime, not UTC. No synchronized wall clock is claimed. */
    int64_t capture_uptime_ms;
    sensor_value_t temperature;
    sensor_value_t turbidity;
    sensor_value_t ph;
} sensor_reading_t;

/* Call once at startup before starting tasks. Does not access the sensors. */
esp_err_t sensor_service_init(void);

/* Acquires both sensors independently, filters successes and copies a snapshot.
 * ESP_OK means a snapshot was produced; inspect each metric for sensor failures.
 * One sensing task owns acquisition. Initialization is retried after failure.
 * Do not call read concurrently; other tasks use the snapshot getters.
 * Hardware conversion occurs outside the short snapshot/state mutex.
 */
esp_err_t sensor_service_read(sensor_reading_t *out);

/* No acquisition: refresh ages/staleness and copy under the service mutex.
 * Before the first read, produces missing sensors and explicitly default pH.
 * Returned copies do not change when subsequent readings arrive.
 */
esp_err_t sensor_service_get_latest(sensor_reading_t *out);

/* Bounded alternative for control/display: timeout never implies healthy data. */
esp_err_t sensor_service_try_get_latest(sensor_reading_t *out, uint32_t timeout_ms);

const char *sensor_validity_name(sensor_validity_t validity);
