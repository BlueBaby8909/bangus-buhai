#include "command_manager.h"
#include "relay_control.h"
#include "telemetry.h"
#include "cJSON.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "esp_crc.h"
#include "esp_log.h"
#include "psa/crypto.h"
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <time.h>

#define COMMAND_MAGIC 0x42424331U
typedef struct {
    uint32_t acked, seq;
    char boot[37];
    command_result_wire_t wire;
} result_t;
typedef struct {
    uint32_t phase; /* 0 free; 1 admitted/possibly executing; 2 final */
    char id[37], binding[37], digest[65];
    int64_t expires_us;
    result_t accepted, terminal;
} entry_t;
typedef struct {
    uint32_t magic, version;
    char device[16];
    entry_t entries[COMMAND_CAPACITY];
    uint32_t crc;
} ledger_t;
static ledger_t ledger, next;
static nvs_handle_t store;
static bool opened, healthy;
static char identity[16], boot_id[37];
static bool (*current_binding)(const char *binding);
static const char *TAG = "commands";
/* Two blob generations plus NVS GC reserve fit beside the existing queue's
 * conservative 160 KiB bound, without changing the partition or old format. */
_Static_assert(sizeof(ledger_t) < 20000, "Command ledger exceeds reserved NVS budget");

static const char *text(const cJSON *root, const char *key)
{
    cJSON *value = cJSON_GetObjectItemCaseSensitive(root, key);
    return cJSON_IsString(value) ? value->valuestring : NULL;
}

bool command_timestamp(const char *value, int64_t *out)
{
    if (!value || !out) { return false; }
    size_t size = strlen(value);
    if (size < 20 || size > 27) { return false; }
    for (int i = 0; i < 19; ++i) {
        char expected = i == 4 || i == 7 ? '-' : i == 10 ? 'T' : i == 13 || i == 16 ? ':' : 0;
        if (expected ? value[i] != expected : value[i] < '0' || value[i] > '9') { return false; }
    }
    int y, m, d, hh, mm, ss;
    if (sscanf(value, "%4d-%2d-%2dT%2d:%2d:%2d", &y, &m, &d, &hh, &mm, &ss) != 6 ||
        y < 1970 || y > 9999 || m < 1 || m > 12 || hh > 23 || mm > 59 || ss > 59) { return false; }
    const int months[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    bool leap = y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
    if (d < 1 || d > months[m-1] + (m == 2 && leap)) { return false; }
    int64_t days = d-1;
    for (int yr = 1970; yr < y; ++yr) { days += 365 + (yr % 4 == 0 && (yr % 100 != 0 || yr % 400 == 0)); }
    for (int month = 1; month < m; ++month) { days += months[month-1] + (month == 2 && leap); }
    const char *tail = value + 19;
    int64_t fraction = 0, scale = 100000;
    if (*tail == '.') {
        ++tail; unsigned count = 0;
        while (*tail >= '0' && *tail <= '9' && count < 6) {
            fraction += (*tail++ - '0') * scale; scale /= 10; ++count;
        }
        if (!count) { return false; }
    }
    if (strcmp(tail, "Z")) { return false; }
    *out = (days * 86400 + hh * 3600 + mm * 60 + ss) * 1000000 + fraction;
    return true;
}

static uint32_t crc(const ledger_t *value)
{
    return esp_crc32_le(0, (const uint8_t *)value, offsetof(ledger_t, crc));
}
static esp_err_t save(void)
{
    next.crc = crc(&next);
    esp_err_t ret = nvs_set_blob(store, "ledger", &next, sizeof(next));
    if (ret == ESP_OK) { ret = nvs_commit(store); }
    size_t size = sizeof(ledger);
    if (ret == ESP_OK) { ret = nvs_get_blob(store, "ledger", &ledger, &size); }
    if (ret == ESP_OK && (size != sizeof(ledger) || memcmp(&ledger, &next, sizeof(ledger)))) { ret = ESP_ERR_INVALID_CRC; }
    if (ret != ESP_OK) { healthy = false; ESP_LOGE(TAG, "Command storage unavailable; actuation admission stopped"); }
    return ret;
}

static esp_err_t result(result_t *slot, const entry_t *entry, const char *result, const char *reason,
                        const relay_control_state_t *state, int64_t utc_us, int64_t uptime_ms)
{
    memset(slot, 0, sizeof(*slot));
    esp_err_t ret = telemetry_allocate_sequence(&slot->seq);
    if (ret != ESP_OK) { return ret; }
    strcpy(slot->boot, boot_id);
    char timestamp[48], observed[6];
    strcpy(timestamp, "null"); strcpy(observed, "null");
    if (utc_us > 0) {
        time_t seconds = utc_us / 1000000; struct tm tm;
        char base[32];
        if (!gmtime_r(&seconds, &tm) || strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm) != 19) { return ESP_ERR_INVALID_ARG; }
        snprintf(timestamp, sizeof(timestamp), "\"%s.%06ldZ\"", base, (long)(utc_us % 1000000));
    }
    if (state && state->known) { strcpy(observed, state->on ? "true" : "false"); }
    int written = snprintf(slot->wire.payload, sizeof(slot->wire.payload),
        "{\"schema_version\":1,\"device_id\":\"%s\",\"binding_id\":\"%s\",\"boot_id\":\"%s\","
        "\"seq\":%lu,\"capture_uptime_ms\":%lld,\"time_quality\":\"%s\",\"created_at\":%s,"
        "\"command_id\":\"%s\",\"result\":\"%s\",\"reason\":\"%s\",\"observed_on\":%s}",
        identity, entry->binding, boot_id, (unsigned long)slot->seq, (long long)uptime_ms,
        utc_us > 0 ? "synchronized" : "unsynchronized", timestamp, entry->id, result, reason, observed);
    if (written <= 0 || written >= sizeof(slot->wire.payload)) { return ESP_ERR_INVALID_SIZE; }
    slot->wire.length = written;
    return ESP_OK;
}

