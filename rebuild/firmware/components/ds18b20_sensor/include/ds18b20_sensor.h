#pragma once

#include "esp_err.h"

esp_err_t ds18b20_sensor_init(void);

esp_err_t ds18b20_sensor_read(float *out_temperature);