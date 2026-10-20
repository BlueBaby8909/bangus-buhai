#include "wifi_manager.h"
#include <ctype.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "esp_check.h"
#include "esp_console.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "esp_wifi_default.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "protocomm.h"
#include "protocomm_ble.h"
#include "protocomm_security2.h"
#include "network_provisioning/network_config.h"
#include "network_provisioning/network_scan.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "wifi_setup_material.h"

#if !CONFIG_BT_NIMBLE_ENABLED || !CONFIG_ESP_PROTOCOMM_SUPPORT_SECURITY_VERSION_2
#error "T07 requires NimBLE and Security 2"
#endif
#if !CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG
#error "T07 requires USB Serial/JTAG primary console"
#endif

#define SETUP_WINDOW_US (300LL * 1000000)
#define TRIAL_WINDOW_US (30LL * 1000000)
#define SCAN_LIMIT CONFIG_NETWORK_PROV_SCAN_MAX_ENTRIES
#define SCAN_FINISHED BIT0
_Static_assert(sizeof(bb_setup_mac) == 6 && sizeof(bb_setup_salt) == 16 &&
               sizeof(bb_setup_verifier) == 384, "Invalid Security 2 material widths");
static const char *TAG = "wifi_manager";
static bool initialized, worker_started;
static esp_netif_t *station_netif;
static QueueHandle_t events;
static SemaphoreHandle_t shared_lock;
static EventGroupHandle_t scan_flags;
static atomic_bool event_overflow;
static atomic_uint ble_generation;

typedef struct {
    uint8_t version, ssid_length, password_length, reserved;
    uint8_t ssid[32], password[64];
} saved_network_t;
_Static_assert(sizeof(saved_network_t) == 100, "Saved network format changed");

typedef enum {
    STA_STARTED, STA_DISCONNECTED, GOT_IP, LOST_IP, SCAN_DONE, BLE_DISCONNECTED,
    OPEN_SETUP, FORGET_NETWORK, APPLY_NETWORK, SCAN_NETWORKS
} event_kind_t;
typedef struct {
    event_kind_t kind;
    uint16_t reason;
    uint32_t ip;
    uint32_t generation;
    saved_network_t candidate;
    bool passive;
    uint32_t period_ms;
} manager_event_t;
typedef enum { SETUP_REQUIRED, STORAGE_ERROR, WAIT_START, CONNECTING, ONLINE, BACKOFF } phase_t;
static const char *const phase_names[] = {
    "SETUP_REQUIRED", "STORAGE_ERROR", "WAIT_START", "CONNECTING", "ONLINE", "BACKOFF"
};

/* Protocol callbacks use this mutex-protected staging area/snapshot.
 * Only the worker changes the Wi-Fi driver, NVS and BLE lifetime. */
static struct {
    phase_t phase;
    bool saved, setup_open, trial, apply_pending, staged;
    int64_t setup_deadline;
    uint32_t staged_session, staged_generation;
    saved_network_t pending;
    network_prov_config_get_wifi_data_t provision;
    bool scan_pending, scan_finished;
    esp_err_t scan_error;
    uint16_t scan_count, scan_total;
    network_prov_scan_wifi_result_t scan[SCAN_LIMIT];
} shared;

static saved_network_t saved, candidate;
static bool has_saved, driver_started, trial_active, scan_running, config_dirty = true;
static phase_t phase;
static uint32_t backoff_ms = 1000;
static int64_t retry_at, attempt_deadline, trial_deadline, setup_deadline;
static int64_t scan_deadline, success_close_at;
static protocomm_t *provisioning;
static esp_err_t storage_error;
static uint32_t trial_generation;

static void wipe(void *ptr, size_t size)
{
    volatile unsigned char *bytes = ptr;
    while (size--) { *bytes++ = 0; }
}

static bool valid_record(const saved_network_t *r, size_t size)
{
    return size == sizeof(*r) && r->version == 1 && r->reserved == 0 &&
        r->ssid_length > 0 && r->ssid_length <= sizeof(r->ssid) &&
        r->password_length <= sizeof(r->password) &&
        memchr(r->ssid, 0, r->ssid_length) == NULL &&
        memchr(r->password, 0, r->password_length) == NULL;
}

static void publish_state(void)
{
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    shared.phase = phase;
    shared.saved = has_saved;
    shared.trial = trial_active;
    shared.setup_open = provisioning && setup_deadline > esp_timer_get_time();
    shared.setup_deadline = setup_deadline;
    xSemaphoreGive(shared_lock);
}

static esp_err_t load_saved_network(void)
{
    has_saved = false;
    wipe(&saved, sizeof(saved));
    nvs_handle_t handle;
    esp_err_t ret = nvs_open("bb_wifi", NVS_READONLY, &handle);
    if (ret == ESP_ERR_NVS_NOT_FOUND) { return ESP_OK; }
    if (ret != ESP_OK) { return ret; }
    size_t size = sizeof(saved);
    ret = nvs_get_blob(handle, "active", &saved, &size);
    nvs_close(handle);
    if (ret == ESP_ERR_NVS_NOT_FOUND) { return ESP_OK; }
    if (ret != ESP_OK) { return ret; }
    if (!valid_record(&saved, size)) {
        wipe(&saved, sizeof(saved));
        return ESP_ERR_INVALID_ARG;
    }
    has_saved = true;
    return ESP_OK;
}

