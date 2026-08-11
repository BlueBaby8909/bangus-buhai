/**
 * @file wifi_manager.c
 * @brief Wi-Fi lifecycle manager — SoftAP provisioning + station mode.
 *
 * DESIGN NOTES
 * ============
 *
 * Provisioning via BLE:
 * ---------------------
 * BLE was chosen for provisioning because:
 *   1. It's the standard for modern IoT devices, allowing quick discovery.
 *   2. Better user experience through the ESP BLE Provisioning app.
 *   3. It does not disconnect the phone from its current Wi-Fi network.
 *   4. Built into ESP-IDF's wifi_provisioning manager — well maintained.
 *
 * Reconnection strategy:
 * ----------------------
 * Exponential backoff: 1s → 2s → 4s → 8s → ... → 300s (5 min cap).
 * The delay is implemented with a FreeRTOS timer rather than blocking the
 * event handler — event handlers must return quickly.
 *
 * After AUTH_FAIL (bad stored password), the device re-enters provisioning
 * mode instead of looping forever on bad credentials.
 *
 * Event loop integration:
 * -----------------------
 * Posts SYSTEM_EVENT_WIFI_CONNECTED and SYSTEM_EVENT_WIFI_DISCONNECTED to the
 * default event loop. The telemetry service and any other component should wait
 * on these events rather than polling wifi_manager_is_connected().
 */

#include "wifi_manager.h"
#include "app_events.h"
#include "sdkconfig.h"

#include <string.h>
#include <stdlib.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/timers.h"

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "nvs.h"

#include "network_provisioning/manager.h"
#include "network_provisioning/scheme_ble.h"

/* -------------------------------------------------------------------------- */
/*  Private constants & types                                                  */
/* -------------------------------------------------------------------------- */

static const char *TAG = "WIFI_MGR";

/* NVS namespace for Wi-Fi credential state. The actual SSID/password are
 * stored by the Wi-Fi driver itself (CONFIG_ESP_WIFI_NVS_ENABLED=y, default).
 * We only track whether provisioning has been completed. */
#define NVS_NAMESPACE           "wifi_mgr"
#define NVS_KEY_PROVISIONED     "provisioned"

/* Maximum retry delay cap — 5 minutes. */
#define RECONNECT_MAX_DELAY_MS  (5UL * 60UL * 1000UL)

/* SoftAP provisioning AP prefix. The full name will be "BB-SETUP-XXXXXX"
 * where XXXXXX is the last 3 bytes of the station MAC. */
#define PROV_AP_NAME_PREFIX     CONFIG_BB_DEVICE_NAME_PREFIX

/* Provisioning security level.
 * WIFI_PROV_SECURITY_1 = Curve25519 key exchange + AES-CTR with Proof of
 * Possession (PoP). The PoP is printed on the device label (or shown on the
 * LCD) so only someone physically near the device can provision it. */
#define PROV_SECURITY_LEVEL     NETWORK_PROV_SECURITY_1

/* -------------------------------------------------------------------------- */
/*  Module-level state                                                         */
/* -------------------------------------------------------------------------- */

static volatile bool s_wifi_connected    = false;
static uint32_t      s_reconnect_delay_ms = 1000;   /* starts at 1 s           */
static TimerHandle_t s_reconnect_timer   = NULL;
static bool          s_auth_failed       = false;    /* sticky across retries   */

/* -------------------------------------------------------------------------- */
/*  Forward declarations                                                       */
/* -------------------------------------------------------------------------- */

static void start_provisioning(void);
static void start_reconnect_timer(void);
static void reconnect_timer_cb(TimerHandle_t xTimer);
static void set_connected(bool connected);

/* -------------------------------------------------------------------------- */
/*  NVS helpers                                                                */
/* -------------------------------------------------------------------------- */

/** @return true if NVS says we have been provisioned before. */
static bool nvs_is_provisioned(void)
{
    nvs_handle_t handle;
    uint8_t val = 0;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle) == ESP_OK) {
        nvs_get_u8(handle, NVS_KEY_PROVISIONED, &val);
        nvs_close(handle);
    }
    return val == 1;
}

/** Write provisioned flag to NVS. */
static void nvs_mark_provisioned(void)
{
    nvs_handle_t handle;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle) == ESP_OK) {
        nvs_set_u8(handle, NVS_KEY_PROVISIONED, 1);
        nvs_commit(handle);
        nvs_close(handle);
    }
}

