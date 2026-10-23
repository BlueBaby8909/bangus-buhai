#include "telemetry.h"

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include "cJSON.h"
#include "esp_crc.h"
#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "psa/crypto.h"

#define SLOT_COUNT (TELEMETRY_CAPACITY + 1U)
#define MANIFEST_MAGIC 0x42425131U
#define RECORD_MAGIC 0x42425231U
#define STORE_VERSION 1U

typedef struct {
    uint32_t slot, seq, length;
    char boot_id[37];
} entry_t;

typedef struct {
    uint32_t magic, version, count;
    entry_t entries[TELEMETRY_CAPACITY];
    uint32_t crc;
} manifest_t;

typedef struct {
    uint32_t magic, version, length, crc;
    char payload[TELEMETRY_MAX_PAYLOAD];
} record_t;

static const char *TAG = "telemetry";
static nvs_handle_t store;
static bool opened, healthy, head_cached;
static manifest_t manifest;
static record_t record; /* Worker-owned reusable buffers, not task-stack arrays. */
static telemetry_event_t head;
static char device_id[16], boot_id[37], binding_id[37], fw_version[65];
static uint64_t next_seq;
static int64_t capture_at;
static uint32_t dropped;

/* Conservative capacity bound: two 4 KiB pages per largest blob, plus manifest
 * versions and spare GC pages, below the dedicated 256 KiB partition size. */
_Static_assert(SLOT_COUNT * 8192U + 3U * 8192U < 256U * 1024U, "Telemetry NVS capacity too small");

bool telemetry_ack_fragment(telemetry_ack_assembly_t *assembly, bool topic_matches, bool retained,
                            int mid, size_t offset, size_t total, const char *data, size_t length)
{
    if (!assembly) { return false; }
    if (!offset) {
        assembly->active = false;
        assembly->offset = 0;
        if (!topic_matches || retained || !total || total > TELEMETRY_MAX_PAYLOAD) { return false; }
        assembly->message.length = total; assembly->mid = mid; assembly->active = true;
    }
    if (!assembly->active) { return false; }
    if (retained || mid != assembly->mid || offset != assembly->offset ||
        total != assembly->message.length || !data || !length || length > total - assembly->offset) {
        assembly->active = false; return false;
    }
    memcpy(assembly->message.data + assembly->offset, data, length);
    assembly->offset += length;
    if (assembly->offset != total) { return false; }
    assembly->message.data[total] = 0;
    assembly->active = false;
    return true;
}

bool telemetry_valid_uuid(const char *s)
{
    if (!s || strlen(s) != 36) { return false; }
    for (unsigned i = 0; i < 36; ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (s[i] != '-') { return false; }
        } else if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) {
            return false;
        }
    }
    return true;
}

static bool valid_device(const char *s)
{
    if (!s || strlen(s) != 15 || memcmp(s, "BB-", 3)) { return false; }
    for (unsigned i = 3; i < 15; ++i) {
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'A' && s[i] <= 'F'))) { return false; }
    }
    return true;
}

/* cJSON does not validate UTF-8. Reject overlong encodings and surrogates. */
static bool valid_utf8(const unsigned char *s, size_t length)
{
    for (size_t i = 0; i < length;) {
        unsigned c = s[i++], value, tail;
        if (c < 0x80) { if (!c) { return false; } continue; }
        if (c >= 0xc2 && c <= 0xdf) { value = c & 31; tail = 1; }
        else if (c >= 0xe0 && c <= 0xef) { value = c & 15; tail = 2; }
        else if (c >= 0xf0 && c <= 0xf4) { value = c & 7; tail = 3; }
        else { return false; }
        if (length - i < tail) { return false; }
        for (unsigned n = 0; n < tail; ++n) {
            c = s[i++];
            if ((c & 0xc0) != 0x80) { return false; }
            value = (value << 6) | (c & 63);
        }
        if ((tail == 1 && value < 0x80) || (tail == 2 && value < 0x800) ||
            (tail == 3 && value < 0x10000) || value > 0x10ffff ||
            (value >= 0xd800 && value <= 0xdfff)) { return false; }
    }
    return true;
}

