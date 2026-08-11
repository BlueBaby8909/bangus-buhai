/**
 * @file sensor_service.h
 * @brief Sensor aggregation service for Bangus Buhai firmware.
 *
 * This service reads all physical sensors, applies EMA filtering, validates
 * ranges, and exposes the results in a thread-safe, structured form.
 *
 * Physical sensors (what the hardware actually measures):
 *   - Temperature  (DS18B20, °C)
 *   - Turbidity    (analog sensor, NTU)
 *
 * Soft/estimated parameters (NOT measured by hardware):
 *   - pH           — fixed at CONFIG_BB_PH_DEFAULT / 100.0f for the prototype.
 *                    The ph_source field is set to "default". When a real pH
 *                    sensor is added, only sensor_service.c changes.
 *
 * All other water-quality parameters (dissolved oxygen, ammonia, etc.) are
 * derived by the ML model on the backend, NOT measured here.
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Structured output of one sensor service reading cycle.
 *
 * The ph_source field communicates to the backend and frontend whether the
 * pH value came from a physical sensor, a fixed default, or manual entry:
 *   "sensor"  — read from a real pH sensor (future hardware addition)
 *   "default" — fixed Kconfig constant, no physical sensor present
 *   "manual"  — entered by the user via the frontend app
 */
typedef struct {
    float    temperature;         /**< Filtered temperature, °C              */
    float    turbidity;           /**< Filtered turbidity, NTU               */
    float    ph;                  /**< pH value (see ph_source)              */
    char     ph_source[8];        /**< "sensor" | "default" | "manual"       */
    bool     temperature_valid;   /**< false if sensor is absent or stale    */
    bool     turbidity_valid;     /**< false if ADC read failed              */
    uint32_t timestamp_ms;        /**< esp_timer_get_time() / 1000 at read   */
    uint32_t consecutive_failures;/**< increments on each full read failure  */
} sensor_reading_t;

/**
 * @brief Initialise the sensor service (must be called after hardware inits).
 * @return ESP_OK on success.
 */
esp_err_t sensor_service_init(void);

/**
 * @brief Read all sensors, apply EMA filtering, validate ranges.
 *
 * Thread-safe. Blocks briefly while taking the internal mutex.
 * The DS18B20 conversion takes ~200 ms; callers should run this in a
 * dedicated task and vTaskDelay() between calls.
 *
 * @param[out] out  Pointer to a sensor_reading_t to fill.
 * @return ESP_OK on success, ESP_ERR_INVALID_STATE if not initialised.
 */
esp_err_t sensor_service_read(sensor_reading_t *out);

/**
 * @brief Get the most recent valid reading without triggering a new read.
 *
 * Returns the last result from sensor_service_read(). Thread-safe.
 *
 * @param[out] out  Pointer to a sensor_reading_t to fill.
 * @return ESP_OK, or ESP_ERR_NOT_FOUND if no reading has been taken yet.
 */
esp_err_t sensor_service_get_latest(sensor_reading_t *out);

/**
 * @brief Return true if the latest temperature reading is considered stale
 *        (no successful read within SENSOR_STALE_TIMEOUT_S seconds).
 *
 * Callers (e.g. control_task) must call this to decide whether to place
 * controlled equipment in a safe state.
 */
bool sensor_service_is_temperature_stale(void);

#ifdef __cplusplus
}
#endif
