    #pragma once

#include "esp_err.h"

/**
 * @brief Initialize the DS18B20 temperature sensor on the OneWire bus
 * 
 * @return ESP_OK on success, or an error code on failure
 */
esp_err_t ds18b20_sensor_init(void);

/**
 * @brief Read the current temperature from the sensor
 * 
 * @param[out] out_temperature Pointer to store the temperature in Celsius
 * @return ESP_OK on success, or an error code on failure
 */
esp_err_t ds18b20_sensor_read(float *out_temperature);