static esp_err_t save_candidate(void)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open("bb_wifi", NVS_READWRITE, &handle);
    if (ret != ESP_OK) { return ret; }
    /* One blob avoids mixed SSID/password updates; no write occurs during trial. */
    ret = nvs_set_blob(handle, "active", &candidate, sizeof(candidate));
    if (ret == ESP_OK) { ret = nvs_commit(handle); }
    if (ret == ESP_OK && trial_generation != atomic_load(&ble_generation)) {
        ret = ESP_ERR_INVALID_STATE; /* Phone cancelled during the storage call. */
    }
    if (ret != ESP_OK) {
        esp_err_t rollback = has_saved ?
            nvs_set_blob(handle, "active", &saved, sizeof(saved)) :
            nvs_erase_key(handle, "active");
        if (rollback == ESP_ERR_NVS_NOT_FOUND && !has_saved) { rollback = ESP_OK; }
        if (rollback == ESP_OK) { rollback = nvs_commit(handle); }
        if (rollback != ESP_OK) {
            ESP_LOGE(TAG, "Storage rollback failed: %s; inspect storage",
                     esp_err_to_name(rollback));
        }
    }
    nvs_close(handle);
    return ret;
}

static esp_err_t forget_saved_network(void)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open("bb_wifi", NVS_READWRITE, &handle);
    if (ret != ESP_OK) { return ret; }
    ret = nvs_erase_key(handle, "active");
    if (ret == ESP_ERR_NVS_NOT_FOUND) { ret = ESP_OK; }
    if (ret == ESP_OK) { ret = nvs_commit(handle); }
    nvs_close(handle);
    return ret;
}

static void on_network_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    manager_event_t event = {0};
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        event.kind = STA_STARTED;
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        event.kind = STA_DISCONNECTED;
        event.reason = ((wifi_event_sta_disconnected_t *)data)->reason;
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_SCAN_DONE) {
        event.kind = SCAN_DONE;
        event.reason = ((wifi_event_sta_scan_done_t *)data)->status;
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const ip_event_got_ip_t *ip_event = data;
        if (ip_event->esp_netif != station_netif) { return; }
        event.kind = GOT_IP;
        event.ip = ip_event->ip_info.ip.addr;
    } else if (base == IP_EVENT && id == IP_EVENT_STA_LOST_IP) {
        event.kind = LOST_IP;
    } else if (base == PROTOCOMM_TRANSPORT_BLE_EVENT &&
               id == PROTOCOMM_TRANSPORT_BLE_CONNECTED) {
        atomic_fetch_add(&ble_generation, 1);
        return;
    } else if (base == PROTOCOMM_TRANSPORT_BLE_EVENT &&
               id == PROTOCOMM_TRANSPORT_BLE_DISCONNECTED) {
        event.kind = BLE_DISCONNECTED;
        event.generation = atomic_fetch_add(&ble_generation, 1) + 1;
    } else { return; }
    if (xQueueSend(events, &event, 0) != pdTRUE) {
        atomic_store(&event_overflow, true);
    }
}

static void provisioning_state(network_prov_wifi_sta_state_t state,
                               network_prov_wifi_sta_fail_reason_t reason)
{
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    memset(&shared.provision, 0, sizeof(shared.provision));
    shared.provision.wifi_state = state;
    shared.trial = trial_active;
    if (state == NETWORK_PROV_WIFI_STA_CONN_ATTEMPT_FAILED) {
        shared.provision.fail_reason = reason;
    }
    shared.apply_pending = false;
    xSemaphoreGive(shared_lock);
}

static void scan_complete(esp_err_t error)
{
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    shared.scan_error = error;
    shared.scan_pending = false;
    shared.scan_finished = true;
    xSemaphoreGive(shared_lock);
    scan_running = false;
    scan_deadline = 0;
    xEventGroupSetBits(scan_flags, SCAN_FINISHED);
}

static void stop_scan(void)
{
    if (scan_running) {
        esp_wifi_scan_stop();
        esp_wifi_clear_ap_list();
        scan_complete(ESP_ERR_INVALID_STATE);
    }
}

static esp_err_t stop_station(void)
{
    stop_scan();
    retry_at = attempt_deadline = 0;
    if (!driver_started) { return ESP_OK; }
    esp_err_t ret = esp_wifi_stop();
    if (ret == ESP_OK || ret == ESP_ERR_WIFI_NOT_STARTED) {
        driver_started = false;
        return ESP_OK;
    }
    ESP_LOGE(TAG, "Wi-Fi stop failed: %s", esp_err_to_name(ret));
    return ret;
}

static void schedule_retry(void)
{
    if (retry_at || !has_saved || trial_active) { return; }
    uint32_t low = backoff_ms * 3 / 4, high = backoff_ms + backoff_ms / 4;
    if (high > 300000) { high = 300000; }
    uint32_t delay_ms = low + esp_random() % (high - low + 1);
    retry_at = esp_timer_get_time() + (int64_t)delay_ms * 1000;
    attempt_deadline = 0;
    phase = BACKOFF;
    backoff_ms = backoff_ms >= 150000 ? 300000 : backoff_ms * 2;
    ESP_LOGI(TAG, "Disconnected; retry in %lu ms", (unsigned long)delay_ms);
}

static void trial_failed(const char *reason, network_prov_wifi_sta_fail_reason_t error)
{
    ESP_LOGW(TAG, "Trial failed/cancelled: %s; previous record preserved", reason);
    trial_active = false;
    trial_deadline = success_close_at = 0;
    config_dirty = true;
    wipe(&candidate, sizeof(candidate));
    provisioning_state(NETWORK_PROV_WIFI_STA_CONN_ATTEMPT_FAILED, error);
    stop_station();
    phase = has_saved ? BACKOFF : SETUP_REQUIRED;
    schedule_retry();
}

