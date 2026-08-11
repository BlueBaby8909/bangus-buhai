/**
 * @file telemetry_service.c
 * @brief MQTT telemetry service — TLS, LWT, local queue, command reception.
 *
 * DESIGN DECISIONS
 * ================
 *
 * TLS (Transport Layer Security):
 *   MQTT runs over TLS so sensor data cannot be eavesdropped in transit and the
 *   device verifies it is talking to the correct broker (not a man-in-the-middle).
 *   We embed the broker's CA certificate at compile-time via CMake's
 *   target_add_binary_data(). This is standard ESP-IDF practice.
 *
 * Authentication: username / password (not client certificates):
 *   Mutual TLS (client certificates) is the gold standard but requires
 *   per-device certificate provisioning — complex for a prototype. Username/
 *   password over TLS is production-appropriate at this scale and can be
 *   upgraded to mTLS later without changing the topic structure.
 *
 * Last Will Testament (LWT):
 *   The broker publishes the LWT message automatically if the MQTT connection
 *   drops without a clean DISCONNECT. This lets the backend mark the device
 *   as "offline" immediately — without waiting for a missed heartbeat.
 *   The LWT topic is: bangusbuhai/devices/{device_id}/status
 *   The LWT payload is: {"status":"offline","device_id":"..."}
 *
 * Local ring buffer (offline queue):
 *   A fixed-size ring buffer (TELEMETRY_QUEUE_DEPTH entries) stores readings
 *   while MQTT is disconnected. On reconnection, the buffer is drained in order.
 *   This prevents data loss during transient network outages.
 *   Ring buffer uses a mutex so it is safe from both the sensor task (writer)
 *   and the telemetry task (reader).
 *
 * Topic structure:
 *   bangusbuhai/devices/{device_id}/telemetry  ← device publishes
 *   bangusbuhai/devices/{device_id}/status     ← device publishes online/offline
 *   bangusbuhai/devices/{device_id}/cmd        ← backend publishes commands TO device
 *
 * Device ID derivation:
 *   Derived from the station MAC address: "BB-" + last 6 bytes as hex.
 *   Example: "BB-AABBCC112233". Unique per device, human-readable on a label.
 *
 * pH design note:
 *   The prototype has no pH sensor. We send the Kconfig default value
 *   (CONFIG_BB_PH_DEFAULT / 100.0f) with ph_source = "default". The backend
 *   stores this flag so the UI and ML pipeline can treat the value appropriately.
 *   Adding a real sensor later = read it, pass the value, set ph_source="sensor".
 */

#include "telemetry_service.h"
#include "app_events.h"
#include "sdkconfig.h"

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"

#include "esp_log.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "esp_heap_caps.h"

#include "mqtt_client.h"
#include "cJSON.h"
#include "relay_driver.h"

/* ── Embedded CA certificate ────────────────────────────────────────────────
 * The file mosquitto_ca.crt must be placed at:
 *   firmware/components/telemetry_service/certs/mosquitto_ca.crt
 * CMakeLists.txt embeds it as a binary symbol. See CMakeLists.txt for details.
 *
 * For development without a real broker, comment out the .verification block
 * in mqtt_cfg and change the URI to mqtt:// (non-TLS). Do NOT ship this to
 * production without re-enabling TLS.
 * ─────────────────────────────────────────────────────────────────────────── */
extern const uint8_t mosquitto_ca_cert_pem_start[] asm("_binary_mosquitto_ca_crt_start");
extern const uint8_t mosquitto_ca_cert_pem_end[]   asm("_binary_mosquitto_ca_crt_end");

/* ── Firmware version ──────────────────────────────────────────────────────── */
#define FW_VERSION "1.0.0"

/* ── Logging tag ───────────────────────────────────────────────────────────── */
static const char *TAG = "TELEMETRY";

/* ── Topic buffers (populated in telemetry_service_init) ───────────────────── */
static char s_device_id[20];             /* "BB-AABBCC112233"          */
static char s_topic_telemetry[80];       /* bangusbuhai/devices/.../telemetry */
static char s_topic_status[80];          /* bangusbuhai/devices/.../status    */
static char s_topic_cmd[80];             /* bangusbuhai/devices/.../cmd       */

/* ── MQTT client handle ────────────────────────────────────────────────────── */
static esp_mqtt_client_handle_t s_client = NULL;
static volatile bool s_mqtt_connected    = false;
static uint32_t      s_mqtt_reconnects   = 0;
static uint32_t      s_seq_number        = 0;

/* ── Local offline ring buffer ─────────────────────────────────────────────── */
typedef struct {
    float       temperature;
    float       turbidity;
    float       ph;
    char        ph_source[8];  /* "sensor" | "default" | "manual" */
    bool        relay_state;
} queued_reading_t;

