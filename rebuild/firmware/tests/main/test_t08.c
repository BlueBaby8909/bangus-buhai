#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "unity.h"
#include "telemetry.h"
#include "device_setup.h"
#include "cJSON.h"
#include "nvs.h"
#include "nvs_flash.h"

/* Model atomic individual NVS key updates, including ambiguous commit failures.
 * Never initialize or erase any real on-device NVS partition from this suite. */
typedef struct { size_t length; unsigned char bytes[TELEMETRY_MAX_PAYLOAD + 128]; } fake_blob_t;
static fake_blob_t blobs[18], setup_blob;
static unsigned char command_blob[20000];
static size_t command_blob_length;
static int operation, fail_at;
static bool fail_after, fail_open;
static const char *DEVICE = "BB-14C19FC68C60";
static const char *BOOT_A = "11111111-1111-4111-8111-111111111111";
static const char *BOOT_B = "22222222-2222-4222-8222-222222222222";
static const char *BINDING = "97fcde45-4112-41d4-a509-17e5bb1c0d91";
static char saved_payload[TELEMETRY_MAX_PAYLOAD + 1], ack[TELEMETRY_MAX_PAYLOAD + 1];

static int blob_index(const char *key)
{
    if (!strcmp(key, "manifest")) { return 17; }
    TEST_ASSERT_EQUAL('r', key[0]);
    TEST_ASSERT_EQUAL(3, strlen(key));
    int slot = atoi(key + 1);
    TEST_ASSERT_INT_WITHIN(8, 8, slot);
    return slot;
}

static bool before_write(void) { return ++operation == fail_at && !fail_after; }
static bool after_write(void) { return operation == fail_at && fail_after; }

esp_err_t __wrap_nvs_flash_init_partition(const char *partition)
{
    TEST_ASSERT_EQUAL_STRING("telemetry", partition);
    return fail_open ? ESP_ERR_NVS_NO_FREE_PAGES : ESP_OK;
}
esp_err_t __wrap_nvs_open_from_partition(const char *partition, const char *name,
                                        nvs_open_mode_t mode, nvs_handle_t *handle)
{
    if (!strcmp(partition, "nvs")) {
        TEST_ASSERT_EQUAL_STRING("bb_setup", name);
        if (mode == NVS_READONLY && !setup_blob.length) { return ESP_ERR_NVS_NOT_FOUND; }
        *handle = 8; return ESP_OK;
    }
    TEST_ASSERT_EQUAL_STRING("telemetry", partition);
    if (!strcmp(name, "bb_cmd")) { TEST_ASSERT_EQUAL(NVS_READWRITE, mode); *handle = 9; return ESP_OK; }
    TEST_ASSERT_EQUAL_STRING("queue", name);
    TEST_ASSERT_EQUAL(NVS_READWRITE, mode);
    *handle = 7;
    return ESP_OK;
}
void __wrap_nvs_close(nvs_handle_t handle) { TEST_ASSERT_TRUE(handle == 7 || handle == 8 || handle == 9); }
esp_err_t __wrap_nvs_get_blob(nvs_handle_t handle, const char *key, void *out, size_t *length)
{
    if (handle == 9) {
        TEST_ASSERT_EQUAL_STRING("ledger", key);
        if (!command_blob_length) { return ESP_ERR_NVS_NOT_FOUND; }
        if (*length < command_blob_length) { *length = command_blob_length; return ESP_ERR_NVS_INVALID_LENGTH; }
        if (out) { memcpy(out, command_blob, command_blob_length); } *length = command_blob_length; return ESP_OK;
    }
    TEST_ASSERT_TRUE(handle == 7 || handle == 8);
    fake_blob_t *blob = handle == 8 ? &setup_blob : &blobs[blob_index(key)];
    if (!blob->length) { return ESP_ERR_NVS_NOT_FOUND; }
    if (!out) { *length = blob->length; return ESP_OK; }
    if (*length < blob->length) { *length = blob->length; return ESP_ERR_NVS_INVALID_LENGTH; }
    memcpy(out, blob->bytes, blob->length); *length = blob->length;
    return ESP_OK;
}
esp_err_t __wrap_nvs_set_blob(nvs_handle_t handle, const char *key, const void *data, size_t length)
{
    if (handle == 9) {
        TEST_ASSERT_EQUAL_STRING("ledger", key);
        if (before_write()) { return ESP_FAIL; }
        TEST_ASSERT_LESS_OR_EQUAL(sizeof(command_blob), length);
        memcpy(command_blob, data, length); command_blob_length = length;
        return after_write() ? ESP_FAIL : ESP_OK;
    }
    TEST_ASSERT_TRUE(handle == 7 || handle == 8);
    if (before_write()) { return ESP_FAIL; }
    fake_blob_t *blob = handle == 8 ? &setup_blob : &blobs[blob_index(key)];
    TEST_ASSERT_LESS_OR_EQUAL(sizeof(blob->bytes), length);
    memcpy(blob->bytes, data, length); blob->length = length;
    return after_write() ? ESP_FAIL : ESP_OK;
}
esp_err_t __wrap_nvs_erase_key(nvs_handle_t handle, const char *key)
{
    TEST_ASSERT_TRUE(handle == 7 || handle == 8);
    if (before_write()) { return ESP_FAIL; }
    fake_blob_t *blob = handle == 8 ? &setup_blob : &blobs[blob_index(key)];
    if (!blob->length) { return ESP_ERR_NVS_NOT_FOUND; }
    blob->length = 0;
    return after_write() ? ESP_FAIL : ESP_OK;
}
esp_err_t __wrap_nvs_commit(nvs_handle_t handle)
{
    TEST_ASSERT_TRUE(handle == 7 || handle == 8 || handle == 9);
    if (before_write()) { return ESP_FAIL; }
    return after_write() ? ESP_FAIL : ESP_OK;
}