static bool clean_tree(const cJSON *item)
{
    if (cJSON_IsNumber(item) && !isfinite(item->valuedouble)) { return false; }
    for (const cJSON *child = item->child; child; child = child->next) {
        if (cJSON_IsObject(item)) {
            for (const cJSON *other = child->next; other; other = other->next) {
                if (!strcmp(child->string, other->string)) { return false; }
            }
        }
        if (!clean_tree(child)) { return false; }
    }
    return true;
}

static bool whitespace(char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; }

cJSON *telemetry_parse_json(const char *data, size_t length, bool integer_numbers)
{
    if (!data || !length || length > TELEMETRY_MAX_PAYLOAD ||
        !valid_utf8((const unsigned char *)data, length)) { return NULL; }
    bool quoted = false;
    unsigned depth = 0;
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)data[i];
        if (quoted) {
            if (c == '\\') {
                if (++i >= length) { return NULL; }
                /* Embedded string NUL would hide identity/key suffixes in cJSON. */
                if (data[i] == 'u' && length - i >= 5 && !memcmp(data + i + 1, "0000", 4)) { return NULL; }
            } else if (c == '"') { quoted = false; }
            else if (c < 0x20) { return NULL; }
        } else if (c == '"') { quoted = true; }
        else if (c == '{' || c == '[') { if (++depth > 8) { return NULL; } }
        else if (c == '}' || c == ']') { if (!depth) { return NULL; } --depth; }
        else if (integer_numbers && (c == '-' || (c >= '0' && c <= '9'))) {
            if (c == '-') {
                if (++i >= length || data[i] < '0' || data[i] > '9') { return NULL; }
                c = (unsigned char)data[i];
            }
            if (c == '0') {
                if (i + 1 < length && data[i + 1] >= '0' && data[i + 1] <= '9') { return NULL; }
            } else {
                while (i + 1 < length && data[i + 1] >= '0' && data[i + 1] <= '9') { ++i; }
            }
            if (i + 1 < length && !whitespace(data[i + 1]) && data[i + 1] != ',' &&
                data[i + 1] != '}' && data[i + 1] != ']') { return NULL; }
        }
        /* Integer tokens above reject fractions/exponents at their boundary.
         * Do not reject 'e' globally: it also terminates true and false. */
        else if (c < 0x20 && !whitespace((char)c)) { return NULL; }
    }
    if (quoted || depth) { return NULL; }
    const char *end = NULL;
    cJSON *root = cJSON_ParseWithLengthOpts(data, length, &end, false);
    if (root) {
        while (end < data + length && whitespace(*end)) { ++end; }
        if (end != data + length || !cJSON_IsObject(root) || !clean_tree(root)) {
            cJSON_Delete(root); root = NULL;
        }
    }
    return root;
}

static const char *string_field(const cJSON *root, const char *name)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, name);
    return cJSON_IsString(item) ? item->valuestring : NULL;
}

static bool uint_field(const cJSON *root, const char *name, uint32_t *out)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, name);
    if (!cJSON_IsNumber(item) || item->valuedouble < 0 || item->valuedouble > UINT32_MAX ||
        floor(item->valuedouble) != item->valuedouble) { return false; }
    *out = (uint32_t)item->valuedouble;
    return true;
}

static uint32_t manifest_crc(const manifest_t *value)
{
    return esp_crc32_le(0, (const uint8_t *)value, offsetof(manifest_t, crc));
}

static esp_err_t fault(esp_err_t error)
{
    healthy = false; /* A failed commit has an uncertain durable outcome: reopen on reboot. */
    ESP_LOGE(TAG, "Storage paused: %s; data preserved, no automatic erase", esp_err_to_name(error));
    return error;
}

static void slot_key(uint32_t slot, char key[8]) { snprintf(key, 8, "r%02lu", (unsigned long)slot); }

