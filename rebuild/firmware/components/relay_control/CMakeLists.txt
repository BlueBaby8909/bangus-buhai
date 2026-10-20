idf_component_register(
    SRCS "src/relay_control.c"
    INCLUDE_DIRS "include"
    REQUIRES relay_driver sensor_service freertos esp_timer log
)