static esp_err_t open_queue(const char *boot)
{
    telemetry_config_t config = {DEVICE, boot, BINDING, "t08-test"};
    return telemetry_init(&config);
}
static void reset_store(void)
{
    telemetry_close();
    memset(blobs, 0, sizeof(blobs));
    operation = fail_at = 0; fail_after = fail_open = false;
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_A));
}
static sensor_reading_t snapshot(void)
{
    return (sensor_reading_t){
        .capture_uptime_ms = 1000,
        .temperature = {.value = 27, .has_value = true, .validity = SENSOR_VALID,
            .source = "sensor", .unit = "degC", .sample_age_ms = 10, .last_valid_age_ms = 10},
        .turbidity = {.value = 12, .has_value = true, .validity = SENSOR_UNVERIFIED,
            .source = "sensor", .unit = "NTU", .sample_age_ms = 100, .last_valid_age_ms = -1},
        .ph = {.value = 7.8f, .has_value = true, .validity = SENSOR_UNVERIFIED,
            .source = "default", .unit = "pH", .sample_age_ms = -1, .last_valid_age_ms = -1}
    };
}
static void capture(void)
{
    sensor_reading_t value = snapshot();
    relay_control_state_t relay = {.known = true, .on = false, .mode = RELAY_MODE_AUTO};
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_capture(&value, &relay, NULL, 0));
}
static const telemetry_event_t *peek(void)
{
    const telemetry_event_t *value = NULL;
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_peek(&value));
    TEST_ASSERT_NOT_NULL(value);
    return value;
}
static void make_ack(const char *boot, uint32_t seq, const char *result)
{
    snprintf(ack, sizeof(ack), "{\"schema_version\":1,\"device_id\":\"%s\",\"boot_id\":\"%s\","
             "\"seq\":%lu,\"event_kind\":\"telemetry\",\"result\":\"%s\"}",
             DEVICE, boot, (unsigned long)seq, result);
}
static void acknowledge(const char *boot, uint32_t seq, const char *result)
{
    make_ack(boot, seq, result);
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_accept_ack(ack, strlen(ack)));
}

