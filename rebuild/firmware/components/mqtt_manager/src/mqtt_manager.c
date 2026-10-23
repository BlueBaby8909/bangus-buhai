#include "mqtt_manager.h"

#include <stdbool.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include "sdkconfig.h"
#include "esp_crt_bundle.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_app_desc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "mqtt_client.h"
#include "telemetry.h"
#include "device_setup.h"
#include "command_manager.h"

#if !CONFIG_MBEDTLS_HAVE_TIME_DATE || !CONFIG_MBEDTLS_CERTIFICATE_BUNDLE || !CONFIG_MQTT_TRANSPORT_SSL
#error "T07 MQTT requires TLS, the CA bundle and certificate validity-date checks"
#endif

extern const char mqtt_device_cert[];
extern const char mqtt_device_key[];
#ifdef BB_MQTT_PASSWORD_AUTH
#include "device_mqtt_login.h"
_Static_assert(sizeof(BB_MQTT_PASSWORD) >= 33 && sizeof(BB_MQTT_PASSWORD) <= 257,
               "Private MQTT password must be 32-256 characters");
#define MQTT_AUTH_DESCRIPTION "device login"
#else
#define MQTT_AUTH_DESCRIPTION "device certificate"
#endif

static const char *TAG = "mqtt_manager";
#define BEGIN_WORK BIT0
#define WAKE_WORKER BIT1
#define MQTT_DISCONNECTED BIT3
#define MQTT_SIGNALS MQTT_DISCONNECTED
#define MAX_BACKOFF_MS 300000U
#define CONNECT_WINDOW_US (30LL * 1000000)

static bool started;
static esp_netif_t *station;
static TaskHandle_t worker;
static atomic_bool time_ready;
static char device_id[16];
static char boot_id[37], connection_id[37], status_topic[80], telemetry_topic[80], ack_topic[80], quarantine_topic[96];
static bool assembly_quarantine;
static bool assembly_command;
static char command_topic[96], result_topic[96];
static QueueHandle_t commands;
static StaticQueue_t command_queue_storage;
static uint8_t command_queue_bytes[2 * sizeof(telemetry_ack_message_t)];
/* Immutable while a client exists; destroy joins its task before reuse. */
static char online_status[256], offline_status[256];

typedef enum { TRANSPORT_PUBLISHED, TRANSPORT_SUBSCRIBED, TRANSPORT_DELETED } transport_kind_t;
typedef struct { transport_kind_t kind; int mid; bool accepted; } transport_event_t;
static QueueHandle_t transport_events, acknowledgements;
static StaticQueue_t transport_queue_storage, ack_queue_storage;
static uint8_t transport_queue_bytes[8 * sizeof(transport_event_t)];
static uint8_t ack_queue_bytes[2 * sizeof(telemetry_ack_message_t)];
/* Only the SDK MQTT task touches assembly; only the worker parses completed ACKs. */
static telemetry_ack_assembly_t assembly;
static telemetry_ack_message_t received_ack;
static atomic_uint inbox_dropped;

static void receive_ack(const esp_mqtt_event_t *event)
{
    if (event->current_data_offset < 0 || event->total_data_len < 0 || event->data_len < 0) {
        assembly.active = false; return;
    }
    bool acknowledgement = event->topic && event->topic_len == (int)strlen(ack_topic) &&
                         !memcmp(event->topic, ack_topic, (size_t)event->topic_len);
    bool quarantine = event->topic && event->topic_len == (int)strlen(quarantine_topic) &&
                         !memcmp(event->topic, quarantine_topic, (size_t)event->topic_len);
    bool command = event->topic && event->topic_len == (int)strlen(command_topic) &&
                         !memcmp(event->topic, command_topic, (size_t)event->topic_len) && event->qos == 1;
    if (!event->current_data_offset) { assembly_quarantine = quarantine; assembly_command = command; }
    bool topic_matches = acknowledgement || quarantine || command;
    if (telemetry_ack_fragment(&assembly, topic_matches, event->retain, event->msg_id,
                              (size_t)event->current_data_offset, (size_t)event->total_data_len,
                              event->data, (size_t)event->data_len)) {
        assembly.message.quarantine = assembly_quarantine;
        if (xQueueSend(assembly_command ? commands : acknowledgements, &assembly.message, 0) != pdTRUE) { atomic_fetch_add(&inbox_dropped, 1); }
    }
}

