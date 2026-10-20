idf_component_register(
    SRCS "src/ds18b20_sensor.c"
    INCLUDE_DIRS "include"
    REQUIRES freertos log ds18b20 onewire_bus
)