static void test_t08_immutable_replay_and_reboot(void)
{
    reset_store(); capture();
    strcpy(saved_payload, peek()->payload);
    printf("T08_WIRE_JSON:%s\n", saved_payload);
    sensor_reading_t changed = snapshot();
    changed.temperature.value = 29; changed.capture_uptime_ms = 2000;
    time_t utc = 1792540000;
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_capture(&changed, NULL, &utc, 3));
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
    TEST_ASSERT_EQUAL_STRING(BOOT_A, peek()->boot_id);
    TEST_ASSERT_EQUAL(2, telemetry_pending());
    capture();
    acknowledge(BOOT_A, 0, "stored");
    acknowledge(BOOT_A, 1, "duplicate");
    TEST_ASSERT_EQUAL_STRING(BOOT_B, peek()->boot_id);
    TEST_ASSERT_EQUAL(0, peek()->seq);
    acknowledge(BOOT_B, 0, "stored");
    const telemetry_event_t *empty;
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, telemetry_peek(&empty));
    TEST_ASSERT_NULL(empty);
}

static void test_t08_capture_time_and_quality(void)
{
    reset_store();
    sensor_reading_t value = snapshot();
    value.temperature.has_value = false; value.temperature.validity = SENSOR_STALE;
    value.capture_uptime_ms = 90000; value.temperature.sample_age_ms = 60000;
    value.temperature.last_valid_age_ms = 60000;
    time_t utc = 1792540000;
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_capture(&value, NULL, &utc, 4));
    const telemetry_event_t *event = peek();
    printf("T08_WIRE_JSON:%s\n", event->payload);
    cJSON *json = cJSON_Parse(event->payload);
    TEST_ASSERT_NOT_NULL(json);
    TEST_ASSERT_EQUAL_STRING("synchronized", cJSON_GetObjectItem(json, "time_quality")->valuestring);
    TEST_ASSERT_TRUE(cJSON_IsString(cJSON_GetObjectItem(json, "measured_at")));
    cJSON *readings = cJSON_GetObjectItem(json, "readings");
    TEST_ASSERT_TRUE(cJSON_IsNull(cJSON_GetObjectItem(cJSON_GetObjectItem(readings, "temperature"), "value")));
    TEST_ASSERT_EQUAL_STRING("default", cJSON_GetObjectItem(cJSON_GetObjectItem(readings, "ph"), "source")->valuestring);
    TEST_ASSERT_TRUE(cJSON_IsNull(cJSON_GetObjectItem(cJSON_GetObjectItem(json, "relay"), "on")));
    cJSON_Delete(json);
    acknowledge(BOOT_A, 0, "stored");
    value = snapshot();
    value.capture_uptime_ms = 9007199254740991LL;
    value.turbidity.sample_age_ms = value.capture_uptime_ms;
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_capture(&value, NULL, NULL, UINT32_MAX));
    event = peek();
    TEST_ASSERT_NOT_NULL(strstr(event->payload, "\"capture_uptime_ms\":9007199254740991"));
    TEST_ASSERT_NOT_NULL(strstr(event->payload, "\"reconnects\":4294967295"));
    printf("T08_WIRE_JSON:%s\n", event->payload);
}

static void test_t08_newest_sixteen_and_lost_ack(void)
{
    reset_store();
    for (unsigned i = 0; i < 18; ++i) { capture(); }
    TEST_ASSERT_EQUAL(16, telemetry_pending());
    TEST_ASSERT_EQUAL(2, telemetry_dropped());
    TEST_ASSERT_EQUAL(2, peek()->seq);
    strcpy(saved_payload, peek()->payload);
    /* No application ACK: peeks/resends/reboot never remove or regenerate it. */
    for (unsigned i = 0; i < 5; ++i) { TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload); }
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL(0, telemetry_dropped()); /* Wire diagnostics are current-boot counters. */
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
    make_ack(BOOT_A, 0, "stored");
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, telemetry_accept_ack(ack, strlen(ack)));
    acknowledge(BOOT_A, 2, "duplicate");
    TEST_ASSERT_EQUAL(15, telemetry_pending());
    make_ack(BOOT_A, 2, "duplicate");
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, telemetry_accept_ack(ack, strlen(ack)));
    TEST_ASSERT_EQUAL(15, telemetry_pending());
}

