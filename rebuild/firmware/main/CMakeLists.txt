idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES log freertos esp_timer sensor_service relay_control lcd_display wifi_manager mqtt_manager bootloader_support esp_hw_support
)
