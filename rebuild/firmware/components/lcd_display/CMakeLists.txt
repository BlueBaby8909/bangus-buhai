idf_component_register(
    SRCS "src/lcd_display.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_driver_i2c freertos esp_rom relay_control
)
