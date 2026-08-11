idf_component_register(
    SRCS "src/sensor_service.c"
    INCLUDE_DIRS "include"
    REQUIRES
        ds18b20_sensor
        turbidity_sensor
        esp_event
        esp_timer
        freertos
        log
    PRIV_REQUIRES
        main
)