/** Clear provisioned flag so next boot re-enters provisioning. */
static void nvs_clear_provisioned(void)
{
    nvs_handle_t handle;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle) == ESP_OK) {
        nvs_set_u8(handle, NVS_KEY_PROVISIONED, 0);
        nvs_commit(handle);
        nvs_close(handle);
    }
}

/* -------------------------------------------------------------------------- */
/*  Connection state management                                                */
/* -------------------------------------------------------------------------- */

static void set_connected(bool connected)
{
    s_wifi_connected = connected;
    if (connected) {
        /* Reset backoff on successful connection */
        s_reconnect_delay_ms = 1000;
        s_auth_failed = false;
        esp_event_post(SYSTEM_EVENTS, SYSTEM_EVENT_WIFI_CONNECTED, NULL, 0, portMAX_DELAY);
        ESP_LOGI(TAG, "Wi-Fi connected");
    } else {
        esp_event_post(SYSTEM_EVENTS, SYSTEM_EVENT_WIFI_DISCONNECTED, NULL, 0, portMAX_DELAY);
        ESP_LOGW(TAG, "Wi-Fi disconnected");
    }
}

/* -------------------------------------------------------------------------- */
/*  Reconnection with exponential backoff                                      */
/* -------------------------------------------------------------------------- */

static void reconnect_timer_cb(TimerHandle_t xTimer)
{
    ESP_LOGI(TAG, "Attempting Wi-Fi reconnect...");
    esp_err_t err = esp_wifi_connect();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_connect() failed: %s", esp_err_to_name(err));
    }
}

static void start_reconnect_timer(void)
{
    ESP_LOGW(TAG, "Scheduling reconnect in %lu ms", (unsigned long)s_reconnect_delay_ms);

    if (s_reconnect_timer == NULL) {
        s_reconnect_timer = xTimerCreate(
            "wifi_reconnect",
            pdMS_TO_TICKS(s_reconnect_delay_ms),
            pdFALSE,   /* one-shot */
            NULL,
            reconnect_timer_cb
        );
    } else {
        xTimerChangePeriod(s_reconnect_timer,
                           pdMS_TO_TICKS(s_reconnect_delay_ms),
                           portMAX_DELAY);
    }

    xTimerStart(s_reconnect_timer, portMAX_DELAY);

    /* Exponential backoff: double the delay, cap at 5 minutes */
    s_reconnect_delay_ms = s_reconnect_delay_ms * 2;
    if (s_reconnect_delay_ms > RECONNECT_MAX_DELAY_MS) {
        s_reconnect_delay_ms = RECONNECT_MAX_DELAY_MS;
    }
}

/* -------------------------------------------------------------------------- */
/*  Provisioning                                                               */
/* -------------------------------------------------------------------------- */

static void start_provisioning(void)
{
    ESP_LOGI(TAG, "Starting BLE provisioning mode...");

    /* Build the AP name: BB-SETUP-AABBCC */
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    char service_name[32];
    snprintf(service_name, sizeof(service_name),
             "%s-%02X%02X%02X",
             PROV_AP_NAME_PREFIX, mac[3], mac[4], mac[5]);

    /* Proof of Possession: last 8 hex chars of MAC.
     * In a real product this would be printed on a label on the device. */
    char pop[9];
    snprintf(pop, sizeof(pop), "%02X%02X%02X%02X", mac[2], mac[3], mac[4], mac[5]);

    ESP_LOGI(TAG, "Provisioning AP: %s | PoP: %s", service_name, pop);

    /* Print to LCD / serial so the user knows how to connect */
    ESP_LOGI(TAG, "Use ESP BLE Provisioning app to connect to \"%s\"", service_name);

    network_prov_mgr_config_t config = {
        .scheme = network_prov_scheme_ble,
        .scheme_event_handler = NETWORK_PROV_SCHEME_BLE_EVENT_HANDLER_FREE_BTDM,
    };
    ESP_ERROR_CHECK(network_prov_mgr_init(config));

    ESP_ERROR_CHECK(network_prov_mgr_start_provisioning(
        PROV_SECURITY_LEVEL,
        (const void *)pop,   /* proof of possession */
        service_name,        /* BLE Device Name */
        NULL
    ));
}

/* -------------------------------------------------------------------------- */
/*  Event handlers                                                             */
/* -------------------------------------------------------------------------- */

