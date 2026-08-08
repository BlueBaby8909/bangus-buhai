idf_component_register(
    SRCS "src/lcd_display.c"
    INCLUDE_DIRS "include"
    REQUIRES "log" "esp_driver_i2c"
)