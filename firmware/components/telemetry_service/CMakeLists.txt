idf_component_register(
    SRCS "src/telemetry_service.c"
    INCLUDE_DIRS "include"
    REQUIRES
        mqtt
        wifi_manager
        esp_wifi
        esp_event
        esp_timer
        freertos
        nvs_flash
        cjson
        log
        esp_hw_support
        relay_driver
    PRIV_REQUIRES
        main
)

# --------------------------------------------------------------------------
# Embed the broker CA certificate as a binary symbol.
#
# Place your Mosquitto CA certificate at:
#   firmware/components/telemetry_service/certs/mosquitto_ca.crt
#
# The cert is embedded into the firmware binary and referenced in
# telemetry_service.c as:
#   extern const uint8_t mosquitto_ca_cert_pem_start[];
#   extern const uint8_t mosquitto_ca_cert_pem_end[];
#
# For local development without TLS, create a placeholder empty file so the
# build succeeds, and set CONFIG_BB_MQTT_USE_TLS=n in sdkconfig.
# --------------------------------------------------------------------------
set(CERT_FILE "${CMAKE_CURRENT_SOURCE_DIR}/certs/mosquitto_ca.crt")
if(NOT EXISTS "${CERT_FILE}")
    message(WARNING
        "Broker CA cert not found at ${CERT_FILE}. "
        "Creating placeholder — TLS will not work until you add the real cert. "
        "Set CONFIG_BB_MQTT_USE_TLS=n for non-TLS development.")
    file(WRITE "${CERT_FILE}" "# placeholder\n")
endif()

target_add_binary_data(${COMPONENT_LIB} "certs/mosquitto_ca.crt" TEXT)