static esp_err_t commit_manifest(manifest_t *next)
{
    next->crc = manifest_crc(next);
    esp_err_t ret = nvs_set_blob(store, "manifest", next, sizeof(*next));
    if (ret == ESP_OK) { ret = nvs_commit(store); }
    if (ret != ESP_OK) { return fault(ret); }
    manifest = *next;
    return ESP_OK;
}

static esp_err_t read_entry(const entry_t *entry)
{
    char key[8]; slot_key(entry->slot, key);
    size_t bytes = sizeof(record);
    esp_err_t ret = nvs_get_blob(store, key, &record, &bytes);
    if (ret != ESP_OK) { return ret; }
    if (record.magic != RECORD_MAGIC || record.version != STORE_VERSION ||
        record.length != entry->length || record.length > TELEMETRY_MAX_PAYLOAD ||
        bytes != offsetof(record_t, payload) + record.length ||
        record.crc != esp_crc32_le(0, (const uint8_t *)record.payload, record.length)) {
        return ESP_ERR_INVALID_CRC;
    }
    cJSON *json = telemetry_parse_json(record.payload, record.length, false);
    uint32_t seq, version;
    const char *id = json ? string_field(json, "device_id") : NULL;
    const char *boot = json ? string_field(json, "boot_id") : NULL;
    bool valid = json && id && boot && !strcmp(id, device_id) && !strcmp(boot, entry->boot_id) &&
        uint_field(json, "seq", &seq) && seq == entry->seq &&
        uint_field(json, "schema_version", &version) && version == 1;
    cJSON_Delete(json);
    return valid ? ESP_OK : ESP_ERR_INVALID_RESPONSE;
}

void telemetry_close(void)
{
    if (opened) { nvs_close(store); }
    opened = healthy = head_cached = false;
}

esp_err_t telemetry_init(const telemetry_config_t *config)
{
    telemetry_close();
    if (!config || !valid_device(config->device_id) || !telemetry_valid_uuid(config->boot_id) ||
        (config->binding_id && !telemetry_valid_uuid(config->binding_id)) || !config->fw_version ||
        !strlen(config->fw_version) || strlen(config->fw_version) > 64 ||
        !valid_utf8((const unsigned char *)config->fw_version, strlen(config->fw_version))) { return ESP_ERR_INVALID_ARG; }
    strcpy(device_id, config->device_id); strcpy(boot_id, config->boot_id);
    binding_id[0] = 0;
    if (config->binding_id) { strcpy(binding_id, config->binding_id); }
    strcpy(fw_version, config->fw_version);
    next_seq = dropped = 0;
    capture_at = 0;
    memset(&manifest, 0, sizeof(manifest));
    esp_err_t ret = nvs_flash_init_partition("telemetry");
    if (ret == ESP_OK) { ret = nvs_open_from_partition("telemetry", "queue", NVS_READWRITE, &store); }
    if (ret != ESP_OK) { return fault(ret); }
    opened = true;
    size_t bytes = sizeof(manifest);
    ret = nvs_get_blob(store, "manifest", &manifest, &bytes);
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        memset(&manifest, 0, sizeof(manifest));
        manifest.magic = MANIFEST_MAGIC; manifest.version = STORE_VERSION;
        ret = commit_manifest(&manifest);
    } else if (ret == ESP_OK && (bytes != sizeof(manifest) || manifest.magic != MANIFEST_MAGIC ||
               manifest.version != STORE_VERSION || manifest.count > TELEMETRY_CAPACITY ||
               manifest.crc != manifest_crc(&manifest))) { ret = ESP_ERR_INVALID_CRC; }
    if (ret != ESP_OK) { return fault(ret); }
    bool used[SLOT_COUNT] = {0};
    for (uint32_t i = 0; i < manifest.count; ++i) {
        const entry_t *entry = &manifest.entries[i];
        if (entry->slot >= SLOT_COUNT || used[entry->slot] || !entry->length ||
            entry->length > TELEMETRY_MAX_PAYLOAD || entry->boot_id[36] ||
            !telemetry_valid_uuid(entry->boot_id)) { return fault(ESP_ERR_INVALID_RESPONSE); }
        for (uint32_t j = 0; j < i; ++j) {
            if (entry->seq == manifest.entries[j].seq && !strcmp(entry->boot_id, manifest.entries[j].boot_id)) {
                return fault(ESP_ERR_INVALID_RESPONSE);
            }
        }
        used[entry->slot] = true;
        ret = read_entry(entry);
        if (ret != ESP_OK) { return fault(ret); }
    }
    bool reclaimed = false;
    for (uint32_t slot = 0; slot < SLOT_COUNT; ++slot) {
        if (used[slot]) { continue; }
        char key[8]; slot_key(slot, key);
        ret = nvs_erase_key(store, key);
        if (ret == ESP_OK) { reclaimed = true; }
        else if (ret != ESP_ERR_NVS_NOT_FOUND) { return fault(ret); }
    }
    if (reclaimed && (ret = nvs_commit(store)) != ESP_OK) { return fault(ret); }
    healthy = true;
    ESP_LOGI(TAG, "Restored %lu pending readings; capture binding=%s",
             (unsigned long)manifest.count, binding_id);
    return ESP_OK;
}