static queued_reading_t s_ring_buf[TELEMETRY_QUEUE_DEPTH];
static int              s_ring_head  = 0;   /* next write position */
static int              s_ring_tail  = 0;   /* next read position  */
static int              s_ring_count = 0;
static SemaphoreHandle_t s_ring_mutex = NULL;

/* ── Forward declarations ──────────────────────────────────────────────────── */
static void  derive_device_id(void);
static void  build_topics(void);
static char *build_telemetry_json(const queued_reading_t *r);
static void  publish_online_status(void);
static void  drain_queue(void);
static void  ring_buf_push(const queued_reading_t *r);
static bool  ring_buf_pop(queued_reading_t *r);

/* ── MQTT event handler ────────────────────────────────────────────────────── */
static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {

        case MQTT_EVENT_CONNECTED:
            s_mqtt_connected = true;
            ESP_LOGI(TAG, "MQTT connected (reconnects so far: %lu)",
                     (unsigned long)s_mqtt_reconnects);

            /* Subscribe to command topic (QoS 1) */
            esp_mqtt_client_subscribe(s_client, s_topic_cmd, 1);

            /* Publish online status (retained=1 so new subscribers see it) */
            publish_online_status();

            /* Drain any readings that accumulated while offline */
            drain_queue();
            break;

        case MQTT_EVENT_DISCONNECTED:
            s_mqtt_connected = false;
            s_mqtt_reconnects++;
            ESP_LOGW(TAG, "MQTT disconnected — will auto-reconnect");
            break;

        case MQTT_EVENT_SUBSCRIBED:
            ESP_LOGI(TAG, "Subscribed to cmd topic (msg_id=%d)", event->msg_id);
            break;

        case MQTT_EVENT_DATA:
            /* Remote command received on s_topic_cmd */
            ESP_LOGI(TAG, "Command received: topic=%.*s payload=%.*s",
                     event->topic_len, event->topic,
                     event->data_len,  event->data);
                     
            if (strncmp(event->topic, s_topic_cmd, event->topic_len) == 0) {
                cJSON *root = cJSON_ParseWithLength(event->data, event->data_len);
                if (root) {
                    cJSON *relay = cJSON_GetObjectItem(root, "relay");
                    cJSON *state = cJSON_GetObjectItem(root, "state");
                    
                    if (cJSON_IsString(relay) && cJSON_IsBool(state)) {
                        if (strcmp(relay->valuestring, "heater") == 0) {
                            bool turn_on = cJSON_IsTrue(state);
                            relay_driver_set_state(turn_on);
                            ESP_LOGI(TAG, "Relay command executed: %s -> %s", relay->valuestring, turn_on ? "ON" : "OFF");
                        } else {
                            ESP_LOGW(TAG, "Unknown relay requested: %s", relay->valuestring);
                        }
                    } else {
                        ESP_LOGW(TAG, "Invalid command JSON format");
                    }
                    cJSON_Delete(root);
                } else {
                    ESP_LOGE(TAG, "Failed to parse command JSON");
                }
            }
            break;

        case MQTT_EVENT_PUBLISHED:
            ESP_LOGD(TAG, "Message published (msg_id=%d)", event->msg_id);
            break;

        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT error — type=%d",
                     event->error_handle->error_type);
            if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
                ESP_LOGE(TAG, "  Transport err: 0x%x",
                         event->error_handle->esp_transport_sock_errno);
            }
            break;

        default:
            break;
    }
}

/* ── Helpers ───────────────────────────────────────────────────────────────── */