void command_manager_close(void)
{
    if (opened) { nvs_close(store); }
    opened = healthy = false;
}
esp_err_t command_manager_init(const char *device, const char *boot, bool (*binding)(const char *))
{
    command_manager_close();
    if (!device || strlen(device) != 15 || !telemetry_valid_uuid(boot) || !binding) { return ESP_ERR_INVALID_ARG; }
    strcpy(identity, device); strcpy(boot_id, boot); current_binding = binding;
    esp_err_t ret = nvs_flash_init_partition("telemetry");
    if (ret == ESP_OK) { ret = nvs_open_from_partition("telemetry", "bb_cmd", NVS_READWRITE, &store); }
    if (ret != ESP_OK) { return ret; }
    opened = true;
    size_t size = sizeof(ledger);
    ret = nvs_get_blob(store, "ledger", &ledger, &size);
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        memset(&next, 0, sizeof(next)); next.magic = COMMAND_MAGIC; next.version = 1;
        strcpy(next.device, device); ret = save();
    } else if (ret == ESP_OK && (size != sizeof(ledger) || ledger.magic != COMMAND_MAGIC || ledger.version != 1 ||
               strcmp(ledger.device, device) || ledger.crc != crc(&ledger))) { ret = ESP_ERR_INVALID_CRC; }
    healthy = ret == ESP_OK;
    return ret;
}