bool telemetry_ready(void) { return healthy; }
esp_err_t telemetry_allocate_sequence(uint32_t *out)
{
    if (!healthy || !out || next_seq > UINT32_MAX) { return ESP_ERR_INVALID_STATE; }
    *out = (uint32_t)next_seq++;
    return ESP_OK;
}
uint32_t telemetry_pending(void) { return manifest.count; }
uint32_t telemetry_dropped(void) { return dropped; }
bool telemetry_capture_due(int64_t now_us)
{
    if (now_us < capture_at) { return false; }
    capture_at += ((now_us - capture_at) / TELEMETRY_INTERVAL_US + 1) * TELEMETRY_INTERVAL_US;
    return true;
}

static bool add_integer(cJSON *root, const char *name, int64_t value)
{
    /* cJSON's generic number printer can use exponent notation for large ages;
     * the wire contract requires JSON integers, not integral floating values. */
    char text[24];
    snprintf(text, sizeof(text), "%lld", (long long)value);
    return cJSON_AddRawToObject(root, name, text) != NULL;
}

static bool add_number_or_null(cJSON *root, const char *name, int64_t value)
{
    return value < 0 ? cJSON_AddNullToObject(root, name) != NULL :
                      add_integer(root, name, value);
}

static bool reading_compatible(const sensor_value_t *value, const char *unit, bool ph, int64_t uptime)
{
    if (!value->unit || strcmp(value->unit, unit) || !value->source ||
        value->validity < SENSOR_VALID || value->validity > SENSOR_UNVERIFIED ||
        value->sample_age_ms < -1 || value->last_valid_age_ms < -1 ||
        value->sample_age_ms > uptime || value->last_valid_age_ms > uptime ||
        (value->has_value && !isfinite(value->value))) { return false; }
    if (ph && !strcmp(value->source, "default")) {
        return value->has_value && value->validity == SENSOR_UNVERIFIED &&
               value->sample_age_ms == -1 && value->last_valid_age_ms == -1;
    }
    if (strcmp(value->source, "sensor")) { return false; }
    if ((value->validity == SENSOR_MISSING || value->validity == SENSOR_INVALID) && value->has_value) { return false; }
    if ((value->validity == SENSOR_VALID || value->validity == SENSOR_UNVERIFIED) && !value->has_value) { return false; }
    if (value->has_value && value->sample_age_ms < 0 && value->validity != SENSOR_UNVERIFIED) { return false; }
    return value->validity != SENSOR_VALID ||
           (value->sample_age_ms >= 0 && value->sample_age_ms == value->last_valid_age_ms &&
            (strcmp(unit, "degC") || value->sample_age_ms < 60000));
}