static void connect_station(void)
{
    phase = CONNECTING;
    attempt_deadline = esp_timer_get_time() + TRIAL_WINDOW_US;
    if (trial_active && attempt_deadline > trial_deadline) { attempt_deadline = trial_deadline; }
    esp_err_t ret = esp_wifi_connect();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Connection attempt failed: %s", esp_err_to_name(ret));
        if (trial_active) { trial_failed("driver connection error", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
        else { schedule_retry(); }
    } else {
        ESP_LOGI(TAG, "Connecting to %s network", trial_active ? "candidate" : "saved");
    }
}

static void begin_attempt(void)
{
    retry_at = 0;
    if (driver_started) {
        wifi_ap_record_t ap;
        if (config_dirty || esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
            if (stop_station() != ESP_OK) { schedule_retry(); return; }
        }
    }
    if (driver_started) { connect_station(); return; }
    const saved_network_t *record = trial_active ? &candidate : &saved;
    wifi_config_t config = {0};
    memcpy(config.sta.ssid, record->ssid, record->ssid_length);
    memcpy(config.sta.password, record->password, record->password_length);
    config.sta.failure_retry_cnt = 0;
    config.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
    config.sta.threshold.authmode = record->password_length ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    config.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;
    esp_err_t ret = esp_wifi_set_config(WIFI_IF_STA, &config);
    wipe(&config, sizeof(config));
    if (ret == ESP_OK) {
        config_dirty = false;
        phase = WAIT_START;
        attempt_deadline = esp_timer_get_time() + TRIAL_WINDOW_US;
        if (trial_active && attempt_deadline > trial_deadline) { attempt_deadline = trial_deadline; }
        ret = esp_wifi_start();
        if (ret == ESP_OK) { driver_started = true; return; }
    }
    ESP_LOGW(TAG, "Wi-Fi start failed: %s", esp_err_to_name(ret));
    if (trial_active) { trial_failed("driver start error", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
    else { schedule_retry(); }
}

static bool current_ip(uint32_t reported, wifi_ap_record_t *ap, esp_netif_ip_info_t *ip)
{
    const saved_network_t *expected = trial_active ? &candidate : &saved;
    return esp_wifi_sta_get_ap_info(ap) == ESP_OK &&
        esp_netif_get_ip_info(station_netif, ip) == ESP_OK &&
        reported != 0 && ip->ip.addr == reported &&
        strnlen((const char *)ap->ssid, sizeof(ap->ssid)) == expected->ssid_length &&
        memcmp(ap->ssid, expected->ssid, expected->ssid_length) == 0;
}

/* Bind staged credentials to the requesting BLE transport session. */
struct network_prov_ctx { uint32_t session; };

static esp_err_t protocol_get_status(network_prov_config_get_wifi_data_t *out, network_prov_ctx_t **ctx)
{
    (void)ctx;
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    *out = shared.provision;
    xSemaphoreGive(shared_lock);
    return ESP_OK;
}

static esp_err_t protocol_set_config(const network_prov_config_set_wifi_data_t *in, network_prov_ctx_t **ctx)
{
    size_t ssid_len = strnlen(in->ssid, sizeof(in->ssid));
    size_t password_len = strnlen(in->password, sizeof(in->password));
    if (!ssid_len || ssid_len > 32 || password_len > 63) { return ESP_ERR_INVALID_ARG; }
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    if (!shared.setup_open || shared.trial || shared.apply_pending ||
        esp_timer_get_time() >= shared.setup_deadline) {
        xSemaphoreGive(shared_lock);
        return ESP_ERR_INVALID_STATE;
    }
    wipe(&shared.pending, sizeof(shared.pending));
    shared.pending.version = 1;
    shared.pending.ssid_length = ssid_len;
    shared.pending.password_length = password_len;
    memcpy(shared.pending.ssid, in->ssid, ssid_len);
    memcpy(shared.pending.password, in->password, password_len);
    shared.staged_session = (*ctx)->session;
    shared.staged_generation = atomic_load(&ble_generation);
    shared.staged = true;
    xSemaphoreGive(shared_lock);
    return ESP_OK;
}

static esp_err_t protocol_apply_config(network_prov_ctx_t **ctx)
{
    manager_event_t event = {.kind = APPLY_NETWORK};
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    if (!shared.setup_open || !shared.staged || shared.apply_pending || shared.trial ||
        shared.staged_session != (*ctx)->session ||
        shared.staged_generation != atomic_load(&ble_generation) ||
        esp_timer_get_time() >= shared.setup_deadline) {
        xSemaphoreGive(shared_lock);
        return ESP_ERR_INVALID_STATE;
    }
    event.candidate = shared.pending;
    event.generation = shared.staged_generation;
    esp_err_t ret = ESP_ERR_TIMEOUT;
    if (xQueueSend(events, &event, 0) == pdTRUE) {
        shared.apply_pending = true;
        shared.staged = false;
        shared.provision.wifi_state = NETWORK_PROV_WIFI_STA_CONNECTING;
        wipe(&shared.pending, sizeof(shared.pending));
        ret = ESP_OK;
    }
    xSemaphoreGive(shared_lock);
    wipe(&event, sizeof(event));
    return ret;
}

static bool accepts_setup_requests(void)
{
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    bool allowed = shared.setup_open && esp_timer_get_time() < shared.setup_deadline;
    xSemaphoreGive(shared_lock);
    return allowed;
}

static esp_err_t config_endpoint(uint32_t session, const uint8_t *input, ssize_t length,
                                uint8_t **output, ssize_t *out_length, void *arg)
{
    (void)arg;
    if (!accepts_setup_requests()) { return ESP_ERR_INVALID_STATE; }
    network_prov_ctx_t context = {.session = session};
    network_prov_config_handlers_t handlers = {
        .wifi_get_status_handler = protocol_get_status,
        .wifi_set_config_handler = protocol_set_config,
        .wifi_apply_config_handler = protocol_apply_config, .ctx = &context
    };
    return network_prov_config_data_handler(session, input, length, output, out_length, &handlers);
}

static esp_err_t protocol_scan_start(bool blocking, bool passive, uint8_t groups,
                                     uint32_t period_ms, network_prov_scan_ctx_t **ctx)
{
    (void)ctx; (void)groups; /* BLE supports scanning all channels together. */
    manager_event_t event = {
        .kind = SCAN_NETWORKS, .passive = passive,
        .period_ms = period_ms < 30 ? 120 : (period_ms > 300 ? 300 : period_ms)
    };
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    if (shared.scan_pending || shared.trial || shared.apply_pending) {
        xSemaphoreGive(shared_lock);
        return ESP_ERR_INVALID_STATE;
    }
    shared.scan_pending = true;
    shared.scan_finished = false;
    shared.scan_error = ESP_OK;
    shared.scan_count = shared.scan_total = 0;
    xEventGroupClearBits(scan_flags, SCAN_FINISHED);
    bool queued = xQueueSend(events, &event, 0) == pdTRUE;
    if (!queued) {
        shared.scan_pending = false;
        shared.scan_finished = true;
        shared.scan_error = ESP_ERR_TIMEOUT;
    }
    xSemaphoreGive(shared_lock);
    if (!queued) { return ESP_ERR_TIMEOUT; }
    if (blocking) {
        EventBits_t bits = xEventGroupWaitBits(scan_flags, SCAN_FINISHED, pdFALSE, pdTRUE, pdMS_TO_TICKS(10000));
        if (!(bits & SCAN_FINISHED)) { return ESP_ERR_TIMEOUT; }
        xSemaphoreTake(shared_lock, portMAX_DELAY);
        esp_err_t ret = shared.scan_error;
        xSemaphoreGive(shared_lock);
        return ret;
    }
    return ESP_OK;
}

static esp_err_t protocol_scan_status(bool *finished, uint16_t *count, network_prov_scan_ctx_t **ctx)
{
    (void)ctx;
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    *finished = shared.scan_finished;
    *count = shared.scan_count;
    xSemaphoreGive(shared_lock);
    return ESP_OK;
}

static esp_err_t protocol_scan_result(uint16_t index, network_prov_scan_wifi_result_t *out, network_prov_scan_ctx_t **ctx)
{
    (void)ctx;
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    esp_err_t ret = ESP_ERR_NOT_FOUND;
    if (index < shared.scan_count) { *out = shared.scan[index]; ret = ESP_OK; }
    xSemaphoreGive(shared_lock);
    return ret;
}

static esp_err_t scan_endpoint(uint32_t session, const uint8_t *input, ssize_t length,
                               uint8_t **output, ssize_t *out_length, void *arg)
{
    (void)arg;
    if (!accepts_setup_requests()) { return ESP_ERR_INVALID_STATE; }
    network_prov_scan_handlers_t handlers = {
        .wifi_scan_start = protocol_scan_start, .wifi_scan_status = protocol_scan_status,
        .wifi_scan_result = protocol_scan_result
    };
    return network_prov_scan_handler(session, input, length, output, out_length, &handlers);
}

static void close_setup(void)
{
    atomic_fetch_add(&ble_generation, 1); /* Invalidate requests queued before close/forget. */
    xSemaphoreTake(shared_lock, portMAX_DELAY);
    shared.setup_open = shared.staged = shared.apply_pending = false;
    wipe(&shared.pending, sizeof(shared.pending));
    xSemaphoreGive(shared_lock);
    setup_deadline = success_close_at = 0;
    if (provisioning) {
        esp_err_t ret = protocomm_ble_stop(provisioning);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "BLE stop failed: %s; setup requests remain disabled", esp_err_to_name(ret));
            return; /* Transport may still reference the object: do not free it. */
        }
        protocomm_delete(provisioning);
        provisioning = NULL;
    }
    ESP_LOGI(TAG, "BLE setup closed; use wifi setup to reopen");
}

static esp_err_t open_setup(void)
{
    uint8_t mac[6];
    esp_err_t ret = esp_read_mac(mac, ESP_MAC_WIFI_STA);
    if (ret != ESP_OK) { return ret; }
    if (memcmp(mac, bb_setup_mac, sizeof(mac)) != 0) {
        ESP_LOGE(TAG, "Setup material belongs to another device; regenerate for this MAC");
        return ESP_ERR_INVALID_STATE;
    }
    if (provisioning && !setup_deadline) {
        close_setup();
        if (provisioning) { return ESP_ERR_INVALID_STATE; }
    }
    if (provisioning) {
        setup_deadline = esp_timer_get_time() + SETUP_WINDOW_US;
        success_close_at = 0;
        publish_state();
        return ESP_OK;
    }
    provisioning = protocomm_new();
    if (!provisioning) { return ESP_ERR_NO_MEM; }
    static protocomm_ble_name_uuid_t endpoints[] = {
        {"prov-scan", 0xff50}, {"prov-session", 0xff51},
        {"prov-config", 0xff52}, {"proto-ver", 0xff53}
    };
    protocomm_ble_config_t config = {
        .service_uuid = {0x07,0xed,0x9b,0x2d,0x0f,0x06,0x7c,0x87,0x9b,0x43,0x43,0x6b,0x4d,0x24,0x75,0x17},
        .nu_lookup_count = 4, .nu_lookup = endpoints
    };
    strlcpy(config.device_name, BB_SETUP_NAME, sizeof(config.device_name));
    ret = protocomm_ble_start(provisioning, &config);
    if (ret != ESP_OK) {
        protocomm_delete(provisioning); provisioning = NULL; return ret;
    }
    static const protocomm_security2_params_t security = {
        .salt = (const char *)bb_setup_salt, .salt_len = sizeof(bb_setup_salt),
        .verifier = (const char *)bb_setup_verifier, .verifier_len = sizeof(bb_setup_verifier)
    };
    ret = protocomm_set_security(provisioning, "prov-session", &protocomm_security2, &security);
    if (ret == ESP_OK) {
        char version[160];
        snprintf(version, sizeof(version),
            "{\"prov\":{\"ver\":\"v1.1\",\"sec_ver\":2,\"sec_patch_ver\":%u,\"cap\":[\"wifi_prov\",\"wifi_scan\"]}}",
            protocomm_security2.patch_ver);
        ret = protocomm_set_version(provisioning, "proto-ver", version);
    }
    if (ret == ESP_OK) { ret = protocomm_add_endpoint(provisioning, "prov-config", config_endpoint, NULL); }
    if (ret == ESP_OK) { ret = protocomm_add_endpoint(provisioning, "prov-scan", scan_endpoint, NULL); }
    if (ret != ESP_OK) { close_setup(); return ret; }
    setup_deadline = esp_timer_get_time() + SETUP_WINDOW_US;
    success_close_at = 0;
    provisioning_state(NETWORK_PROV_WIFI_STA_DISCONNECTED, NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
    publish_state();
    ESP_LOGI(TAG, "BLE setup open for five minutes: %s (Security 2)", BB_SETUP_NAME);
    return ESP_OK;
}

static void start_scan(const manager_event_t *event)
{
    if (!provisioning || trial_active || phase == CONNECTING || phase == WAIT_START) {
        scan_complete(ESP_ERR_INVALID_STATE); return;
    }
    esp_err_t ret = ESP_OK;
    if (!driver_started) {
        ret = esp_wifi_start();
        if (ret == ESP_OK) { driver_started = true; config_dirty = true; }
    }
    wifi_scan_config_t config = {
        .show_hidden = true,
        .scan_type = event->passive ? WIFI_SCAN_TYPE_PASSIVE : WIFI_SCAN_TYPE_ACTIVE,
        .scan_time = {.active = {.min = event->period_ms, .max = event->period_ms}}
    };
    if (event->passive) { config.scan_time.passive = event->period_ms; }
    if (ret == ESP_OK) { ret = esp_wifi_scan_start(&config, false); }
    if (ret != ESP_OK) { scan_complete(ret); return; }
    scan_running = true;
    scan_deadline = esp_timer_get_time() + 9000000;
}

static void collect_scan(uint16_t status)
{
    if (!scan_running) { return; }
    if (status) { scan_complete(ESP_FAIL); return; }
    uint16_t total = 0, count = SCAN_LIMIT;
    esp_err_t ret = esp_wifi_scan_get_ap_num(&total);
    wifi_ap_record_t *records = calloc(SCAN_LIMIT, sizeof(*records));
    if (!records) {
        esp_wifi_clear_ap_list(); scan_complete(ESP_ERR_NO_MEM); return;
    }
    if (ret == ESP_OK) { ret = esp_wifi_scan_get_ap_records(&count, records); }
    if (ret == ESP_OK) {
        xSemaphoreTake(shared_lock, portMAX_DELAY);
        shared.scan_total = total;
        shared.scan_count = count;
        for (unsigned i = 0; i < count; ++i) {
            network_prov_scan_wifi_result_t *out = &shared.scan[i];
            memset(out, 0, sizeof(*out));
            memcpy(out->ssid, records[i].ssid, sizeof(out->ssid));
            out->ssid[sizeof(out->ssid)-1] = 0;
            memcpy(out->bssid, records[i].bssid, sizeof(out->bssid));
            out->channel = records[i].primary;
            out->rssi = records[i].rssi;
            out->auth = records[i].authmode;
        }
        xSemaphoreGive(shared_lock);
        ESP_LOGI(TAG, "Scan complete: %u of %u APs stored; wifi status shows channels/RSSI",
                 (unsigned)count, (unsigned)total);
    } else { esp_wifi_clear_ap_list(); }
    free(records);
    scan_complete(ret);
}

static void on_got_ip(uint32_t reported)
{
    if (phase != CONNECTING && phase != ONLINE) { return; }
    wifi_ap_record_t ap;
    esp_netif_ip_info_t ip;
    if (!current_ip(reported, &ap, &ip)) { return; }
    if (trial_active) {
        if (trial_generation != atomic_load(&ble_generation)) {
            trial_failed("phone session ended", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); return;
        }
        if (esp_timer_get_time() >= trial_deadline || esp_timer_get_time() >= setup_deadline) {
            trial_failed("30-second deadline", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); return;
        }
        esp_err_t ret = save_candidate();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Could not save replacement: %s", esp_err_to_name(ret));
            trial_failed("NVS save error", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); return;
        }
        saved = candidate;
        has_saved = true;
        storage_error = ESP_OK;
        trial_active = false;
        trial_deadline = 0;
        wipe(&candidate, sizeof(candidate));
        xSemaphoreTake(shared_lock, portMAX_DELAY);
        memset(&shared.provision, 0, sizeof(shared.provision));
        shared.provision.wifi_state = NETWORK_PROV_WIFI_STA_CONNECTED;
        network_prov_wifi_sta_conn_info_t *out = &shared.provision.conn_info;
        snprintf(out->ip_addr, sizeof(out->ip_addr), IPSTR, IP2STR(&ip.ip));
        memcpy(out->ssid, ap.ssid, sizeof(out->ssid)); out->ssid[sizeof(out->ssid)-1] = 0;
        memcpy(out->bssid, ap.bssid, sizeof(out->bssid));
        out->channel = ap.primary; out->auth_mode = ap.authmode;
        shared.apply_pending = false;
        xSemaphoreGive(shared_lock);
        success_close_at = esp_timer_get_time() + 5000000;
        ESP_LOGI(TAG, "Candidate acquired IP; replacement committed");
    }
    phase = ONLINE;
    retry_at = attempt_deadline = 0;
    backoff_ms = 1000;
    ESP_LOGI(TAG, "Connected; IP acquired (internet/MQTT not checked)");
}

static void handle_event(manager_event_t *event)
{
    switch (event->kind) {
    case OPEN_SETUP: {
        esp_err_t ret = open_setup();
        if (ret != ESP_OK) { ESP_LOGE(TAG, "Setup open failed: %s", esp_err_to_name(ret)); }
        break;
    }
    case FORGET_NETWORK: {
        esp_err_t ret = forget_saved_network();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Forget failed: %s; RAM state retained", esp_err_to_name(ret)); break;
        }
        trial_active = has_saved = false; trial_deadline = 0; config_dirty = true;
        wipe(&saved, sizeof(saved)); wipe(&candidate, sizeof(candidate));
        stop_station(); phase = SETUP_REQUIRED; storage_error = ESP_OK;
        close_setup(); ret = open_setup();
        ESP_LOGI(TAG, "Replacement Wi-Fi record removed; identity and certificates preserved");
        if (ret != ESP_OK) { ESP_LOGE(TAG, "Setup open failed: %s", esp_err_to_name(ret)); }
        break;
    }
    case APPLY_NETWORK:
        if (!provisioning || event->generation != atomic_load(&ble_generation) ||
            esp_timer_get_time() >= setup_deadline || trial_active) {
            provisioning_state(NETWORK_PROV_WIFI_STA_CONN_ATTEMPT_FAILED, NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); break;
        }
        if (stop_station() != ESP_OK) {
            provisioning_state(NETWORK_PROV_WIFI_STA_CONN_ATTEMPT_FAILED, NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
            schedule_retry(); break;
        }
        candidate = event->candidate; trial_active = true; config_dirty = true;
        trial_generation = event->generation;
        trial_deadline = esp_timer_get_time() + TRIAL_WINDOW_US; success_close_at = 0;
        provisioning_state(NETWORK_PROV_WIFI_STA_CONNECTING, NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
        begin_attempt();
        break;
    case SCAN_NETWORKS: start_scan(event); break;
    case SCAN_DONE: collect_scan(event->reason); break;
    case BLE_DISCONNECTED:
        if (event->generation != atomic_load(&ble_generation)) { break; }
        xSemaphoreTake(shared_lock, portMAX_DELAY);
        shared.staged = false; wipe(&shared.pending, sizeof(shared.pending));
        xSemaphoreGive(shared_lock);
        if (trial_active) { trial_failed("phone disconnected before success", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
        else if (success_close_at) { close_setup(); }
        break;
    case STA_STARTED:
        if (phase == WAIT_START) { connect_station(); }
        break;
    case STA_DISCONNECTED: {
        wifi_ap_record_t ap;
        if (!driver_started || phase == WAIT_START || (!has_saved && !trial_active) ||
            esp_wifi_sta_get_ap_info(&ap) == ESP_OK) { break; }
        ESP_LOGW(TAG, "Disconnected, reason=%u; credentials retained", (unsigned)event->reason);
        bool auth = event->reason == WIFI_REASON_AUTH_FAIL ||
            event->reason == WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT || event->reason == WIFI_REASON_HANDSHAKE_TIMEOUT;
        if (auth) { ESP_LOGW(TAG, "Authentication/handshake failed; check password/AP security"); }
        if (trial_active) {
            trial_failed(auth ? "authentication" : "AP connection",
                         auth ? NETWORK_PROV_WIFI_STA_AUTH_ERROR : NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
        } else { schedule_retry(); }
        break;
    }
    case GOT_IP: on_got_ip(event->ip); break;
    case LOST_IP:
        if (phase == ONLINE) {
            esp_netif_ip_info_t ip;
            if (esp_netif_get_ip_info(station_netif, &ip) == ESP_OK && ip.ip.addr != 0) { break; }
            stop_station(); schedule_retry();
        }
        break;
    }
}

static void wifi_worker(void *arg)
{
    (void)arg;
    phase = storage_error != ESP_OK ? STORAGE_ERROR : SETUP_REQUIRED;
    provisioning_state(NETWORK_PROV_WIFI_STA_DISCONNECTED, NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
    if (has_saved) { begin_attempt(); }
    else if (storage_error == ESP_OK) {
        ESP_LOGI(TAG, "SETUP_REQUIRED: no saved network");
        esp_err_t ret = open_setup();
        if (ret != ESP_OK) { ESP_LOGE(TAG, "Setup open failed: %s", esp_err_to_name(ret)); }
    }
    publish_state();
    for (;;) {
        int64_t now = esp_timer_get_time(), wake_at = now + 1000000;
        int64_t deadlines[] = {scan_running ? 0 : retry_at, attempt_deadline,
            trial_deadline, setup_deadline, success_close_at, scan_deadline};
        for (unsigned i = 0; i < sizeof(deadlines)/sizeof(deadlines[0]); ++i) {
            if (deadlines[i] && deadlines[i] < wake_at) { wake_at = deadlines[i]; }
        }
        int64_t remaining_ms = (wake_at - now + 999)/1000;
        TickType_t wait = remaining_ms > 0 ? pdMS_TO_TICKS(remaining_ms) : 0;
        manager_event_t event = {0};
        bool received = xQueueReceive(events, &event, wait) == pdTRUE;
        if (atomic_exchange(&event_overflow, false)) {
            ESP_LOGW(TAG, "Event queue overflow; recovering saved network");
            atomic_fetch_add(&ble_generation, 1); /* Invalidate queued/staged trials. */
            if (trial_active) { trial_failed("event overflow", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
            else { stop_station(); schedule_retry(); }
            xSemaphoreTake(shared_lock, portMAX_DELAY);
            shared.staged = shared.apply_pending = false;
            wipe(&shared.pending, sizeof(shared.pending));
            xSemaphoreGive(shared_lock);
            /* Keep queued USB commands. Stale IP events are checked against live state. */
        }
        if (received) { handle_event(&event); }
        wipe(&event, sizeof(event));
        now = esp_timer_get_time();
        if (trial_active && trial_generation != atomic_load(&ble_generation)) {
            trial_failed("phone session ended", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND);
        }
        if (scan_running && now >= scan_deadline) { stop_scan(); }
        if (trial_active && now >= trial_deadline) { trial_failed("30-second deadline", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
        if (attempt_deadline && now >= attempt_deadline) {
            ESP_LOGW(TAG, "No IP within 30 seconds; saved credentials retained");
            stop_station(); schedule_retry();
        }
        if (setup_deadline && now >= setup_deadline) {
            if (trial_active) { trial_failed("setup window expired", NETWORK_PROV_WIFI_STA_AP_NOT_FOUND); }
            stop_scan(); close_setup();
        } else if (success_close_at && now >= success_close_at) {
            stop_scan(); close_setup();
        }
        if (retry_at && now >= retry_at && !scan_running) { begin_attempt(); }
        publish_state();
    }
}

static int wifi_command(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "status") == 0) {
        xSemaphoreTake(shared_lock, portMAX_DELAY);
        phase_t state = shared.phase;
        bool saved_present = shared.saved, open = shared.setup_open, trial = shared.trial;
        int64_t remaining = shared.setup_deadline - esp_timer_get_time();
        uint16_t count = shared.scan_count, total = shared.scan_total;
        xSemaphoreGive(shared_lock);
        printf("Wi-Fi: %s; saved=%s; setup=%s (%lld s); trial=%s\n",
               phase_names[state], saved_present ? "yes" : "no", open ? "open" : "closed",
               (long long)(open && remaining > 0 ? remaining/1000000 : 0), trial ? "yes" : "no");
        printf("Last scan: %u of %u APs%s\n", (unsigned)count, (unsigned)total,
               total > count ? " (truncated; manual SSID entry supported)" : "");
        for (unsigned i = 0; i < count; ++i) {
            xSemaphoreTake(shared_lock, portMAX_DELAY);
            network_prov_scan_wifi_result_t entry = shared.scan[i];
            xSemaphoreGive(shared_lock);
            char name[33];
            for (unsigned j = 0; j < sizeof(name); ++j) {
                unsigned char c = (unsigned char)entry.ssid[j];
                name[j] = c == 0 ? 0 : (isprint(c) ? (char)c : '?');
            }
            name[32] = 0;
            printf("  ch=%u rssi=%d auth=%u SSID=%s\n",
                   (unsigned)entry.channel, entry.rssi, (unsigned)entry.auth, name);
        }
        return 0;
    }
    manager_event_t event = {0};
    if (argc == 2 && strcmp(argv[1], "setup") == 0) { event.kind = OPEN_SETUP; }
    else if (argc == 3 && strcmp(argv[1], "forget") == 0 && strcmp(argv[2], "CONFIRM") == 0) {
        event.kind = FORGET_NETWORK;
    } else { printf("Usage: wifi status | wifi setup | wifi forget CONFIRM\n"); return 1; }
    if (xQueueSend(events, &event, 0) != pdTRUE) { printf("Wi-Fi worker busy; retry command\n"); return 1; }
    printf("Request queued; completion/error will appear in the Wi-Fi log\n");
    return 0;
}

static esp_err_t start_console(void)
{
    esp_console_repl_config_t config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    config.prompt = "bb> "; config.max_cmdline_length = 64;
    config.max_cmdline_args = 4; config.max_history_len = 4;
    esp_console_dev_usb_serial_jtag_config_t device = ESP_CONSOLE_DEV_USB_SERIAL_JTAG_CONFIG_DEFAULT();
    esp_console_repl_t *repl = NULL;
    esp_err_t ret = esp_console_new_repl_usb_serial_jtag(&device, &config, &repl);
    if (ret != ESP_OK) { return ret; }
    esp_console_cmd_t command = {.command = "wifi", .help = "status | setup | forget CONFIRM", .func = wifi_command};
    ret = esp_console_cmd_register(&command);
    if (ret == ESP_OK) { ret = esp_console_start_repl(repl); }
    if (ret != ESP_OK) { repl->del(repl); }
    return ret;
}

esp_err_t wifi_manager_start(void)
{
    if (!initialized) { return ESP_ERR_INVALID_STATE; }
    if (worker_started) { return ESP_OK; }
    storage_error = load_saved_network();
    if (storage_error != ESP_OK) {
        ESP_LOGE(TAG, "Saved network load failed: %s; storage preserved; USB setup/forget available",
                 esp_err_to_name(storage_error));
    }
    shared_lock = xSemaphoreCreateMutex(); scan_flags = xEventGroupCreate();
    events = xQueueCreate(16, sizeof(manager_event_t));
    if (!shared_lock || !scan_flags || !events) {
        if (shared_lock) { vSemaphoreDelete(shared_lock); shared_lock = NULL; }
        if (scan_flags) { vEventGroupDelete(scan_flags); scan_flags = NULL; }
        if (events) { vQueueDelete(events); events = NULL; }
        return ESP_ERR_NO_MEM;
    }
    atomic_store(&event_overflow, false);
    atomic_store(&ble_generation, 0);
    esp_event_handler_instance_t wifi_handler, ip_handler, ble_handler;
    esp_err_t ret = esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_network_event, NULL, &wifi_handler);
    if (ret != ESP_OK) { goto fail_queue; }
    ret = esp_event_handler_instance_register(IP_EVENT, ESP_EVENT_ANY_ID, on_network_event, NULL, &ip_handler);
    if (ret != ESP_OK) { goto fail_wifi; }
    ret = esp_event_handler_instance_register(PROTOCOMM_TRANSPORT_BLE_EVENT, ESP_EVENT_ANY_ID, on_network_event, NULL, &ble_handler);
    if (ret != ESP_OK) { goto fail_ip; }
    if (xTaskCreate(wifi_worker, "wifi_manager", 6144, NULL, 4, NULL) != pdPASS) {
        ret = ESP_ERR_NO_MEM;
        esp_event_handler_instance_unregister(PROTOCOMM_TRANSPORT_BLE_EVENT, ESP_EVENT_ANY_ID, ble_handler);
        goto fail_ip;
    }
    worker_started = true;
    ret = start_console();
    if (ret != ESP_OK) { ESP_LOGE(TAG, "USB console unavailable: %s; Wi-Fi worker remains running", esp_err_to_name(ret)); }
    return ret;
fail_ip:
    esp_event_handler_instance_unregister(IP_EVENT, ESP_EVENT_ANY_ID, ip_handler);
fail_wifi:
    esp_event_handler_instance_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_handler);
fail_queue:
    vQueueDelete(events); events = NULL;
    vEventGroupDelete(scan_flags); scan_flags = NULL;
    vSemaphoreDelete(shared_lock); shared_lock = NULL;
    return ret;
}

esp_err_t wifi_manager_init(void)
{
    if (initialized) { return ESP_OK; }
    /* Never erase NVS to recover initialization: other settings live there. */
    ESP_RETURN_ON_ERROR(nvs_flash_init(), TAG, "NVS initialization failed");
    ESP_RETURN_ON_ERROR(esp_netif_init(), TAG, "Network initialization failed");
    esp_err_t ret = esp_event_loop_create_default();
    bool owns_event_loop = ret == ESP_OK;
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) { return ret; }
    bool driver_initialized = false;
    esp_netif_config_t netif_config = ESP_NETIF_DEFAULT_WIFI_STA();
    esp_netif_t *station = esp_netif_new(&netif_config);
    if (!station) { ret = ESP_ERR_NO_MEM; goto fail; }
    ESP_GOTO_ON_ERROR(esp_netif_attach_wifi_station(station), fail, TAG, "Station attachment failed");
    ESP_GOTO_ON_ERROR(esp_wifi_set_default_wifi_sta_handlers(), fail, TAG, "Station handlers failed");
    wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_GOTO_ON_ERROR(esp_wifi_init(&config), fail, TAG, "Wi-Fi initialization failed");
    driver_initialized = true;
    ESP_GOTO_ON_ERROR(esp_wifi_set_storage(WIFI_STORAGE_RAM), fail, TAG, "RAM storage selection failed");
    ESP_GOTO_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), fail, TAG, "Station mode selection failed");
    station_netif = station; initialized = true;
    ESP_LOGI(TAG, "Initialized; Wi-Fi has not been started");
    return ESP_OK;
fail:
    if (driver_initialized) {
        esp_err_t cleanup = esp_wifi_deinit();
        if (cleanup != ESP_OK) { ESP_LOGW(TAG, "Wi-Fi cleanup failed: %s", esp_err_to_name(cleanup)); }
    }
    esp_netif_destroy_default_wifi(station);
    if (owns_event_loop) {
        esp_err_t cleanup = esp_event_loop_delete_default();
        if (cleanup != ESP_OK) { ESP_LOGW(TAG, "Event loop cleanup failed: %s", esp_err_to_name(cleanup)); }
    }
    return ret;
}