esp_err_t command_manager_receive(const char *payload, size_t length, const char *binding,
                                  int64_t utc_us, int64_t uptime_ms)
{
    if (!healthy || !telemetry_ready() || uptime_ms < 0 || uptime_ms > 9007199254740991LL) { return ESP_ERR_INVALID_STATE; }
    cJSON *root = telemetry_parse_json(payload, length, true);
    const char *id = root ? text(root, "device_id") : NULL;
    const char *bound = root ? text(root, "binding_id") : NULL;
    const char *command = root ? text(root, "command_id") : NULL;
    const char *type = root ? text(root, "type") : NULL;
    cJSON *version = root ? cJSON_GetObjectItemCaseSensitive(root, "schema_version") : NULL;
    cJSON *on = root ? cJSON_GetObjectItemCaseSensitive(root, "desired_on") : NULL;
    int64_t issued = 0, expires = 0;
    bool automatic = type && !strcmp(type, "relay.auto");
    bool valid = root && cJSON_IsNumber(version) && version->valuedouble == 1 && id && !strcmp(id, identity) &&
        bound && telemetry_valid_uuid(bound) && command && telemetry_valid_uuid(command) && type &&
        (automatic ? (!on || cJSON_IsNull(on)) : (!strcmp(type, "relay.set") && cJSON_IsBool(on))) &&
        cJSON_GetArraySize(root) == (on ? 8 : 7) &&
        command_timestamp(text(root, "issued_at"), &issued) && command_timestamp(text(root, "expires_at"), &expires) &&
        expires > issued && expires - issued <= 60000000;
    if (!valid) { cJSON_Delete(root); return ESP_ERR_INVALID_RESPONSE; }
    /* Hash semantic command content, independent of key order/whitespace. */
    char canonical[256], hash[65]; uint8_t bytes[32]; size_t written;
    int n = snprintf(canonical, sizeof(canonical), "%s|%s|%s|%d|%lld|%lld", command, bound, type,
        automatic ? 2 : cJSON_IsTrue(on), (long long)issued, (long long)expires);
    if (n < 0 || n >= sizeof(canonical) || psa_crypto_init() != PSA_SUCCESS ||
        psa_hash_compute(PSA_ALG_SHA_256, (uint8_t *)canonical, n, bytes, sizeof(bytes), &written) != PSA_SUCCESS || written != 32) {
        cJSON_Delete(root); return ESP_FAIL;
    }
    for (unsigned i = 0; i < 32; ++i) { snprintf(hash + 2*i, 3, "%02x", bytes[i]); }
    unsigned slot = COMMAND_CAPACITY;
    for (unsigned i = 0; i < COMMAND_CAPACITY; ++i) {
        entry_t *entry = &ledger.entries[i];
        if (entry->phase && !strcmp(entry->id, command)) {
            bool same = !strcmp(entry->digest, hash);
            cJSON_Delete(root);
            if (!same) { return ESP_ERR_INVALID_RESPONSE; }
            /* Replay original evidence; never enqueue this command twice. */
            next = ledger;
            if (next.entries[i].accepted.wire.length) { next.entries[i].accepted.acked = 0; }
            if (next.entries[i].terminal.wire.length) { next.entries[i].terminal.acked = 0; }
            return save();
        }
        if (!entry->phase || (entry->phase == 2 && entry->accepted.acked && entry->terminal.acked && utc_us >= entry->expires_us)) { slot = i; }
    }
    if (slot == COMMAND_CAPACITY) { cJSON_Delete(root); return ESP_ERR_NO_MEM; }
    bool desired = cJSON_IsTrue(on);
    next = ledger; entry_t *entry = &next.entries[slot]; memset(entry, 0, sizeof(*entry));
    strcpy(entry->id, command); strcpy(entry->binding, bound); strcpy(entry->digest, hash); entry->expires_us = expires;
    entry->accepted.acked = entry->terminal.acked = 1;
    cJSON_Delete(root);
    const char *rejected = utc_us <= 0 ? "clock_unsynchronized" : utc_us < issued ? "command_not_yet_valid" :
        utc_us >= expires ? "command_expired" : !binding || strcmp(binding, entry->binding) || !current_binding(entry->binding) ? "binding_changed" : NULL;
    relay_control_state_t state;
    const relay_control_state_t *view = relay_control_get_state(&state) == ESP_OK ? &state : NULL;
    esp_err_t ret;
    if (rejected) {
        entry->phase = 2;
        ret = result(&entry->terminal, entry, "rejected", rejected, view, utc_us, uptime_ms);
        return ret == ESP_OK ? save() : ret;
    }
    entry->phase = 1;
    ret = result(&entry->accepted, entry, "accepted", "queued", view, utc_us, uptime_ms);
    if (ret != ESP_OK || (ret = save()) != ESP_OK) { return ret; }
    relay_command_request_t request = {.token = slot + 1, .automatic = automatic, .on = desired,
        .issued_us = issued, .expires_us = expires, .deadline_ms = uptime_ms + (expires - utc_us + 999) / 1000,
        .binding_current = current_binding};
    strcpy(request.binding_id, ledger.entries[slot].binding);
    ret = relay_control_request_command(&request);
    if (ret != ESP_OK) {
        next = ledger; entry = &next.entries[slot]; entry->phase = 2;
        ret = result(&entry->terminal, entry, "failed", "control_queue_unavailable", view, utc_us, uptime_ms);
        return ret == ESP_OK ? save() : ret;
    }
    ESP_LOGI(TAG, "Command admitted: id=%s token=%u", ledger.entries[slot].id, slot + 1);
    return ESP_OK;
}