static void notify_worker(uint32_t bits)
{
    xTaskNotify(worker, bits, eSetBits);
}

static void on_mqtt_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    (void)base;
    const esp_mqtt_event_t *event = data;
    switch (id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT connected to HiveMQ using %s (%s)", MQTT_AUTH_DESCRIPTION, device_id);
        notify_worker(WAKE_WORKER);
        break;
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT disconnected; credentials retained");
        notify_worker(MQTT_DISCONNECTED);
        break;
    case MQTT_EVENT_PUBLISHED:
    case MQTT_EVENT_SUBSCRIBED:
    case MQTT_EVENT_DELETED: {
        transport_event_t notice = {
            .kind = id == MQTT_EVENT_PUBLISHED ? TRANSPORT_PUBLISHED :
                    id == MQTT_EVENT_SUBSCRIBED ? TRANSPORT_SUBSCRIBED : TRANSPORT_DELETED,
            .mid = event->msg_id,
            .accepted = id != MQTT_EVENT_SUBSCRIBED ||
                (event->data_len == 3 && event->data && (unsigned char)event->data[0] <= 1 && (unsigned char)event->data[1] <= 1 && (unsigned char)event->data[2] == 1)
        };
        if (xQueueSend(transport_events, &notice, 0) != pdTRUE) { atomic_fetch_add(&inbox_dropped, 1); }
        notify_worker(WAKE_WORKER);
        break;
    }
    case MQTT_EVENT_DATA:
        receive_ack(event);
        notify_worker(WAKE_WORKER);
        break;
    case MQTT_EVENT_ERROR: {
        const esp_mqtt_error_codes_t *error = event ? event->error_handle : NULL;
        if (!error) {
            ESP_LOGE(TAG, "MQTT error without diagnostic details");
        } else if (error->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
            ESP_LOGE(TAG, "MQTT transport error: esp=%s tls=0x%x verify=0x%x socket_errno=%d",
                     esp_err_to_name(error->esp_tls_last_esp_err),
                     (unsigned)error->esp_tls_stack_err,
                     (unsigned)error->esp_tls_cert_verify_flags,
                     error->esp_transport_sock_errno);
        } else if (error->error_type == MQTT_ERROR_TYPE_CONNECTION_REFUSED) {
            ESP_LOGE(TAG, "MQTT broker refused connection: code=%d",
                     (int)error->connect_return_code);
        } else {
            ESP_LOGE(TAG, "MQTT error: type=%d", (int)error->error_type);
        }
        break;
    }
    default:
        break;
    }
}

static void on_synchronized_time(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    if (base != NETIF_SNTP_EVENT || id != NETIF_SNTP_TIME_SYNC || !data) {
        return;
    }
    const esp_netif_sntp_time_sync_t *event = data;
    if (event->tv.tv_sec > 0) {
        atomic_store(&time_ready, true);
        notify_worker(WAKE_WORKER);
    }
}

static bool network_ready(void)
{
    esp_netif_ip_info_t ip;
    return station && atomic_load(&time_ready) && time(NULL) > 0 &&
        esp_netif_is_netif_up(station) &&
        esp_netif_get_ip_info(station, &ip) == ESP_OK && ip.ip.addr != 0;
}

static void make_uuid(char out[37])
{
    uint8_t bytes[16];
    esp_fill_random(bytes, sizeof(bytes));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    static const char hex[] = "0123456789abcdef";
    unsigned pos = 0;
    for (unsigned i = 0; i < sizeof(bytes); ++i) {
        if (i == 4 || i == 6 || i == 8 || i == 10) { out[pos++] = '-'; }
        out[pos++] = hex[bytes[i] >> 4];
        out[pos++] = hex[bytes[i] & 0x0f];
    }
    out[pos] = 0;
}

