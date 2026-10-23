set(setup_sources "src/configuration.c" "src/security.c")
if(NOT BB_SETUP_TEST_ONLY)
    list(APPEND setup_sources "src/client.c")
endif()
idf_component_register(SRCS ${setup_sources} INCLUDE_DIRS "include"
    REQUIRES esp_common
    PRIV_REQUIRES telemetry espressif__cjson nvs_flash esp_hw_support mbedtls
                  esp_http_client esp_netif esp_timer freertos log)
if(NOT BB_SETUP_TEST_ONLY)
    set(BB_DEVICE_SETUP_DIR "$ENV{USERPROFILE}/BangusBuhai-Secrets/t13a" CACHE PATH "Private LAN setup material")
    foreach(material backend-ca.pem device_setup_material.h)
        if(NOT EXISTS "${BB_DEVICE_SETUP_DIR}/${material}")
            message(FATAL_ERROR "Missing T13A setup material: prepare it with backend.features.registry.lab")
        endif()
    endforeach()
    target_include_directories(${COMPONENT_LIB} PRIVATE "${BB_DEVICE_SETUP_DIR}")
    target_add_binary_data(${COMPONENT_LIB} "${BB_DEVICE_SETUP_DIR}/backend-ca.pem" TEXT RENAME_TO setup_backend_ca)
endif()
