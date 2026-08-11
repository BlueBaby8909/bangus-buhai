idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_event
        esp_netif
        nvs_flash
        freertos
        log
        relay_driver
        ds18b20_sensor
        turbidity_sensor
        lcd_display
        sensor_service
        telemetry_service
        wifi_manager
)