static esp_err_t prepare_status(void)
{
    /* Connection randomness is generated after radio startup; boot ID is shared. */
    make_uuid(connection_id);
    const char *format = "{\"schema_version\":1,\"device_id\":\"%s\","
        "\"boot_id\":\"%s\",\"connection_id\":\"%s\",\"state\":\"%s\"}";
    int online_len = snprintf(online_status, sizeof(online_status), format,
                             device_id, boot_id, connection_id, "online");
    int offline_len = snprintf(offline_status, sizeof(offline_status), format,
                              device_id, boot_id, connection_id, "offline");
    if (online_len < 0 || (size_t)online_len >= sizeof(online_status) ||
        offline_len < 0 || (size_t)offline_len >= sizeof(offline_status)) {
        return ESP_ERR_INVALID_SIZE;
    }
    return ESP_OK;
}

static esp_err_t begin_connection(esp_mqtt_client_handle_t *out)
{
    esp_err_t ret = prepare_status();
    if (ret != ESP_OK) { return ret; }
#ifdef BB_MQTT_PASSWORD_AUTH
    /* Fail closed if a different device's private build material was selected. */
    if (strcmp(BB_MQTT_USERNAME, device_id)) { return ESP_ERR_INVALID_ARG; }
#endif
    const esp_mqtt_client_config_t config = {
        .broker.address.uri = "mqtts://steadyalkali-3ff7468c.a01.euc1.aws.hivemq.cloud:8883",
        .broker.verification.crt_bundle_attach = esp_crt_bundle_attach,
        .broker.verification.skip_cert_common_name_check = false,
        .credentials.client_id = device_id,
#ifdef BB_MQTT_PASSWORD_AUTH
        .credentials.username = BB_MQTT_USERNAME,
        .credentials.authentication.password = BB_MQTT_PASSWORD,
#else
        .credentials.authentication.certificate = mqtt_device_cert,
        .credentials.authentication.key = mqtt_device_key,
#endif
        .session.protocol_ver = MQTT_PROTOCOL_V_3_1_1,
        .session.keepalive = 30,
        .session.last_will.topic = status_topic,
        .session.last_will.msg = offline_status,
        .session.last_will.qos = 1,
        .session.last_will.retain = 1,
        .network.timeout_ms = 10000,
        .network.disable_auto_reconnect = true,
        .outbox.limit = 16384,
    };
    esp_mqtt_client_handle_t next = esp_mqtt_client_init(&config);
    if (!next) { return ESP_ERR_NO_MEM; }
    ret = esp_mqtt_client_register_event(next, MQTT_EVENT_ANY, on_mqtt_event, NULL);
    if (ret == ESP_OK) { ret = esp_mqtt_client_start(next); }
    if (ret != ESP_OK) {
        esp_mqtt_client_destroy(next);
        return ret;
    }
    *out = next;
    ESP_LOGI(TAG, "MQTT attempt: connection_id=%s; verified TLS and retained QoS 1 Will",
             connection_id);
    return ESP_OK;
}

static void schedule_retry(uint32_t *base_ms, int64_t *retry_at)
{
    uint32_t low = *base_ms * 3 / 4;
    uint32_t high = *base_ms + *base_ms / 4;
    if (high > MAX_BACKOFF_MS) { high = MAX_BACKOFF_MS; }
    uint32_t delay_ms = low + esp_random() % (high - low + 1);
    *retry_at = esp_timer_get_time() + (int64_t)delay_ms * 1000;
    *base_ms = *base_ms >= MAX_BACKOFF_MS / 2 ? MAX_BACKOFF_MS : *base_ms * 2;
    ESP_LOGI(TAG, "MQTT retry in %lu ms; network/time must be ready", (unsigned long)delay_ms);
}

static bool binding_current(const char *binding)
{
    char current[37];
    return device_setup_binding(current) && !strcmp(current, binding);
}

static int64_t synchronized_utc_us(void)
{
    struct timeval tv;
    return atomic_load(&time_ready) && gettimeofday(&tv, NULL) == 0 ?
        (int64_t)tv.tv_sec * 1000000 + tv.tv_usec : 0;
}

