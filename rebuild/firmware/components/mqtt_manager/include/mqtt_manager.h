#pragma once

#include <stdbool.h>
#include "esp_err.h"

/* Call once from app_main after local tasks and the Wi-Fi initialization attempt.
 * boot_id is a canonical UUID generated before ADC/radio startup. Copied here.
 * The worker captures/persists telemetry even without a usable station or UTC.
 * One worker owns time-gated MQTT recovery, client lifetime and the durable queue.
 * Never waits for network/time. No subscriptions except application ACKs.
 */
esp_err_t mqtt_manager_start(const char *boot_id, bool networking_initialized);
