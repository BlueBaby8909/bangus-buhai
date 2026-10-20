#pragma once

#include "esp_err.h"

esp_err_t turbidity_sensor_init(void);

esp_err_t turbidity_sensor_read(int *outvoltage_mv);