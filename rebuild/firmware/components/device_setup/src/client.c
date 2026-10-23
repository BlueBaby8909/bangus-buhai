#include "device_setup.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "device_setup_material.h"
#include "telemetry.h"
#include "cJSON.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

extern const char setup_backend_ca[], mqtt_device_key[];
static const char *TAG = "device_setup";
static char identity[16];
static portMUX_TYPE mutex = portMUX_INITIALIZER_UNLOCKED;
static device_setup_config_t active;
static bool ready, started;
static char response[4097];
static size_t response_length;
static bool response_overflow;
static unsigned retry_after;

static void publish(const device_setup_config_t *value, bool enabled)
{
    portENTER_CRITICAL(&mutex);
    if (value) { active = *value; }
    ready = enabled;
    portEXIT_CRITICAL(&mutex);
}

bool device_setup_binding(char out[37])
{
    portENTER_CRITICAL(&mutex);
    bool enabled = ready && active.confirmed && !active.archived && active.binding_id[0];
    if (enabled) { memcpy(out, active.binding_id, 37); } else { out[0] = 0; }
    portEXIT_CRITICAL(&mutex);
    return enabled;
}

static esp_err_t on_http(esp_http_client_event_t *event)
{
    if (event->event_id == HTTP_EVENT_ON_DATA) {
        if (event->data_len < 0 || response_length + event->data_len > sizeof(response)-1) {
            response_overflow = true; return ESP_ERR_INVALID_SIZE;
        }
        memcpy(response + response_length, event->data, event->data_len);
        response_length += event->data_len; response[response_length] = 0;
    } else if (event->event_id == HTTP_EVENT_ON_HEADER && event->header_key && event->header_value &&
            !strcasecmp(event->header_key, "Retry-After")) {
        char *end; unsigned long value = strtoul(event->header_value, &end, 10);
        if (!*end && value >= 1 && value <= 300) { retry_after = value; }
    }
    return ESP_OK;
}

static esp_err_t post(const char *path, const char *body)
{
    char url[256];
    int size = snprintf(url, sizeof(url), "%s/api/device/v1/%s", BB_DEVICE_SETUP_URL, path);
    if (size <= 0 || size >= sizeof(url) || strncmp(url, "https://", 8)) { return ESP_ERR_INVALID_ARG; }
    response_length = 0; response[0] = 0; response_overflow = false;
    const esp_http_client_config_t config = {
        .url = url, .cert_pem = setup_backend_ca, .method = HTTP_METHOD_POST,
        .timeout_ms = 5000, .disable_auto_redirect = true, .event_handler = on_http,
        .buffer_size = 1024, .buffer_size_tx = 1536, .keep_alive_enable = false,
        .skip_cert_common_name_check = false,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) { return ESP_ERR_NO_MEM; }
    esp_err_t ret = esp_http_client_set_header(client, "Content-Type", "application/json");
    if (ret == ESP_OK) { ret = esp_http_client_set_post_field(client, body, strlen(body)); }
    if (ret == ESP_OK) { ret = esp_http_client_perform(client); }
    int status = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
    if (response_overflow) { return ESP_ERR_INVALID_SIZE; }
    if (ret == ESP_OK && status != 200) {
        ESP_LOGW(TAG, "Setup request deferred: HTTP %d", status);
        ret = status == 429 ? ESP_ERR_TIMEOUT : ESP_ERR_INVALID_RESPONSE;
    }
    return ret;
}