static void mqtt_worker(void *arg)
{
    (void)arg;
    uint32_t signals = 0;
    /* Registration can fail during startup: no client exists until released. */
    do { xTaskNotifyWait(0, UINT32_MAX, &signals, portMAX_DELAY); }
    while (!(signals & BEGIN_WORK));

    esp_mqtt_client_handle_t client = NULL;
    bool online_queued = false;
    bool subscribed = false, transport_pending = false;
    int status_mid = -1, subscription_mid = -1, telemetry_mid = -1;
    char sent_boot[37] = {0};
    uint32_t sent_seq = 0, reconnects = 0;
    bool connected_before = false;
#ifdef BB_T13A_CUSTODY_EXERCISE
    bool custody_exercise_attempted = false;
#endif
    uint32_t backoff_ms = 1000;
    int64_t retry_at = 0, connect_deadline = 0, subscription_retry_at = 0;
    int64_t subscription_deadline = 0, telemetry_retry_at = 0;
    int64_t command_result_retry_at = 0;
    telemetry_config_t telemetry_config = {
        .device_id = device_id, .boot_id = boot_id,
        .binding_id = NULL,
        .fw_version = esp_app_get_description()->version
    };
    esp_err_t telemetry_error = telemetry_init(&telemetry_config);
    if (telemetry_error != ESP_OK) {
        ESP_LOGE(TAG, "Telemetry storage unavailable: %s; flash updated partition table if absent",
                 esp_err_to_name(telemetry_error));
    }
    esp_err_t command_error = command_manager_init(device_id, boot_id, binding_current);
    if (command_error != ESP_OK) { ESP_LOGE(TAG, "Command storage unavailable: %s", esp_err_to_name(command_error)); }
    ESP_LOGI(TAG, "MQTT waiting for station IP and synchronized UTC");
    for (;;) {
        int64_t now = esp_timer_get_time(), wake_at = now + 1000000;
        if (retry_at > now && retry_at < wake_at) { wake_at = retry_at; }
        if (connect_deadline && connect_deadline < wake_at) { wake_at = connect_deadline; }
        TickType_t wait = wake_at > now ? pdMS_TO_TICKS((wake_at - now + 999) / 1000) : 0;
        if (wake_at > now && wait == 0) { wait = 1; }
        signals = 0;
        xTaskNotifyWait(0, UINT32_MAX, &signals, wait);
        now = esp_timer_get_time();

        /* ACKs from a dying connection still refer to immutable durable events. */
        while (xQueueReceive(acknowledgements, &received_ack, 0) == pdTRUE) {
            esp_err_t ret = received_ack.quarantine ?
                telemetry_accept_quarantine_receipt(received_ack.data, received_ack.length) :
                telemetry_accept_ack(received_ack.data, received_ack.length);
            if (!received_ack.quarantine && ret != ESP_OK) {
                esp_err_t command_ret = command_manager_ack(received_ack.data, received_ack.length);
                if (command_ret == ESP_OK) { ret = ESP_OK; command_result_retry_at = 0; }
            }
            if (ret != ESP_OK && ret != ESP_ERR_NOT_FOUND) {
                ESP_LOGW(TAG, "Application acknowledgement ignored: %s", esp_err_to_name(ret));
            }
        }
        unsigned lost_notices = atomic_exchange(&inbox_dropped, 0);
        if (lost_notices) { ESP_LOGW(TAG, "MQTT inbox dropped %u notices; durable readings remain pending", lost_notices); }

        char runtime_binding[37];
        bool capture_enabled = device_setup_binding(runtime_binding);
        telemetry_set_binding(capture_enabled ? runtime_binding : NULL);
        command_manager_poll(synchronized_utc_us(), now / 1000);
        while (xQueueReceive(commands, &received_ack, 0) == pdTRUE) {
            esp_err_t ret = command_manager_receive(received_ack.data, received_ack.length,
                capture_enabled ? runtime_binding : NULL, synchronized_utc_us(), esp_timer_get_time() / 1000);
            if (ret != ESP_OK) { ESP_LOGW(TAG, "Command refused: %s", esp_err_to_name(ret)); }
            command_result_retry_at = 0;
        }
        bool exercise_followup = false;
#ifdef BB_T13A_CUSTODY_EXERCISE
        /* Opt-in lab build only. Queue owner creates a new diagnostic identity;
         * no saved configuration or existing queued event is ever modified. */
        if (!custody_exercise_attempted && capture_enabled && subscribed &&
            network_ready() && telemetry_ready() && telemetry_pending() == 0) {
            custody_exercise_attempted = true;
            sensor_reading_t snapshot;
            relay_control_state_t relay;
            char unknown_binding[37];
            make_uuid(unknown_binding);
            esp_err_t ret = sensor_service_try_get_latest(&snapshot, 20);
            const relay_control_state_t *relay_view = relay_control_get_state(&relay) == ESP_OK ? &relay : NULL;
            if (ret == ESP_OK) { ret = telemetry_set_binding(unknown_binding); }
            if (ret == ESP_OK) {
                /* Deliberately uncertain diagnostic capture, destined for quarantine. */
                ESP_LOGW(TAG, "T13A DIAGNOSTIC: new unknown-binding reading; excluded from tank history");
                ret = telemetry_capture(&snapshot, relay_view, NULL, reconnects);
            }
            telemetry_set_binding(runtime_binding);
            if (ret == ESP_OK) {
                exercise_followup = true;
                ESP_LOGI(TAG, "T13A DIAGNOSTIC: normal follow-up uses unchanged saved assignment");
            } else {
                ESP_LOGE(TAG, "T13A diagnostic capture unavailable: %s", esp_err_to_name(ret));
            }
        }
#endif
        if (capture_enabled && (exercise_followup || telemetry_capture_due(now))) {
            if (telemetry_ready()) {
                sensor_reading_t snapshot;
                relay_control_state_t relay;
                esp_err_t ret = sensor_service_try_get_latest(&snapshot, 20);
                const relay_control_state_t *relay_view = relay_control_get_state(&relay) == ESP_OK ? &relay : NULL;
                time_t captured_utc = 0;
                struct timeval tv;
                bool synchronized = atomic_load(&time_ready) && gettimeofday(&tv, NULL) == 0;
                if (ret == ESP_OK) {
                    int64_t delta_ms = esp_timer_get_time() / 1000 - snapshot.capture_uptime_ms;
                    if (synchronized) {
                        int64_t capture_ms = (int64_t)tv.tv_sec * 1000 + tv.tv_usec / 1000 - delta_ms;
                        synchronized = capture_ms > 0;
                        captured_utc = (time_t)(capture_ms / 1000);
                    }
                    ret = telemetry_capture(&snapshot, relay_view, synchronized ? &captured_utc : NULL, reconnects);
                }
                if (ret != ESP_OK) { ESP_LOGW(TAG, "Telemetry capture failed: %s", esp_err_to_name(ret)); }
            }
        }

        bool connected = false;
        bool failed = client && (signals & MQTT_DISCONNECTED);
        if (client && !failed) {
            esp_mqtt_client_connection_state_t state = esp_mqtt_client_get_state(client);
            connected = state == MQTT_CLIENT_STATE_CONNECTED;
            if (connected) {
                connect_deadline = 0;
            } else if (state == MQTT_CLIENT_STATE_WAITING_RECONNECT || !connect_deadline ||
                       now >= connect_deadline) {
                if (connect_deadline && now >= connect_deadline) {
                    ESP_LOGW(TAG, "MQTT connection deadline expired");
                }
                failed = true;
            }
        }
        if (failed) {
            esp_err_t ret = esp_mqtt_client_destroy(client);
            if (ret != ESP_OK) {
                ESP_LOGE(TAG, "MQTT cleanup failed: %s", esp_err_to_name(ret));
                notify_worker(MQTT_DISCONNECTED);
                vTaskDelay(pdMS_TO_TICKS(1000));
                continue;
            }
            client = NULL;
            online_queued = false;
            subscribed = transport_pending = false;
            status_mid = subscription_mid = telemetry_mid = -1;
            subscription_deadline = subscription_retry_at = telemetry_retry_at = 0;
            sent_boot[0] = 0;
            assembly.active = false;
            xQueueReset(transport_events);
            /* Completed application ACKs are safe across clients; drain next loop. */
            connect_deadline = 0;
            /* Destroy joins the old SDK task: no callback/outbox crosses attempts. */
            ulTaskNotifyValueClear(NULL, MQTT_SIGNALS);
            schedule_retry(&backoff_ms, &retry_at);
            continue;
        }
        transport_event_t notice;
        while (xQueueReceive(transport_events, &notice, 0) == pdTRUE) {
            if (!client || !connected) { continue; }
            if (notice.kind == TRANSPORT_SUBSCRIBED && notice.mid == subscription_mid) {
                subscribed = notice.accepted;
                subscription_mid = -1;
                subscription_deadline = 0;
                subscription_retry_at = now + TELEMETRY_ACK_RETRY_US;
                if (subscribed) { ESP_LOGI(TAG, "Application acknowledgement subscription ready"); }
                else { ESP_LOGW(TAG, "Acknowledgement subscription denied; readings retained"); }
            } else if (notice.kind == TRANSPORT_DELETED && notice.mid == status_mid) {
                online_queued = false; status_mid = -1;
                schedule_retry(&backoff_ms, &retry_at);
            } else if (notice.kind == TRANSPORT_DELETED && notice.mid == subscription_mid) {
                subscribed = false; subscription_mid = -1;
                subscription_deadline = 0; subscription_retry_at = now + TELEMETRY_ACK_RETRY_US;
            } else if (notice.kind == TRANSPORT_PUBLISHED && notice.mid == status_mid) {
                status_mid = -1;
                backoff_ms = 1000;
                if (connected_before && reconnects < UINT32_MAX) { ++reconnects; }
                connected_before = true;
                ESP_LOGI(TAG, "Online status PUBACK received; connection_id=%s", connection_id);
            } else if (notice.mid == telemetry_mid &&
                       (notice.kind == TRANSPORT_PUBLISHED || notice.kind == TRANSPORT_DELETED)) {
                transport_pending = false; telemetry_mid = -1;
                telemetry_retry_at = now + TELEMETRY_ACK_RETRY_US;
                ESP_LOGI(TAG, "Telemetry transport %s; %lu durable readings pending application acknowledgement",
                         notice.kind == TRANSPORT_PUBLISHED ? "PUBACK" : "expiry", (unsigned long)telemetry_pending());
            }
        }

        if (!network_ready()) { continue; }
        if (!client && now >= retry_at) {
            ulTaskNotifyValueClear(NULL, MQTT_SIGNALS);
            esp_err_t ret = begin_connection(&client);
            if (ret != ESP_OK) {
                ESP_LOGW(TAG, "MQTT attempt start failed: %s", esp_err_to_name(ret));
                schedule_retry(&backoff_ms, &retry_at);
            } else {
                retry_at = 0;
                connect_deadline = esp_timer_get_time() + CONNECT_WINDOW_US;
            }
        } else if (client && connected && !online_queued && now >= retry_at) {
            int mid = esp_mqtt_client_enqueue(client, status_topic, online_status, 0, 1, 1, true);
            if (mid < 0) {
                ESP_LOGW(TAG, "Online status enqueue failed: %d", mid);
                schedule_retry(&backoff_ms, &retry_at);
            } else {
                online_queued = true;
                status_mid = mid;
                retry_at = 0;
                ESP_LOGI(TAG, "Retained online status queued: msg_id=%d; connection_id=%s",
                         mid, connection_id);
            }
        }
        if (client && connected && online_queued) {
            if (!subscribed && subscription_mid < 0 && now >= subscription_retry_at) {
                esp_mqtt_topic_t topics[] = {{.filter = ack_topic, .qos = 1}, {.filter = quarantine_topic, .qos = 1}, {.filter = command_topic, .qos = 1}};
                subscription_mid = esp_mqtt_client_subscribe_multiple(client, topics, 3);
                subscription_retry_at = now + TELEMETRY_ACK_RETRY_US;
                if (subscription_mid >= 0) { subscription_deadline = now + CONNECT_WINDOW_US; }
            }
            if (subscription_mid >= 0 && now >= subscription_deadline) {
                ESP_LOGW(TAG, "Acknowledgement SUBACK missing; readings retained");
                if (esp_mqtt_client_get_outbox_size(client) == 0) {
                    /* SDK completed/expired it but its callback was lost. */
                    subscription_mid = -1;
                    subscription_retry_at = now;
                } else { subscription_deadline = now + MAX_BACKOFF_MS * 1000LL; }
            }
            if (transport_pending && esp_mqtt_client_get_outbox_size(client) == 0) {
                /* A callback may be dropped, or SDK outbox expiry reporting disabled.
                 * Neither case can wedge replay or acknowledge durable storage. */
                transport_pending = false; telemetry_mid = -1;
                telemetry_retry_at = now + TELEMETRY_ACK_RETRY_US;
            }
            if (subscribed && !transport_pending && telemetry_ready()) {
                const command_result_wire_t *command_result = NULL;
                if (now >= command_result_retry_at && command_manager_peek(&command_result) == ESP_OK) {
                    int mid = esp_mqtt_client_enqueue(client, result_topic, command_result->payload,
                        command_result->length, 1, 0, true);
                    command_result_retry_at = now + TELEMETRY_ACK_RETRY_US;
                    if (mid >= 0) { ESP_LOGI(TAG, "Durable command result queued: msg_id=%d", mid); }
                }
                const telemetry_event_t *event = NULL;
                if (telemetry_peek(&event) == ESP_OK) {
                    bool different = sent_seq != event->seq || strcmp(sent_boot, event->boot_id);
                    if (different || now >= telemetry_retry_at) {
                        /* Remember a failed attempt too, so enqueue errors stay bounded. */
                        strcpy(sent_boot, event->boot_id); sent_seq = event->seq;
                        int mid = esp_mqtt_client_enqueue(client, telemetry_topic, event->payload,
                                                          (int)event->length, 1, 0, true);
                        telemetry_retry_at = now + TELEMETRY_ACK_RETRY_US;
                        if (mid >= 0) {
                            telemetry_mid = mid; transport_pending = true;
                            ESP_LOGI(TAG, "Telemetry queued: boot=%s seq=%lu; %lu pending", sent_boot,
                                     (unsigned long)sent_seq, (unsigned long)telemetry_pending());
                        } else {
                            ESP_LOGW(TAG, "Telemetry enqueue failed: %d; reading remains durable", mid);
                        }
                    }
                }
            }
        }
        /* An established client detects socket/keepalive loss itself. Stopping it
         * on a Wi-Fi event could send DISCONNECT and suppress its Last Will. */
    }
}

