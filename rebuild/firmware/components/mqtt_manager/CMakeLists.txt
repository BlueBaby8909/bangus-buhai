idf_component_register(
    SRCS "src/mqtt_manager.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_common
    PRIV_REQUIRES espressif__mqtt esp_event esp_netif esp_hw_support esp_timer mbedtls log freertos telemetry esp_app_format device_setup command_manager
)

set(BB_MQTT_CERT_DIR "$ENV{USERPROFILE}/BangusBuhai-Secrets/t07" CACHE PATH
    "External per-device MQTT certificate and private key")
foreach(cert_file device-cert.pem device-key.pem)
    if(NOT EXISTS "${BB_MQTT_CERT_DIR}/${cert_file}")
        message(FATAL_ERROR "Missing ${cert_file}; set BB_MQTT_CERT_DIR to the external device credential directory")
    endif()
endforeach()

target_add_binary_data(${COMPONENT_LIB}
    "${BB_MQTT_CERT_DIR}/device-cert.pem" TEXT RENAME_TO mqtt_device_cert)
target_add_binary_data(${COMPONENT_LIB}
    "${BB_MQTT_CERT_DIR}/device-key.pem" TEXT RENAME_TO mqtt_device_key)
# device_setup references this archive member even when MQTT uses a password.
# Force resolution independently of static-library ordering.
target_link_libraries(${COMPONENT_LIB} INTERFACE "-u mqtt_device_key")

set(BB_MQTT_AUTH_MODE "certificate" CACHE STRING "MQTT certificate or password authentication")
if(BB_MQTT_AUTH_MODE STREQUAL "password")
    set(BB_MQTT_LOGIN_DIR "$ENV{USERPROFILE}/BangusBuhai-Secrets/t13a/mqtt-login" CACHE PATH "Private MQTT login material")
    if(NOT EXISTS "${BB_MQTT_LOGIN_DIR}/device_mqtt_login.h")
        message(FATAL_ERROR "Prepare private MQTT login material before building password mode")
    endif()
    target_include_directories(${COMPONENT_LIB} PRIVATE "${BB_MQTT_LOGIN_DIR}")
    target_compile_definitions(${COMPONENT_LIB} PRIVATE BB_MQTT_PASSWORD_AUTH=1)
elseif(NOT BB_MQTT_AUTH_MODE STREQUAL "certificate")
    message(FATAL_ERROR "Unsupported BB_MQTT_AUTH_MODE")
endif()

option(BB_T13A_CUSTODY_EXERCISE "One local-lab diagnostic unknown-binding event per boot" OFF)
if(BB_T13A_CUSTODY_EXERCISE)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE BB_T13A_CUSTODY_EXERCISE=1)
endif()
