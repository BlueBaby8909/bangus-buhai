idf_component_register(SRCS "src/command_manager.c" INCLUDE_DIRS "include"
    REQUIRES esp_common relay_control
    PRIV_REQUIRES telemetry espressif__cjson nvs_flash esp_hw_support esp_timer log mbedtls)
