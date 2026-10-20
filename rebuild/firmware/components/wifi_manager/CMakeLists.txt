idf_component_register(
    SRCS "src/wifi_manager.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_wifi esp_event esp_netif nvs_flash
    PRIV_REQUIRES log freertos esp_timer esp_hw_support protocomm
                  espressif__network_provisioning console bt
)

set(BB_WIFI_SETUP_DIR "$ENV{USERPROFILE}/BangusBuhai-Secrets/t07" CACHE PATH
    "Private per-device BLE setup material, outside the repository")
if(NOT EXISTS "${BB_WIFI_SETUP_DIR}/wifi_setup_material.h")
    message(FATAL_ERROR "Create private BLE setup material first: python components/wifi_manager/tools/prepare_setup.py --device-id BB-14C19FC68C60")
endif()
target_include_directories(${COMPONENT_LIB} PRIVATE "${BB_WIFI_SETUP_DIR}")