static bool add_reading(cJSON *root, const char *name, const sensor_value_t *value)
{
    cJSON *json = cJSON_AddObjectToObject(root, name);
    if (!json || !cJSON_AddStringToObject(json, "unit", value->unit) ||
        !cJSON_AddStringToObject(json, "source", value->source) ||
        !cJSON_AddStringToObject(json, "validity", sensor_validity_name(value->validity))) { return false; }
    if (value->has_value) {
        if (!isfinite(value->value) || !cJSON_AddNumberToObject(json, "value", value->value)) { return false; }
    } else if (!cJSON_AddNullToObject(json, "value")) { return false; }
    return add_number_or_null(json, "sample_age_ms", value->sample_age_ms) &&
           add_number_or_null(json, "last_valid_age_ms", value->last_valid_age_ms);
}

static esp_err_t serialize(const sensor_reading_t *snapshot, const relay_control_state_t *relay,
                           const time_t *utc, uint32_t reconnects, uint32_t seq, uint32_t losses)
{
    cJSON *root = cJSON_CreateObject();
    if (!root) { return ESP_ERR_NO_MEM; }
    char timestamp[32];
    struct tm tm;
    if (utc && (!gmtime_r(utc, &tm) || strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &tm) != 20)) {
        cJSON_Delete(root); return ESP_ERR_INVALID_ARG;
    }
    cJSON *values = NULL, *state = NULL, *diagnostics = NULL;
    bool ok = cJSON_AddNumberToObject(root, "schema_version", 1) &&
        cJSON_AddStringToObject(root, "device_id", device_id) &&
        cJSON_AddStringToObject(root, "binding_id", binding_id) &&
        cJSON_AddStringToObject(root, "boot_id", boot_id) &&
        add_integer(root, "seq", seq) &&
        cJSON_AddStringToObject(root, "fw_version", fw_version) &&
        cJSON_AddStringToObject(root, "time_quality", utc ? "synchronized" : "unsynchronized") &&
        (utc ? cJSON_AddStringToObject(root, "measured_at", timestamp) : cJSON_AddNullToObject(root, "measured_at")) &&
        add_integer(root, "capture_uptime_ms", snapshot->capture_uptime_ms) &&
        (values = cJSON_AddObjectToObject(root, "readings")) &&
        add_reading(values, "temperature", &snapshot->temperature) &&
        add_reading(values, "turbidity", &snapshot->turbidity) && add_reading(values, "ph", &snapshot->ph) &&
        (state = cJSON_AddObjectToObject(root, "relay")) &&
        cJSON_AddStringToObject(state, "mode", "demo") &&
        (relay && relay->known ? cJSON_AddBoolToObject(state, "on", relay->on) : cJSON_AddNullToObject(state, "on")) &&
        cJSON_AddStringToObject(state, "reason", !relay || !relay->known ? "unavailable" :
            relay->error != ESP_OK ? "output_error" : relay->safety_inhibited ? "safety_inhibited" :
            relay->mode == RELAY_MODE_MANUAL ? "manual" : "automatic") &&
        (diagnostics = cJSON_AddObjectToObject(root, "diagnostics")) &&
        add_integer(diagnostics, "queue_dropped", losses) &&
        add_integer(diagnostics, "reconnects", reconnects);
    if (ok) { ok = cJSON_PrintPreallocated(root, head.payload, sizeof(head.payload), false); }
    cJSON_Delete(root);
    if (!ok) { return ESP_ERR_NO_MEM; }
    head.length = strlen(head.payload);
    head.seq = seq; strcpy(head.boot_id, boot_id);
    return ESP_OK;
}

