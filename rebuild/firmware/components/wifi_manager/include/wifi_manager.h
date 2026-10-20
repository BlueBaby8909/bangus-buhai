#pragma once

#include "esp_err.h"

/* Call from app_main, not concurrently. Initializes Wi-Fi without starting it. */
esp_err_t wifi_manager_init(void);

/* Call once after init, from app_main. Starts recovery, BLE setup and USB commands.
 * Missing credentials open a five-minute setup window; errors never erase NVS.
 * A version-1 bb_wifi/active blob contains four bytes (version, SSID length,
 * password length, reserved=0), then 32 SSID bytes and 64 password bytes.
 * Provisioning writes this record only after a successful 30-second IP trial.
 */
esp_err_t wifi_manager_start(void);
