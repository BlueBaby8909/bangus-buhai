idf_component_register(
    SRCS "src/relay_driver.c"
    INCLUDE_DIRS "include"
    REQUIRES "driver" "esp_driver_gpio"
)