void command_manager_poll(int64_t utc_us, int64_t uptime_ms)
{
    if (!healthy) { return; }
    relay_command_completion_t completed;
    while (relay_control_take_completion(&completed)) {
        unsigned index = completed.token - 1;
        if (index >= COMMAND_CAPACITY || ledger.entries[index].phase != 1) { continue; }
        next = ledger; entry_t *entry = &next.entries[index]; entry->phase = 2;
        if (result(&entry->terminal, entry, completed.result, completed.reason, &completed.state,
                   completed.completed_us, completed.completed_uptime_ms) != ESP_OK || save() != ESP_OK) {
            healthy = false; return;
        }
        ESP_LOGI(TAG, "Command result: id=%s result=%s reason=%s observed=%s mode=%s",
            entry->id, completed.result, completed.reason, completed.state.known ? completed.state.on ? "ON" : "OFF" : "unknown",
            completed.state.mode == RELAY_MODE_AUTO ? "AUTO" : "MANUAL");
    }
    for (unsigned i = 0; i < COMMAND_CAPACITY; ++i) {
        entry_t *entry = &ledger.entries[i];
        /* A pending record from a previous boot is evidence of uncertainty.
         * Never reissue it, even if its expiry has not passed yet. */
        if (entry->phase == 1 && strcmp(entry->accepted.boot, boot_id)) {
            next = ledger; entry = &next.entries[i]; entry->phase = 2;
            if (result(&entry->terminal, entry, "failed", "interrupted_by_restart", NULL, utc_us, uptime_ms) != ESP_OK || save() != ESP_OK) {
                healthy = false; return;
            }
        }
    }
}

esp_err_t command_manager_peek(const command_result_wire_t **out)
{
    if (!out) { return ESP_ERR_INVALID_ARG; } *out = NULL;
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    for (unsigned i = 0; i < COMMAND_CAPACITY; ++i) {
        result_t *slots[] = {&ledger.entries[i].accepted, &ledger.entries[i].terminal};
        for (unsigned j = 0; j < 2; ++j) {
            if (slots[j]->wire.length && !slots[j]->acked) { *out = &slots[j]->wire; return ESP_OK; }
        }
    }
    return ESP_ERR_NOT_FOUND;
}

esp_err_t command_manager_ack(const char *payload, size_t length)
{
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    cJSON *root = telemetry_parse_json(payload, length, true);
    const char *id = root ? text(root, "device_id") : NULL, *boot = root ? text(root, "boot_id") : NULL;
    const char *kind = root ? text(root, "event_kind") : NULL, *outcome = root ? text(root, "result") : NULL;
    cJSON *version = root ? cJSON_GetObjectItemCaseSensitive(root, "schema_version") : NULL;
    cJSON *seq = root ? cJSON_GetObjectItemCaseSensitive(root, "seq") : NULL;
    bool valid = root && cJSON_GetArraySize(root) == 6 && id && !strcmp(id, identity) && boot && telemetry_valid_uuid(boot) &&
        kind && !strcmp(kind, "command_result") && outcome && (!strcmp(outcome, "stored") || !strcmp(outcome, "duplicate")) &&
        cJSON_IsNumber(version) && version->valuedouble == 1 && cJSON_IsNumber(seq) && seq->valuedouble >= 0 && seq->valuedouble <= UINT32_MAX;
    bool found = false; next = ledger;
    if (valid) {
        for (unsigned i = 0; i < COMMAND_CAPACITY; ++i) {
            result_t *slots[] = {&next.entries[i].accepted, &next.entries[i].terminal};
            for (unsigned j = 0; j < 2; ++j) {
                if (slots[j]->wire.length && !slots[j]->acked && slots[j]->seq == (uint32_t)seq->valuedouble && !strcmp(slots[j]->boot, boot)) {
                    slots[j]->acked = 1; found = true;
                }
            }
        }
    }
    cJSON_Delete(root);
    if (!valid) { return ESP_ERR_INVALID_RESPONSE; }
    return found ? save() : ESP_ERR_NOT_FOUND;
}
