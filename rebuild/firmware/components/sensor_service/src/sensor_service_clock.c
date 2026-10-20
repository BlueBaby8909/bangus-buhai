#include "sensor_service_clock.h"
#include "esp_timer.h"

int64_t sensor_service_uptime_ms(void)
{
    return esp_timer_get_time() / 1000;
}