esp_err_t telemetry_capture(const sensor_reading_t *snapshot, const relay_control_state_t *relay,
                            const time_t *utc, uint32_t reconnects)
{
    if (!binding_id[0]) { return ESP_ERR_INVALID_STATE; }
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    if (!snapshot || snapshot->capture_uptime_ms < 0 || snapshot->capture_uptime_ms > 9007199254740991LL ||
        next_seq > UINT32_MAX ||
        !reading_compatible(&snapshot->temperature, "degC", false, snapshot->capture_uptime_ms) ||
        !reading_compatible(&snapshot->turbidity, "NTU", false, snapshot->capture_uptime_ms) ||
        !reading_compatible(&snapshot->ph, "pH", true, snapshot->capture_uptime_ms)) { return ESP_ERR_INVALID_ARG; }
    bool full = manifest.count == TELEMETRY_CAPACITY;
    uint32_t losses = dropped + (full && dropped < UINT32_MAX);
    head_cached = false;
    esp_err_t ret = serialize(snapshot, relay, utc, reconnects, (uint32_t)next_seq++, losses);
    if (ret != ESP_OK) { return ret; }
    bool used[SLOT_COUNT] = {0};
    for (uint32_t i = 0; i < manifest.count; ++i) { used[manifest.entries[i].slot] = true; }
    uint32_t slot = 0;
    while (slot < SLOT_COUNT && used[slot]) { ++slot; }
    if (slot == SLOT_COUNT) { return fault(ESP_ERR_INVALID_STATE); }
    record.magic = RECORD_MAGIC; record.version = STORE_VERSION; record.length = (uint32_t)head.length;
    memcpy(record.payload, head.payload, head.length);
    record.crc = esp_crc32_le(0, (const uint8_t *)record.payload, record.length);
    char key[8]; slot_key(slot, key);
    ret = nvs_set_blob(store, key, &record, offsetof(record_t, payload) + record.length);
    if (ret == ESP_OK) { ret = nvs_commit(store); }
    if (ret != ESP_OK) { return fault(ret); }
    manifest_t next = manifest;
    uint32_t displaced = full ? next.entries[0].slot : SLOT_COUNT;
    if (full) {
        memmove(next.entries, next.entries + 1, (TELEMETRY_CAPACITY - 1) * sizeof(entry_t));
        --next.count;
    }
    entry_t *entry = &next.entries[next.count++];
    memset(entry, 0, sizeof(*entry));
    entry->slot = slot; entry->seq = head.seq; entry->length = (uint32_t)head.length;
    strcpy(entry->boot_id, head.boot_id);
    ret = commit_manifest(&next);
    if (ret != ESP_OK) { return ret; }
    dropped = losses;
    if (full) {
        ESP_LOGW(TAG, "Queue full: oldest event dropped; current-boot losses=%lu", (unsigned long)dropped);
        slot_key(displaced, key);
        ret = nvs_erase_key(store, key);
        if (ret == ESP_OK) { ret = nvs_commit(store); }
        if (ret != ESP_OK) { return fault(ret); }
    }
    ESP_LOGI(TAG, "Captured boot=%s seq=%lu; %lu pending", head.boot_id,
             (unsigned long)head.seq, (unsigned long)manifest.count);
    return ESP_OK;
}

esp_err_t telemetry_peek(const telemetry_event_t **event)
{
    if (!event) { return ESP_ERR_INVALID_ARG; }
    *event = NULL;
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    if (!manifest.count) { return ESP_ERR_NOT_FOUND; }
    if (head_cached) { *event = &head; return ESP_OK; }
    const entry_t *entry = &manifest.entries[0];
    esp_err_t ret = read_entry(entry);
    if (ret != ESP_OK) { return fault(ret); }
    head.length = entry->length; head.seq = entry->seq;
    strcpy(head.boot_id, entry->boot_id);
    memcpy(head.payload, record.payload, head.length); head.payload[head.length] = 0;
    head_cached = true;
    *event = &head;
    return ESP_OK;
}

esp_err_t telemetry_set_binding(const char *binding)
{
    if (binding && !telemetry_valid_uuid(binding)) { return ESP_ERR_INVALID_ARG; }
    binding_id[0] = 0;
    if (binding) { strcpy(binding_id, binding); }
    return ESP_OK;
}

static esp_err_t release_entry(uint32_t found, const char *label)
{
    manifest_t next = manifest;
    uint32_t released = next.entries[found].slot, seq = next.entries[found].seq;
    memmove(next.entries + found, next.entries + found + 1, (next.count - found - 1) * sizeof(entry_t));
    memset(&next.entries[--next.count], 0, sizeof(entry_t));
    esp_err_t ret = commit_manifest(&next);
    if (ret != ESP_OK) { return ret; }
    head_cached = false;
    char key[8]; slot_key(released, key);
    ret = nvs_erase_key(store, key);
    if (ret == ESP_OK) { ret = nvs_commit(store); }
    if (ret != ESP_OK) { return fault(ret); }
    ESP_LOGI(TAG, "%s seq=%lu; %lu pending", label, (unsigned long)seq, (unsigned long)manifest.count);
    return ESP_OK;
}

