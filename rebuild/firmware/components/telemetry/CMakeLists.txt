idf_component_register(
    SRCS "src/telemetry.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_common sensor_service relay_control
    PRIV_REQUIRES nvs_flash esp_hw_support espressif__cjson log mbedtls
)