static esp_err_t exchange(const char *purpose, const device_setup_config_t *config, device_setup_config_t *out)
{
    char request[1024];
    if (!strcmp(purpose, "sync")) {
        snprintf(request, sizeof(request), "{\"device_id\":\"%s\",\"purpose\":\"sync\"}", identity);
    } else {
        snprintf(request, sizeof(request), "{\"device_id\":\"%s\",\"purpose\":\"confirm\",\"configuration_revision\":%lu,\"configuration_digest\":\"%s\"}",
            identity, (unsigned long)config->revision, config->digest);
    }
    esp_err_t ret = post("challenges", request);
    if (ret != ESP_OK) { return ret; }
    ret = device_setup_proof(response, response_length, identity, purpose, config, time(NULL),
        mqtt_device_key, request, sizeof(request));
    if (ret != ESP_OK) { return ret; }
    ret = post("proofs", request);
    if (ret != ESP_OK) { return ret; }
    cJSON *root = telemetry_parse_json(response, response_length, true);
    cJSON *document = root ? cJSON_GetObjectItemCaseSensitive(root, "configuration") : NULL;
    cJSON *state = root ? cJSON_GetObjectItemCaseSensitive(root, "state") : NULL;
    if (!root || cJSON_GetArraySize(root) != 2 || !cJSON_IsString(state)) { cJSON_Delete(root); return ESP_ERR_INVALID_RESPONSE; }
    if (cJSON_IsNull(document) && !strcmp(state->valuestring, "unclaimed")) {
        cJSON_Delete(root); return ESP_ERR_NOT_FOUND;
    }
    char *json = cJSON_PrintUnformatted(document);
    ret = json ? device_setup_parse(json, strlen(json), identity, out) : ESP_ERR_INVALID_RESPONSE;
    if (ret == ESP_OK && strcmp(state->valuestring, out->confirmed ? "complete" : "awaiting_confirmation")) {
        ret = ESP_ERR_INVALID_RESPONSE;
    }
    cJSON_free(json); cJSON_Delete(root); return ret;
}

static void run(void *argument)
{
    (void)argument;
    unsigned delay = 30;
    for (;;) {
        esp_netif_t *station = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
        esp_netif_ip_info_t ip;
        if (!station || !esp_netif_is_netif_up(station) || esp_netif_get_ip_info(station, &ip) != ESP_OK ||
                !ip.ip.addr || time(NULL) < 1700000000) { vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
        retry_after = 0;
        device_setup_config_t next;
        esp_err_t ret = exchange("sync", NULL, &next);
        if (ret == ESP_ERR_NOT_FOUND) {
            publish(NULL, false);
            ESP_LOGI(TAG, "Device unclaimed; sensing continues, new telemetry paused");
            delay = 30;
        } else if (ret == ESP_OK) {
            bool changed = !ready || next.revision != active.revision || strcmp(next.digest, active.digest) ||
                next.confirmed != active.confirmed;
            if (changed) { publish(NULL, false); }
            /* Avoid writes on ordinary unchanged polls. Pending durable state is
             * published before HTTPS confirmation; capture stays paused. */
            if (changed || next.confirmed != active.confirmed) { ret = device_setup_save(&next); }
            if (ret == ESP_OK) {
                publish(&next, true);
                if (!next.confirmed) {
                    ret = exchange("confirm", &next, &next);
                    if (ret == ESP_OK && next.confirmed) { ret = device_setup_save(&next); }
                    else if (ret == ESP_OK) { ret = ESP_ERR_INVALID_RESPONSE; }
                    if (ret == ESP_OK) { publish(&next, true); }
                }
            }
            if (ret != ESP_OK) { publish(NULL, false); }
            else if (changed) { ESP_LOGI(TAG, "Configuration saved and confirmed: revision=%lu binding=%s capture=%s",
                (unsigned long)next.revision, next.binding_id[0] ? next.binding_id : "none",
                next.binding_id[0] && !next.archived ? "enabled" : "paused"); }
            delay = ret == ESP_OK ? 30 : (delay < 150 ? delay*2 : 300);
        } else {
            ESP_LOGW(TAG, "Setup unavailable: %s; saved assignment retained", esp_err_to_name(ret));
            delay = delay < 150 ? delay*2 : 300;
        }
        if (retry_after > delay) { delay = retry_after; }
        vTaskDelay(pdMS_TO_TICKS(delay*1000));
    }
}

esp_err_t device_setup_start(const char *device)
{
    if (started || !device || strlen(device) != 15) { return ESP_ERR_INVALID_STATE; }
    strcpy(identity, device);
    device_setup_config_t saved;
    esp_err_t ret = device_setup_load(device, &saved);
    if (ret == ESP_OK) {
        publish(&saved, true);
        ESP_LOGI(TAG, "Saved configuration restored: revision=%lu confirmed=%lu",
            (unsigned long)saved.revision, (unsigned long)saved.confirmed);
    } else if (ret != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGE(TAG, "Configuration storage unavailable: %s; no automatic erase", esp_err_to_name(ret));
        return ret;
    }
    if (xTaskCreate(run, "device_setup", 12288, NULL, 2, NULL) != pdPASS) { return ESP_ERR_NO_MEM; }
    started = true; return ESP_OK;
}