static void on_time_sync(struct timeval *tv)
{
    if (!tv) { return; }
    struct tm utc;
    char text[32];
    if (!gmtime_r(&tv->tv_sec, &utc) ||
        strftime(text, sizeof(text), "%Y-%m-%dT%H:%M:%SZ", &utc) == 0) {
        ESP_LOGW(TAG, "Synchronized time could not be formatted");
        return;
    }
    ESP_LOGI(TAG, "UTC synchronized: %s", text);
}

static void start_time_sync(void)
{
    esp_err_t ret = esp_netif_sntp_start();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Time sync start failed: %s; local operation continues",
                 esp_err_to_name(ret));
        return;
    }
    ESP_LOGI(TAG, "Time sync requested; waiting for UTC asynchronously");
}

static void on_station_ip(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    if (base != IP_EVENT || id != IP_EVENT_STA_GOT_IP || !data) { return; }
    const ip_event_got_ip_t *event = data;
    if (event->esp_netif == station && event->ip_info.ip.addr != 0) {
        start_time_sync();
        notify_worker(WAKE_WORKER);
    }
}

esp_err_t mqtt_manager_start(const char *shared_boot_id, bool networking_initialized)
{
    if (started) { return ESP_OK; }
    if (!telemetry_valid_uuid(shared_boot_id)) { return ESP_ERR_INVALID_ARG; }
    strcpy(boot_id, shared_boot_id);
    /* The lookup uses lwIP IPC and must not run before successful netif init. */
    station = networking_initialized ? esp_netif_get_handle_from_ifkey("WIFI_STA_DEF") : NULL;

    uint8_t mac[6];
    esp_err_t ret = esp_read_mac(mac, ESP_MAC_WIFI_STA);
    if (ret != ESP_OK) { station = NULL; return ret; }
    snprintf(device_id, sizeof(device_id), "BB-%02X%02X%02X%02X%02X%02X",
             (unsigned)mac[0], (unsigned)mac[1], (unsigned)mac[2],
             (unsigned)mac[3], (unsigned)mac[4], (unsigned)mac[5]);
    snprintf(status_topic, sizeof(status_topic), "bangusbuhai-rebuild/devices/%s/status", device_id);
    snprintf(telemetry_topic, sizeof(telemetry_topic), "bangusbuhai-rebuild/devices/%s/telemetry", device_id);
    snprintf(ack_topic, sizeof(ack_topic), "bangusbuhai-rebuild/devices/%s/acks", device_id);
    snprintf(quarantine_topic, sizeof(quarantine_topic), "bangusbuhai-rebuild/devices/%s/quarantine-receipts", device_id);
    snprintf(command_topic, sizeof(command_topic), "bangusbuhai-rebuild/devices/%s/cmd", device_id);
    snprintf(result_topic, sizeof(result_topic), "bangusbuhai-rebuild/devices/%s/command-results", device_id);
    atomic_store(&time_ready, false);
    if (networking_initialized) {
        esp_err_t setup = device_setup_start(device_id);
        if (setup != ESP_OK) { ESP_LOGE(TAG, "Device setup unavailable: %s; new telemetry paused", esp_err_to_name(setup)); }
    }

    transport_events = xQueueCreateStatic(8, sizeof(transport_event_t), transport_queue_bytes, &transport_queue_storage);
    acknowledgements = xQueueCreateStatic(2, sizeof(telemetry_ack_message_t), ack_queue_bytes, &ack_queue_storage);
    commands = xQueueCreateStatic(2, sizeof(telemetry_ack_message_t), command_queue_bytes, &command_queue_storage);
    if (!transport_events || !acknowledgements || !commands) { return ESP_ERR_NO_MEM; }
    if (xTaskCreate(mqtt_worker, "mqtt_recovery", 8192, NULL, 3, &worker) != pdPASS) { return ESP_ERR_NO_MEM; }
    started = true;

    /* Network setup failure must not disable offline captures or local operation. */
    if (!station) {
        ESP_LOGW(TAG, "No station; offline telemetry capture remains active");
        notify_worker(BEGIN_WORK);
        return ESP_OK;
    }

    esp_sntp_config_t config = ESP_NETIF_SNTP_DEFAULT_CONFIG("time.cloudflare.com");
    config.start = false;
    config.wait_for_sync = false;
    config.sync_cb = on_time_sync;
    ret = esp_netif_sntp_init(&config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Time service unavailable: %s; offline telemetry remains active", esp_err_to_name(ret));
        notify_worker(BEGIN_WORK);
        return ESP_OK;
    }

    esp_event_handler_instance_t time_handler, ip_handler;
    ret = esp_event_handler_instance_register(NETIF_SNTP_EVENT, NETIF_SNTP_TIME_SYNC,
                                             on_synchronized_time, NULL, &time_handler);
    if (ret != ESP_OK) { goto fail_network; }
    ret = esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                             on_station_ip, NULL, &ip_handler);
    if (ret != ESP_OK) {
        esp_event_handler_instance_unregister(NETIF_SNTP_EVENT, NETIF_SNTP_TIME_SYNC, time_handler);
        goto fail_network;
    }
    started = true;
    notify_worker(BEGIN_WORK);

    /* Cover an IP acquired before this handler was registered. */
    esp_netif_ip_info_t ip;
    ret = esp_netif_get_ip_info(station, &ip);
    if (ret == ESP_OK && ip.ip.addr != 0) {
        start_time_sync();
    } else if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Initial IP check failed: %s; waiting for station IP event",
                 esp_err_to_name(ret));
    }
    return ESP_OK;

fail_network:
    esp_netif_sntp_deinit();
    ESP_LOGE(TAG, "Network event setup failed: %s; offline telemetry remains active", esp_err_to_name(ret));
    notify_worker(BEGIN_WORK);
    return ESP_OK;
}