static void prov_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    switch (event_id) {
        case NETWORK_PROV_START:
            ESP_LOGI(TAG, "Provisioning started");
            break;

        case NETWORK_PROV_WIFI_CRED_RECV: {
            wifi_sta_config_t *cfg = (wifi_sta_config_t *)event_data;
            ESP_LOGI(TAG, "Received credentials for SSID: %s", (char *)cfg->ssid);
            break;
        }

        case NETWORK_PROV_WIFI_CRED_FAIL: {
            network_prov_wifi_sta_fail_reason_t *reason = (network_prov_wifi_sta_fail_reason_t *)event_data;
            ESP_LOGE(TAG, "Provisioning failed: %s",
                     (*reason == NETWORK_PROV_WIFI_STA_AUTH_ERROR) ? "Auth error" : "AP not found");
            /* Reset so the user can try again */
            network_prov_mgr_reset_wifi_sm_state_on_failure();
            break;
        }

        case NETWORK_PROV_WIFI_CRED_SUCCESS:
            ESP_LOGI(TAG, "Provisioning credentials accepted");
            nvs_mark_provisioned();
            break;

        case NETWORK_PROV_END:
            /* Release provisioning resources now that STA has connected */
            network_prov_mgr_deinit();
            ESP_LOGI(TAG, "Provisioning complete — resources released");
            break;

        default:
            break;
    }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
            case WIFI_EVENT_STA_START:
                ESP_LOGI(TAG, "STA started, connecting...");
                esp_wifi_connect();
                break;

            case WIFI_EVENT_STA_DISCONNECTED: {
                wifi_event_sta_disconnected_t *disc =
                    (wifi_event_sta_disconnected_t *)event_data;

                set_connected(false);
                ESP_LOGW(TAG, "Disconnected, reason: %d", disc->reason);

                /* AUTH_FAIL means stored credentials are wrong → re-provision */
                if (disc->reason == WIFI_REASON_AUTH_FAIL ||
                    disc->reason == WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT) {
                    if (!s_auth_failed) {
                        s_auth_failed = true;
                        ESP_LOGE(TAG, "Auth failure — stored credentials are invalid");
                        ESP_LOGW(TAG, "Re-entering provisioning mode...");
                        nvs_clear_provisioned();
                        esp_restart(); /* simplest way to cleanly re-enter prov mode */
                    }
                } else {
                    /* Transient disconnect (AP gone, range issue) — use backoff */
                    start_reconnect_timer();
                }
                break;
            }

            default:
                break;
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        set_connected(true);
    }
}

/* -------------------------------------------------------------------------- */
/*  Public API                                                                 */
/* -------------------------------------------------------------------------- */

esp_err_t wifi_manager_init(void)
{
    ESP_LOGI(TAG, "Initialising Wi-Fi manager");

    /* netif + default event loop are initialised by app_main before us */
    esp_netif_create_default_wifi_sta();
    /* SoftAP netif is created by wifi_prov_scheme_softap internally */

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));

    /* Register Wi-Fi and IP event handlers */
    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL));

    /* Register provisioning event handler */
    ESP_ERROR_CHECK(esp_event_handler_register(
        NETWORK_PROV_EVENT, ESP_EVENT_ANY_ID, prov_event_handler, NULL));

    if (!nvs_is_provisioned()) {
        /* First boot or after factory reset — enter provisioning mode */
        ESP_LOGI(TAG, "No credentials stored — entering provisioning mode");
        start_provisioning();
    } else {
        /* Credentials exist — start STA and let the driver load them from NVS */
        ESP_LOGI(TAG, "Credentials found in NVS — connecting...");
        ESP_ERROR_CHECK(esp_wifi_start());
        /* WIFI_EVENT_STA_START will trigger esp_wifi_connect() */
    }

    return ESP_OK;
}

bool wifi_manager_is_connected(void)
{
    return s_wifi_connected;
}

void wifi_manager_reset_credentials(void)
{
    ESP_LOGW(TAG, "Factory reset: clearing Wi-Fi credentials");
    nvs_clear_provisioned();
    /* The Wi-Fi driver stores its own credentials under the "nvs" namespace.
     * Erasing our flag is enough — on next boot, provisioning mode starts and
     * the user will enter new credentials, which the driver saves back to NVS. */
    esp_restart();
}