static void test_t08_ack_correlation_and_strict_json(void)
{
    reset_store(); capture();
    const char *bad[] = {
        "{}", "[]", "null", "{\"schema_version\":1,\"schema_version\":1}",
        "{\"seq\":01}", "{\"seq\":1.0}", "{\"seq\":1e0}", "{\"seq\":true}",
        "{\"seq\":4294967296}", "{\"seq\":-1}", "{\"seq\":0}junk", "{\"x\":\"\\u0000\"}",
        "{\"x\":[[[[[[[[[]]]]]]]]]}", "{\"x\":\"\xc0\xaf\"}",
        "{\"schema_version\":1,\"device_id\":\"BB-14C19FC68C60\","
        "\"boot_id\":\"11111111-1111-4111-8111-111111111111\",\"seq\":0.0,"
        "\"event_kind\":\"telemetry\",\"result\":\"stored\"}",
        "{\"schema_version\":1,\"device_id\":\"BB-14C19FC68C60\","
        "\"boot_id\":\"11111111-1111-4111-8111-111111111111\",\"seq\":00,"
        "\"event_kind\":\"telemetry\",\"result\":\"stored\"}"
    };
    for (unsigned i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        TEST_ASSERT_EQUAL(ESP_ERR_INVALID_RESPONSE, telemetry_accept_ack(bad[i], strlen(bad[i])));
        TEST_ASSERT_EQUAL(1, telemetry_pending());
    }
    make_ack(BOOT_B, 0, "stored");
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, telemetry_accept_ack(ack, strlen(ack)));
    make_ack(BOOT_A, 0, "accepted");
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_RESPONSE, telemetry_accept_ack(ack, strlen(ack)));
    make_ack(BOOT_A, 0, "stored");
    char *device = strstr(ack, "BB-14C19FC68C60"); device[3] = '0';
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_RESPONSE, telemetry_accept_ack(ack, strlen(ack)));
    TEST_ASSERT_EQUAL(1, telemetry_pending());
    acknowledge(BOOT_A, 0, "stored");
    TEST_ASSERT_EQUAL(0, telemetry_pending());
    capture(); make_ack(BOOT_A, 1, "stored");
    size_t length = strlen(ack);
    memset(ack + length, ' ', TELEMETRY_MAX_PAYLOAD - length);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_RESPONSE, telemetry_accept_ack(ack, TELEMETRY_MAX_PAYLOAD + 1));
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_accept_ack(ack, TELEMETRY_MAX_PAYLOAD));
    TEST_ASSERT_EQUAL(0, telemetry_pending());
}

static void test_t08_fragmented_and_retained_ack(void)
{
    reset_store(); capture(); make_ack(BOOT_A, 0, "stored");
    static telemetry_ack_assembly_t incoming;
    memset(&incoming, 0, sizeof(incoming));
    size_t length = strlen(ack), first = length / 2;
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, true, true, 1, 0, length, ack, length));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, false, false, 1, 0, length, ack, length));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, true, false, 1, 0, TELEMETRY_MAX_PAYLOAD + 1, ack, length));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, true, false, 1, 0, length, ack, first));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, false, false, 1, first + 1, length, ack + first, length - first));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, true, false, 1, 0, length, ack, first));
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, false, false, 2, first, length, ack + first, length - first));
    TEST_ASSERT_EQUAL(1, telemetry_pending());
    TEST_ASSERT_FALSE(telemetry_ack_fragment(&incoming, true, false, 3, 0, length, ack, first));
    TEST_ASSERT_TRUE(telemetry_ack_fragment(&incoming, false, false, 3, first, length, ack + first, length - first));
    TEST_ASSERT_EQUAL_STRING(ack, incoming.message.data);
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_accept_ack(incoming.message.data, incoming.message.length));
    TEST_ASSERT_EQUAL(0, telemetry_pending());
}

static void test_t08_interrupted_full_queue_replacement(void)
{
    for (int after = 0; after <= 1; ++after) {
        for (int step = 1; step <= 6; ++step) {
            reset_store();
            for (unsigned i = 0; i < 16; ++i) { capture(); }
            operation = 0; fail_at = step; fail_after = after;
            sensor_reading_t value = snapshot();
            TEST_ASSERT_NOT_EQUAL(ESP_OK, telemetry_capture(&value, NULL, NULL, 0));
            TEST_ASSERT_FALSE(telemetry_ready());
            fail_at = 0;
            TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
            TEST_ASSERT_EQUAL(16, telemetry_pending());
            unsigned live_blobs = 0;
            for (unsigned slot = 0; slot < 18; ++slot) { live_blobs += blobs[slot].length != 0; }
            TEST_ASSERT_EQUAL(17, live_blobs); /* Manifest + exactly sixteen referenced records. */
            uint32_t first = peek()->seq;
            TEST_ASSERT_TRUE(first == 0 || first == 1);
            for (uint32_t seq = first; seq < first + 16; ++seq) {
                TEST_ASSERT_EQUAL(seq, peek()->seq);
                TEST_ASSERT_EQUAL_STRING(BOOT_A, peek()->boot_id);
                acknowledge(BOOT_A, seq, "duplicate");
            }
            TEST_ASSERT_EQUAL(0, telemetry_pending());
        }
    }
}

