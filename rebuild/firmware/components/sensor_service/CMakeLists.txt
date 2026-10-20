idf_component_register(
    SRCS "src/sensor_service.c" "src/sensor_service_clock.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_timer freertos ds18b20_sensor turbidity_sensor
)
