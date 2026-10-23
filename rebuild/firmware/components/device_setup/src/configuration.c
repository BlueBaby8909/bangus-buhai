#include "device_setup.h"
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <math.h>
#include "telemetry.h"
#include "cJSON.h"
#include "esp_crc.h"
#include "nvs.h"

#define SETUP_MAGIC 0x42425331U

static const char *text(const cJSON *root, const char *name)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, name);
    return cJSON_IsString(item) ? item->valuestring : NULL;
}

static bool uuid(const cJSON *root, const char *name, char out[37], bool nullable)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, name);
    if (nullable && cJSON_IsNull(item)) { out[0] = 0; return true; }
    if (!cJSON_IsString(item) || !telemetry_valid_uuid(item->valuestring)) { return false; }
    strcpy(out, item->valuestring); return true;
}

esp_err_t device_setup_parse(const char *json, size_t length, const char *device, device_setup_config_t *out)
{
    if (!device || !out) { return ESP_ERR_INVALID_ARG; }
    cJSON *root = telemetry_parse_json(json, length, true);
    const cJSON *doc = root ? cJSON_GetObjectItemCaseSensitive(root, "document") : NULL;
    const char *id = doc ? text(doc, "device_id") : NULL;
    const char *digest = root ? text(root, "digest") : NULL;
    const cJSON *revision = doc ? cJSON_GetObjectItemCaseSensitive(doc, "revision") : NULL;
    const cJSON *version = doc ? cJSON_GetObjectItemCaseSensitive(doc, "schema_version") : NULL;
    const cJSON *archived = doc ? cJSON_GetObjectItemCaseSensitive(doc, "archived") : NULL;
    const cJSON *confirmed = root ? cJSON_GetObjectItemCaseSensitive(root, "confirmed_revision") : NULL;
    device_setup_config_t value = { .magic = SETUP_MAGIC, .version = 1 };
    bool valid = root && cJSON_GetArraySize(root) == 5 && cJSON_IsObject(doc) && cJSON_GetArraySize(doc) == 7 &&
        id && strlen(id) == 15 && !strcmp(id, device) && digest && strlen(digest) == 64 &&
        cJSON_IsNumber(version) && version->valuedouble == 1 &&
        cJSON_IsNumber(revision) && revision->valuedouble >= 1 && revision->valuedouble <= UINT32_MAX &&
        cJSON_IsBool(archived) && cJSON_IsNumber(confirmed) && confirmed->valuedouble >= 0 &&
        confirmed->valuedouble <= revision->valuedouble &&
        uuid(doc, "hatchery_id", value.hatchery_id, false) && uuid(doc, "tank_id", value.tank_id, true) &&
        uuid(doc, "binding_id", value.binding_id, true) && (!!value.tank_id[0] == !!value.binding_id[0]);
    if (valid) {
        strcpy(value.device_id, id); value.revision = (uint32_t)revision->valuedouble;
        value.confirmed = confirmed->valuedouble == revision->valuedouble;
        value.archived = cJSON_IsTrue(archived);
        const char *status = text(root, "status");
        valid = status && !strcmp(status, value.confirmed ? "confirmed" : "pending");
        char canonical[512], tank[40] = "null", binding[40] = "null";
        if (value.tank_id[0]) { snprintf(tank, sizeof(tank), "\"%s\"", value.tank_id); }
        if (value.binding_id[0]) { snprintf(binding, sizeof(binding), "\"%s\"", value.binding_id); }
        int size = snprintf(canonical, sizeof(canonical),
            "{\"archived\":%s,\"binding_id\":%s,\"device_id\":\"%s\",\"hatchery_id\":\"%s\",\"revision\":%lu,\"schema_version\":1,\"tank_id\":%s}",
            value.archived ? "true" : "false", binding, id, value.hatchery_id, (unsigned long)value.revision, tank);
        valid = valid && size > 0 && size < sizeof(canonical) &&
            device_setup_sha256(canonical, size, value.digest) == ESP_OK && !strcmp(value.digest, digest);
    }
    cJSON_Delete(root);
    if (!valid) { return ESP_ERR_INVALID_RESPONSE; }
    *out = value; return ESP_OK;
}

static uint32_t checksum(const device_setup_config_t *value)
{
    return esp_crc32_le(0, (const uint8_t *)value, offsetof(device_setup_config_t, crc));
}

static bool valid_record(const device_setup_config_t *value)
{
    return value->magic == SETUP_MAGIC && value->version == 1 && value->revision &&
        value->confirmed <= 1 && value->archived <= 1 &&
        value->device_id[15] == 0 && value->hatchery_id[36] == 0 &&
        value->tank_id[36] == 0 && value->binding_id[36] == 0 && value->digest[64] == 0 &&
        telemetry_valid_uuid(value->hatchery_id) && (!value->tank_id[0] || telemetry_valid_uuid(value->tank_id)) &&
        (!value->binding_id[0] || telemetry_valid_uuid(value->binding_id)) &&
        (!!value->tank_id[0] == !!value->binding_id[0]) && strlen(value->digest) == 64;
}

esp_err_t device_setup_load(const char *device, device_setup_config_t *out)
{
    if (!device || !out) { return ESP_ERR_INVALID_ARG; }
    nvs_handle_t handle;
    esp_err_t ret = nvs_open_from_partition("nvs", "bb_setup", NVS_READONLY, &handle);
    if (ret == ESP_ERR_NVS_NOT_FOUND) { return ret; }
    if (ret != ESP_OK) { return ret; }
    device_setup_config_t value = {0}; size_t size = sizeof(value);
    ret = nvs_get_blob(handle, "active", &value, &size); nvs_close(handle);
    if (ret != ESP_OK) { return ret; }
    if (size != sizeof(value) || !valid_record(&value) || value.crc != checksum(&value) ||
            strcmp(value.device_id, device)) { return ESP_ERR_INVALID_CRC; }
    *out = value; return ESP_OK;
}

esp_err_t device_setup_save(const device_setup_config_t *input)
{
    if (!input || !valid_record(input)) { return ESP_ERR_INVALID_ARG; }
    device_setup_config_t previous;
    esp_err_t ret = device_setup_load(input->device_id, &previous);
    if (ret != ESP_OK && ret != ESP_ERR_NVS_NOT_FOUND) { return ret; }
    if (ret == ESP_OK && (input->revision < previous.revision || strcmp(input->hatchery_id, previous.hatchery_id) ||
            (input->revision == previous.revision && (strcmp(input->digest, previous.digest) ||
                (previous.confirmed && !input->confirmed))))) { return ESP_ERR_INVALID_STATE; }
    device_setup_config_t value = *input; value.crc = checksum(&value);
    nvs_handle_t handle;
    ret = nvs_open_from_partition("nvs", "bb_setup", NVS_READWRITE, &handle);
    if (ret != ESP_OK) { return ret; }
    ret = nvs_set_blob(handle, "active", &value, sizeof(value));
    if (ret == ESP_OK) { ret = nvs_commit(handle); }
    nvs_close(handle);
    device_setup_config_t verified;
    if (ret == ESP_OK) { ret = device_setup_load(value.device_id, &verified); }
    if (ret == ESP_OK && memcmp(&value, &verified, sizeof(value))) { ret = ESP_ERR_INVALID_CRC; }
    return ret;
}
