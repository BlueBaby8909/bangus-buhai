#pragma once

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <time.h>
#include "esp_err.h"
#include "sensor_service.h"
#include "relay_control.h"

#define TELEMETRY_CAPACITY 16U
#define TELEMETRY_MAX_PAYLOAD 4096U
/* Temporary owner-requested live UI trial; normal production target is 300 s. */
#define TELEMETRY_INTERVAL_US (5LL * 1000000)
#define TELEMETRY_ACK_RETRY_US (30LL * 1000000)

typedef struct {
    const char *device_id;
    const char *boot_id;
    const char *binding_id;
    const char *fw_version;
} telemetry_config_t;

typedef struct {
    char boot_id[37];
    uint32_t seq;
    size_t length;
    char payload[TELEMETRY_MAX_PAYLOAD + 1];
} telemetry_event_t;

typedef struct { size_t length; char data[TELEMETRY_MAX_PAYLOAD + 1]; bool quarantine; } telemetry_ack_message_t;
typedef struct {
    telemetry_ack_message_t message;
    size_t offset;
    int mid;
    bool active;
} telemetry_ack_assembly_t;

/* Pure bounded assembly, owned by the SDK callback task. A true result means
 * message is complete and must be copied to the worker inbox, never parsed here.
 */
bool telemetry_ack_fragment(telemetry_ack_assembly_t *assembly, bool topic_matches, bool retained,
                            int mid, size_t offset, size_t total, const char *data, size_t length);

/* One caller owns all operations (the MQTT worker). No driver/RTOS task created.
 * init reopens only the separate telemetry NVS partition; never erases it.
 * Repeated initialization closes the previous handle (also used by reboot tests).
 */
esp_err_t telemetry_init(const telemetry_config_t *config);
void telemetry_close(void);
/* Runtime changes affect future captures only. NULL pauses capture, not replay. */
esp_err_t telemetry_set_binding(const char *binding);
esp_err_t telemetry_accept_quarantine_receipt(const char *payload, size_t length);
struct cJSON;
/* Shared strict bounded JSON parser: duplicates, UTF-8, depth, integer grammar. */
struct cJSON *telemetry_parse_json(const char *data, size_t length, bool integers);
bool telemetry_ready(void);
bool telemetry_valid_uuid(const char *text);
uint32_t telemetry_pending(void);
uint32_t telemetry_dropped(void); /* Saturating current-boot counter. */
/* Single MQTT owner allocates identities for telemetry AND command results. */
esp_err_t telemetry_allocate_sequence(uint32_t *out);
/* Startup capture then configured monotonic cadence; coalesce missed slots. */
bool telemetry_capture_due(int64_t now_us);

/* captured_utc == NULL means unsynchronized. Ages/time/diagnostics freeze here.
 * Persist before returning success. Full queues evict their oldest entry only
 * after the replacement record and new manifest are committed.
 */
esp_err_t telemetry_capture(const sensor_reading_t *snapshot,
                            const relay_control_state_t *relay,
                            const time_t *captured_utc, uint32_t reconnects);

/* Returned buffer belongs to this component; valid until the next operation.
 * SDK enqueue copies it. Caller must not retain the pointer for async use.
 */
esp_err_t telemetry_peek(const telemetry_event_t **event);
/* Only a matching application ack can remove an entry; never call for PUBACK.
 * Unknown/previously removed event returns ESP_ERR_NOT_FOUND without mutation.
 */
esp_err_t telemetry_accept_ack(const char *payload, size_t length);