static void test_t08_interrupted_ack_removal(void)
{
    for (int after = 0; after <= 1; ++after) {
        for (int step = 1; step <= 4; ++step) {
            reset_store(); capture(); capture();
            make_ack(BOOT_A, 0, "stored");
            operation = 0; fail_at = step; fail_after = after;
            TEST_ASSERT_NOT_EQUAL(ESP_OK, telemetry_accept_ack(ack, strlen(ack)));
            fail_at = 0;
            TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
            uint32_t count = telemetry_pending();
            TEST_ASSERT_TRUE(count == 1 || count == 2);
            TEST_ASSERT_EQUAL(count == 2 ? 0 : 1, peek()->seq);
            if (count == 2) { acknowledge(BOOT_A, 0, "duplicate"); }
            TEST_ASSERT_EQUAL(1, peek()->seq);
        }
    }
}

static void test_t08_storage_fault_preserves_data(void)
{
    reset_store(); capture();
    strcpy(saved_payload, peek()->payload);
    fail_open = true;
    TEST_ASSERT_NOT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_FALSE(telemetry_ready());
    fail_open = false;
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
    blobs[17].bytes[0] ^= 1;
    TEST_ASSERT_NOT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_FALSE(telemetry_ready());
    blobs[17].bytes[0] ^= 1;
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    blobs[0].bytes[20] ^= 1;
    TEST_ASSERT_NOT_EQUAL(ESP_OK, open_queue(BOOT_B));
    blobs[0].bytes[20] ^= 1;
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
}

static void test_t08_monotonic_capture_schedule(void)
{
    reset_store();
    TEST_ASSERT_TRUE(telemetry_capture_due(0));
    TEST_ASSERT_FALSE(telemetry_capture_due(0));
    TEST_ASSERT_FALSE(telemetry_capture_due(TELEMETRY_INTERVAL_US - 1));
    TEST_ASSERT_TRUE(telemetry_capture_due(TELEMETRY_INTERVAL_US));
    TEST_ASSERT_TRUE(telemetry_capture_due(3 * TELEMETRY_INTERVAL_US + 1));
    TEST_ASSERT_FALSE(telemetry_capture_due(3 * TELEMETRY_INTERVAL_US + 1));
    TEST_ASSERT_FALSE(telemetry_capture_due(4 * TELEMETRY_INTERVAL_US - 1));
    TEST_ASSERT_TRUE(telemetry_capture_due(4 * TELEMETRY_INTERVAL_US));
}

static void test_t08_invalid_snapshot_cannot_become_telemetry(void)
{
    reset_store();
    sensor_reading_t value = snapshot();
    value.temperature.value = NAN;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, telemetry_capture(&value, NULL, NULL, 0));
    value = snapshot(); value.temperature.sample_age_ms = 60000;
    value.temperature.last_valid_age_ms = 60000; value.capture_uptime_ms = 60000;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, telemetry_capture(&value, NULL, NULL, 0));
    value = snapshot(); value.temperature.sample_age_ms = 1001;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, telemetry_capture(&value, NULL, NULL, 0));
    value = snapshot(); value.ph.sample_age_ms = 0;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, telemetry_capture(&value, NULL, NULL, 0));
    value = snapshot(); value.capture_uptime_ms = 9007199254740992LL;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, telemetry_capture(&value, NULL, NULL, 0));
    TEST_ASSERT_EQUAL(0, telemetry_pending());
    capture();
    TEST_ASSERT_EQUAL(0, peek()->seq);
}

