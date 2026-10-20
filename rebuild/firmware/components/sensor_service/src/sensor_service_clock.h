#pragma once

#include <stdint.h>

/* Private clock boundary: tests replace this without changing the RTOS clock. */
int64_t sensor_service_uptime_ms(void);