static void derive_device_id(void)
{
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    snprintf(s_device_id, sizeof(s_device_id),
             "BB-%02X%02X%02X%02X%02X%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    ESP_LOGI(TAG, "Device ID: %s", s_device_id);
}

static void build_topics(void)
{
    const char *prefix = CONFIG_BB_MQTT_TOPIC_PREFIX;
    snprintf(s_topic_telemetry, sizeof(s_topic_telemetry),
             "%s/devices/%s/telemetry", prefix, s_device_id);
    snprintf(s_topic_status,    sizeof(s_topic_status),
             "%s/devices/%s/status",    prefix, s_device_id);
    snprintf(s_topic_cmd,       sizeof(s_topic_cmd),
             "%s/devices/%s/cmd",       prefix, s_device_id);
}

/** Publish {"status":"online","device_id":"..."} retained so the backend and
 *  any subscriber can always query the last known state of this device. */
static void publish_online_status(void)
{
    char payload[128];
    snprintf(payload, sizeof(payload),
             "{\"status\":\"online\",\"device_id\":\"%s\"}", s_device_id);
    esp_mqtt_client_publish(s_client, s_topic_status,
                            payload, 0, 1, 1 /* retain */);
}

/** Build the telemetry JSON payload using cJSON so there is no risk of buffer
 *  overflows or malformed strings from manual snprintf formatting. */
static char *build_telemetry_json(const queued_reading_t *r)
{
    int64_t uptime_us = esp_timer_get_time();

    /* Get Wi-Fi RSSI */
    wifi_ap_record_t ap_info = {0};
    int8_t rssi = 0;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        rssi = ap_info.rssi;
    }

    cJSON *root = cJSON_CreateObject();
    if (!root) return NULL;

    cJSON_AddStringToObject(root, "device_id",  s_device_id);
    cJSON_AddNumberToObject(root, "tank_id",    CONFIG_BB_TANK_ID);
    cJSON_AddNumberToObject(root, "seq",        (double)(s_seq_number++));
    cJSON_AddStringToObject(root, "fw_version", FW_VERSION);
    cJSON_AddNumberToObject(root, "uptime_s",   (double)(uptime_us / 1000000LL));

    cJSON *readings = cJSON_AddObjectToObject(root, "readings");
    cJSON_AddNumberToObject(readings, "temperature", (double)r->temperature);
    cJSON_AddNumberToObject(readings, "turbidity",   (double)r->turbidity);
    cJSON_AddNumberToObject(readings, "ph",          (double)r->ph);
    cJSON_AddStringToObject(readings, "ph_source",   r->ph_source);
    cJSON_AddBoolToObject(readings, "relay_on",      r->relay_state);

    cJSON *system = cJSON_AddObjectToObject(root, "system");
    cJSON_AddNumberToObject(system, "free_heap",       (double)esp_get_free_heap_size());
    cJSON_AddNumberToObject(system, "wifi_rssi",       (double)rssi);
    cJSON_AddNumberToObject(system, "mqtt_reconnects", (double)s_mqtt_reconnects);

    char *json_str = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return json_str;  /* caller must cJSON_free() this */
}

/* ── Ring buffer ───────────────────────────────────────────────────────────── */

static void ring_buf_push(const queued_reading_t *r)
{
    xSemaphoreTake(s_ring_mutex, portMAX_DELAY);

    if (s_ring_count >= TELEMETRY_QUEUE_DEPTH) {
        /* Buffer full — overwrite oldest entry (ring behaviour) */
        ESP_LOGW(TAG, "Offline queue full — oldest reading dropped");
        s_ring_tail = (s_ring_tail + 1) % TELEMETRY_QUEUE_DEPTH;
    } else {
        s_ring_count++;
    }

    s_ring_buf[s_ring_head] = *r;
    s_ring_head = (s_ring_head + 1) % TELEMETRY_QUEUE_DEPTH;

    xSemaphoreGive(s_ring_mutex);
}

static bool ring_buf_pop(queued_reading_t *r)
{
    bool got = false;
    xSemaphoreTake(s_ring_mutex, portMAX_DELAY);

    if (s_ring_count > 0) {
        *r = s_ring_buf[s_ring_tail];
        s_ring_tail = (s_ring_tail + 1) % TELEMETRY_QUEUE_DEPTH;
        s_ring_count--;
        got = true;
    }

    xSemaphoreGive(s_ring_mutex);
    return got;
}

/** Publish all buffered readings in order now that MQTT is connected. */
static void drain_queue(void)
{
    queued_reading_t r;
    int drained = 0;

    while (ring_buf_pop(&r)) {
        char *json = build_telemetry_json(&r);
        if (json) {
            int msg_id = esp_mqtt_client_publish(
                s_client, s_topic_telemetry, json, 0, 1 /* QoS */, 0);
            if (msg_id < 0) {
                ESP_LOGW(TAG, "Drain publish failed — re-queuing");
                ring_buf_push(&r);
                cJSON_free(json);
                break;
            }
            ESP_LOGI(TAG, "Drained queued reading (msg_id=%d)", msg_id);
            cJSON_free(json);
            drained++;
        }
    }

    if (drained > 0) {
        ESP_LOGI(TAG, "Drained %d offline readings", drained);
    }
}

/* ── LWT builder ───────────────────────────────────────────────────────────── */

/** Called once during init to build the static LWT payload string.
 *  The LWT is registered with the broker at connection time. If the TCP
 *  connection drops without a clean DISCONNECT, the broker publishes this
 *  retained message automatically — the backend sees the device go offline
 *  within one keepalive interval without any polling. */
static void build_lwt_payload(char *buf, size_t len)
{
    snprintf(buf, len,
             "{\"status\":\"offline\",\"device_id\":\"%s\"}", s_device_id);
}

/* ── Public API ────────────────────────────────────────────────────────────── */

