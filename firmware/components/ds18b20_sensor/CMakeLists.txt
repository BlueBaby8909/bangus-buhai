idf_component_register(
    SRCS "src/ds18b20_sensor.c"
    INCLUDE_DIRS "include"
    REQUIRES "log" "esp_timer" "driver" "ds18b20" "onewire_bus"
)