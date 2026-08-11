/**
 * @file wifi_manager.h
 * @brief Wi-Fi lifecycle manager for Bangus Buhai firmware.
 *
 * This component manages the complete Wi-Fi lifecycle:
 *  - On first boot (or after factory reset): enters SoftAP provisioning mode,
 *    hosts a captive portal, and accepts home Wi-Fi credentials from a browser.
 *  - On subsequent boots: connects using NVS-stored credentials with exponential
 *    backoff reconnection.
 *  - Publishes SYSTEM_EVENT_WIFI_CONNECTED / SYSTEM_EVENT_WIFI_DISCONNECTED to
 *    the default event loop so other components can react cleanly.
 *
 * Provisioning approach: SoftAP + HTTP captive portal
 *   - The device broadcasts an AP named "BB-SETUP-XXXXXX" where XXXXXX is the
 *     last 3 bytes of the MAC address.
 *   - The user connects from any phone/browser and submits their home Wi-Fi
 *     SSID and password via a web form.
 *   - No companion app required — works with any device that has a browser.
 *   - This matches what commercial IoT products (Sonos, smart plugs) use.
 */

#pragma once

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize Wi-Fi and either connect (if provisioned) or start
 *        provisioning mode (if first boot / after reset).
 *
 * This function initialises the Wi-Fi driver, registers event handlers, and
 * starts either:
 *   a) STA mode with NVS-stored credentials, or
 *   b) SoftAP provisioning mode if no credentials are stored yet.
 *
 * This is the ONLY place Wi-Fi is initialised. Other components must NOT call
 * esp_wifi_init() directly.
 *
 * @return ESP_OK on success.
 */
esp_err_t wifi_manager_init(void);

/**
 * @brief Return true if the station is currently associated and has an IP.
 */
bool wifi_manager_is_connected(void);

/**
 * @brief Erase stored Wi-Fi credentials from NVS and restart provisioning.
 *
 * Call this on a factory-reset trigger (e.g., long button press) so the device
 * enters provisioning mode on the next boot.
 */
void wifi_manager_reset_credentials(void);

#ifdef __cplusplus
}
#endif