esp_err_t telemetry_service_init(void)
{
    ESP_LOGI(TAG, "Initialising telemetry service");

    s_ring_mutex = xSemaphoreCreateMutex();
    if (!s_ring_mutex) {
        ESP_LOGE(TAG, "Failed to create ring buffer mutex");
        return ESP_ERR_NO_MEM;
    }

    /* Derive device ID from MAC — must be called after esp_wifi_init() */
    derive_device_id();
    build_topics();

    /* Build LWT payload */
    static char lwt_payload[128];
    build_lwt_payload(lwt_payload, sizeof(lwt_payload));

    /* ── MQTT client configuration ─────────────────────────────────────────
     *
     * TLS notes:
     *   - broker.verification.certificate: CA cert to verify the broker.
     *   - No client cert/key: we use username/password, not mutual TLS.
     *   - The CA cert is embedded at compile time (see CMakeLists.txt).
     *
     * For development without a real broker (e.g., local Mosquitto without TLS):
     *   Set CONFIG_BB_MQTT_BROKER_URI to "mqtt://localhost:1883" and
     *   comment out the .verification block below. Re-enable for production.
     * ─────────────────────────────────────────────────────────────────────── */
    const esp_mqtt_client_config_t mqtt_cfg = {
        .broker = {
            .address = {
                .uri = CONFIG_BB_MQTT_BROKER_URI,
            },
#ifdef CONFIG_BB_MQTT_USE_TLS
            .verification = {
                .certificate     = (const char *)mosquitto_ca_cert_pem_start,
                .certificate_len = (mosquitto_ca_cert_pem_end - mosquitto_ca_cert_pem_start),
            },
#endif
        },
        .credentials = {
            .username = CONFIG_BB_MQTT_USERNAME,
            .client_id = s_device_id,
            .authentication = {
                .password = CONFIG_BB_MQTT_PASSWORD,
            },
        },
        .session = {
            .last_will = {
                .topic  = s_topic_status,
                .msg    = lwt_payload,
                .qos    = 1,
                .retain = 1,
            },
            .keepalive           = 60,   /* seconds */
            .disable_clean_session = false,
        },
        .network = {
            .reconnect_timeout_ms = 5000,
            .timeout_ms           = 10000,
        },
        .buffer = {
            .size     = 1024,
            .out_size = 1024,
        },
        .outbox = {
            .limit = 8192,  /* bytes — prevents unbounded memory use */
        },
    };

    s_client = esp_mqtt_client_init(&mqtt_cfg);
    if (!s_client) {
        ESP_LOGE(TAG, "Failed to create MQTT client");
        return ESP_FAIL;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(
        s_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL));

    ESP_ERROR_CHECK(esp_mqtt_client_start(s_client));

    ESP_LOGI(TAG, "MQTT client started — broker: %s", CONFIG_BB_MQTT_BROKER_URI);
    ESP_LOGI(TAG, "Telemetry topic : %s", s_topic_telemetry);
    ESP_LOGI(TAG, "Status topic    : %s", s_topic_status);
    ESP_LOGI(TAG, "Command topic   : %s", s_topic_cmd);

    return ESP_OK;
}

esp_err_t telemetry_service_send_data(float temperature, float turbidity,
                                      float ph, const char *ph_source, bool relay_state)
{
    queued_reading_t r = {
        .temperature = temperature,
        .turbidity   = turbidity,
        .ph          = ph,
        .relay_state = relay_state,
    };
    strlcpy(r.ph_source, ph_source ? ph_source : "default", sizeof(r.ph_source));

    if (!s_mqtt_connected) {
        /* Store in local ring buffer — will be sent on next reconnect */
        ring_buf_push(&r);
        ESP_LOGD(TAG, "MQTT offline — reading queued (queue size: %d)", s_ring_count);
        return ESP_OK;
    }

    char *json = build_telemetry_json(&r);
    if (!json) {
        ESP_LOGE(TAG, "Failed to allocate JSON payload");
        return ESP_ERR_NO_MEM;
    }

    int msg_id = esp_mqtt_client_publish(
        s_client, s_topic_telemetry, json, 0, 1 /* QoS 1 */, 0);

    if (msg_id < 0) {
        ESP_LOGW(TAG, "Publish failed — queueing reading");
        ring_buf_push(&r);
        cJSON_free(json);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Published telemetry (msg_id=%d seq=%lu): T=%.1f°C Turb=%.1f NTU pH=%.2f[%s]",
             msg_id, (unsigned long)(s_seq_number - 1),
             temperature, turbidity, ph, r.ph_source);

    cJSON_free(json);
    return ESP_OK;
}

bool telemetry_service_is_mqtt_connected(void)
{
    return s_mqtt_connected;
}
