#pragma once

#include "esp_err.h"

/**
 * @brief Initialize the ADC OneShot unit and calibration scheme for the turbidity sensor.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t turbidity_sensor_init(void);

/**
 * @brief Read the analog voltage from the turbidity sensor.
 * 
 * @param[out] out_voltage Pointer to store the calibrated voltage in millivolts (mV).
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t turbidity_sensor_read(int *out_voltage);