esp_err_t telemetry_accept_ack(const char *payload, size_t length)
{
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    cJSON *json = telemetry_parse_json(payload, length, true);
    if (!json) { return ESP_ERR_INVALID_RESPONSE; }
    const char *id = string_field(json, "device_id"), *boot = string_field(json, "boot_id");
    const char *kind = string_field(json, "event_kind"), *result = string_field(json, "result");
    uint32_t version, seq;
    bool valid = cJSON_GetArraySize(json) == 6 && id && boot && kind && result &&
        !strcmp(id, device_id) && telemetry_valid_uuid(boot) && !strcmp(kind, "telemetry") &&
        (!strcmp(result, "stored") || !strcmp(result, "duplicate")) &&
        uint_field(json, "schema_version", &version) && version == 1 && uint_field(json, "seq", &seq);
    uint32_t found = manifest.count;
    if (valid) {
        for (uint32_t i = 0; i < manifest.count; ++i) {
            if (seq == manifest.entries[i].seq && !strcmp(boot, manifest.entries[i].boot_id)) { found = i; break; }
        }
    }
    cJSON_Delete(json);
    if (!valid) { return ESP_ERR_INVALID_RESPONSE; }
    if (found == manifest.count) { return ESP_ERR_NOT_FOUND; }
    return release_entry(found, "Application acknowledged");
}

esp_err_t telemetry_accept_quarantine_receipt(const char *payload, size_t length)
{
    if (!healthy) { return ESP_ERR_INVALID_STATE; }
    cJSON *root = telemetry_parse_json(payload, length, true);
    const char *id = root ? string_field(root, "device_id") : NULL;
    const char *boot = root ? string_field(root, "boot_id") : NULL;
    const char *kind = root ? string_field(root, "event_kind") : NULL;
    const char *receipt = root ? string_field(root, "quarantine_id") : NULL;
    const char *reason = root ? string_field(root, "reason") : NULL;
    const char *hash = root ? string_field(root, "payload_sha256") : NULL;
    uint32_t version, seq;
    bool valid = root && cJSON_GetArraySize(root) == 8 && id && boot && kind && receipt && reason && hash &&
        !strcmp(id, device_id) && telemetry_valid_uuid(boot) && !strcmp(kind, "telemetry") &&
        telemetry_valid_uuid(receipt) && strlen(hash) == 64 && strlen(reason) > 0 && strlen(reason) <= 64 &&
        reason[0] >= 'a' && reason[0] <= 'z' &&
        uint_field(root, "schema_version", &version) && version == 1 && uint_field(root, "seq", &seq);
    if (valid) {
        for (const char *c = reason; *c; ++c) {
            if (!((*c >= 'a' && *c <= 'z') || (*c >= '0' && *c <= '9') || *c == '_')) { valid = false; }
        }
    }
    const telemetry_event_t *event = NULL;
    if (valid && telemetry_peek(&event) == ESP_OK && seq == event->seq && !strcmp(boot, event->boot_id)) {
        unsigned char bytes[32]; size_t written = 0;
        char expected[65];
        if (psa_crypto_init() != PSA_SUCCESS || psa_hash_compute(PSA_ALG_SHA_256,
                (const uint8_t *)event->payload, event->length, bytes, sizeof(bytes), &written) != PSA_SUCCESS || written != 32) {
            cJSON_Delete(root); return ESP_FAIL;
        }
        for (unsigned i = 0; i < 32; ++i) { snprintf(expected + 2*i, 3, "%02x", bytes[i]); }
        valid = !strcmp(expected, hash);
    } else { valid = false; }
    cJSON_Delete(root);
    if (!valid) { return ESP_ERR_INVALID_RESPONSE; }
    return release_entry(0, "Quarantine custody confirmed (excluded from tank history)");
}