void run_t08_tests(void)
{
    RUN_TEST(test_t08_immutable_replay_and_reboot);
    RUN_TEST(test_t08_capture_time_and_quality);
    RUN_TEST(test_t08_newest_sixteen_and_lost_ack);
    RUN_TEST(test_t08_ack_correlation_and_strict_json);
    RUN_TEST(test_t08_fragmented_and_retained_ack);
    RUN_TEST(test_t08_interrupted_full_queue_replacement);
    RUN_TEST(test_t08_interrupted_ack_removal);
    RUN_TEST(test_t08_storage_fault_preserves_data);
    RUN_TEST(test_t08_monotonic_capture_schedule);
    RUN_TEST(test_t08_invalid_snapshot_cannot_become_telemetry);
    telemetry_close();
}

void t13a_reset_nvs(void)
{
    setup_blob.length = 0; operation = fail_at = 0; fail_after = fail_open = false;
}
void t13a_fail_write(int boundary, bool after)
{
    operation = 0; fail_at = boundary; fail_after = after;
}
void t14_reset_nvs(void)
{
    command_blob_length = 0;
    memset(blobs, 0, sizeof(blobs));
    operation = fail_at = 0; fail_after = fail_open = false;
}
static void quarantine_receipt(void)
{
    const telemetry_event_t *event = peek();
    char hash[65];
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_sha256(event->payload, event->length, hash));
    snprintf(ack, sizeof(ack), "{\"schema_version\":1,\"device_id\":\"%s\",\"boot_id\":\"%s\","
        "\"seq\":%lu,\"event_kind\":\"telemetry\",\"quarantine_id\":\"%s\","
        "\"reason\":\"binding_unavailable\",\"payload_sha256\":\"%s\"}",
        DEVICE, event->boot_id, (unsigned long)event->seq, BINDING, hash);
}
static void test_t13a_quarantine_exact_matching_and_replay(void)
{
    reset_store(); capture(); capture(); quarantine_receipt();
    char *digest = strstr(ack, "payload_sha256");
    TEST_ASSERT_NOT_NULL(digest); digest[17] = digest[17] == '0' ? '1' : '0';
    TEST_ASSERT_NOT_EQUAL(ESP_OK, telemetry_accept_quarantine_receipt(ack, strlen(ack)));
    TEST_ASSERT_EQUAL(2, telemetry_pending());
    quarantine_receipt();
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_accept_quarantine_receipt(ack, strlen(ack)));
    TEST_ASSERT_EQUAL(1, telemetry_pending());
    TEST_ASSERT_NOT_EQUAL(ESP_OK, telemetry_accept_quarantine_receipt(ack, strlen(ack)));
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL(1, telemetry_pending());
}
static void test_t13a_quarantine_interrupted_release(void)
{
    for (int boundary = 1; boundary <= 4; ++boundary) {
        for (int after = 0; after <= 1; ++after) {
            reset_store(); capture(); quarantine_receipt();
            operation = 0; fail_at = boundary; fail_after = after;
            TEST_ASSERT_NOT_EQUAL(ESP_OK, telemetry_accept_quarantine_receipt(ack, strlen(ack)));
            fail_at = 0;
            TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
            TEST_ASSERT_TRUE(telemetry_pending() <= 1);
            if (telemetry_pending()) {
                TEST_ASSERT_EQUAL(ESP_OK, telemetry_accept_quarantine_receipt(ack, strlen(ack)));
            }
        }
    }
}
static void test_t13a_runtime_binding_preserves_old_queue(void)
{
    reset_store(); capture(); strcpy(saved_payload, peek()->payload);
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_set_binding(NULL));
    sensor_reading_t value = snapshot();
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, telemetry_capture(&value, NULL, NULL, 0));
    TEST_ASSERT_EQUAL_STRING(saved_payload, peek()->payload);
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_set_binding(BOOT_B)); capture();
    acknowledge(BOOT_A, 0, "stored");
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload, BOOT_B));
    TEST_ASSERT_EQUAL(ESP_OK, open_queue(BOOT_B));
    TEST_ASSERT_EQUAL(1, telemetry_pending());
}
void run_t13a_queue_tests(void)
{
    RUN_TEST(test_t13a_quarantine_exact_matching_and_replay);
    RUN_TEST(test_t13a_quarantine_interrupted_release);
    RUN_TEST(test_t13a_runtime_binding_preserves_old_queue);
}
