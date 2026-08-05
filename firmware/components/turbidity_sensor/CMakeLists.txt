idf_component_register(
    SRCS "src/turbidity_sensor.c"
    INCLUDE_DIRS "include"
    REQUIRES "esp_adc" "log" "esp_timer"
)