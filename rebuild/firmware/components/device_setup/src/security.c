#include "device_setup.h"
#include <stdio.h>
#include <string.h>
#include "mbedtls/pk.h"
#include "psa/crypto.h"
#include "mbedtls/base64.h"
#include "telemetry.h"
#include "cJSON.h"

esp_err_t device_setup_sha256(const void *data, size_t length, char hex[65])
{
    uint8_t hash[32]; size_t written = 0;
    if (psa_crypto_init() != PSA_SUCCESS || psa_hash_compute(PSA_ALG_SHA_256, data, length,
            hash, sizeof(hash), &written) != PSA_SUCCESS || written != 32) { return ESP_FAIL; }
    for (unsigned i = 0; i < 32; ++i) { snprintf(hex + 2*i, 3, "%02x", hash[i]); }
    return ESP_OK;
}

static const char *field(const cJSON *root, const char *name)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, name);
    return cJSON_IsString(item) ? item->valuestring : NULL;
}

static bool base64url(const char *text, uint8_t *out, size_t capacity, size_t *written)
{
    size_t length = strlen(text);
    if (!length || length > 1800 || length % 4 == 1) { return false; }
    char standard[1805];
    for (size_t i = 0; i < length; ++i) {
        char c = text[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_')) { return false; }
        standard[i] = c == '-' ? '+' : c == '_' ? '/' : c;
    }
    size_t padded = length;
    while (padded % 4) { standard[padded++] = '='; }
    return mbedtls_base64_decode(out, capacity, written, (const uint8_t *)standard, padded) == 0;
}

static time_t expiry(const char *value)
{
    int y, m, d, hh, mm, ss, n = 0;
    if (!value || sscanf(value, "%4d-%2d-%2dT%2d:%2d:%2d%n", &y, &m, &d, &hh, &mm, &ss, &n) != 6 ||
            n != 19 || y < 2020 || y > 2100 || m < 1 || m > 12 || hh < 0 || hh > 23 ||
            mm < 0 || mm > 59 || ss < 0 || ss > 59) { return 0; }
    const char *tail = value + n;
    if (*tail == '.') {
        unsigned digits = 0; ++tail;
        while (*tail >= '0' && *tail <= '9') { ++digits; ++tail; }
        if (!digits || digits > 6) { return 0; }
    }
    if (strcmp(tail, "+00:00") && strcmp(tail, "Z")) { return 0; }
    const int months[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    bool leap = y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
    if (d < 1 || d > months[m-1] + (m == 2 && leap)) { return 0; }
    int64_t days = d-1;
    for (int year = 1970; year < y; ++year) { days += 365 + (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)); }
    for (int month = 1; month < m; ++month) { days += months[month-1] + (month == 2 && leap); }
    return days*86400 + hh*3600 + mm*60 + ss;
}

esp_err_t device_setup_proof(const char *challenge, size_t length, const char *device,
                            const char *purpose, const device_setup_config_t *config, time_t now,
                            const char *key, char *out, size_t capacity)
{
    if (!device || !purpose || !key || !out || (!strcmp(purpose, "confirm") && !config)) { return ESP_ERR_INVALID_ARG; }
    cJSON *root = telemetry_parse_json(challenge, length, true);
    const cJSON *payload = root ? cJSON_GetObjectItemCaseSensitive(root, "payload") : NULL;
    const char *identity = root ? field(root, "challenge_id") : NULL;
    const char *encoded = root ? field(root, "signing_input") : NULL;
    const char *algorithm = root ? field(root, "algorithm") : NULL;
    const char *id = payload ? field(payload, "device_id") : NULL;
    const char *operation = payload ? field(payload, "purpose") : NULL;
    const char *challenge_id = payload ? field(payload, "challenge_id") : NULL;
    const char *nonce = payload ? field(payload, "nonce") : NULL;
    time_t deadline = payload ? expiry(field(payload, "expires_at")) : 0;
    uint8_t input[1400], signature[512]; size_t input_length = 0, signature_length = 0;
    bool valid = root && cJSON_GetArraySize(root) == 4 && cJSON_IsObject(payload) && cJSON_GetArraySize(payload) == 8 &&
        identity && telemetry_valid_uuid(identity) && algorithm && !strcmp(algorithm, "RSA-PSS-SHA256") &&
        id && !strcmp(id, device) && operation && !strcmp(operation, purpose) &&
        challenge_id && !strcmp(challenge_id, identity) && nonce && strlen(nonce) == 43 &&
        now > 0 && deadline > now && deadline <= now + 125 && encoded &&
        base64url(encoded, input, sizeof(input)-1, &input_length) && input_length > 12 &&
        !memcmp(input, "BB-SETUP-V1\n", 12);
    cJSON *decoded = valid ? telemetry_parse_json((const char *)input + 12, input_length-12, true) : NULL;
    valid = valid && decoded && cJSON_Compare(payload, decoded, true);
    const cJSON *revision = payload ? cJSON_GetObjectItemCaseSensitive(payload, "configuration_revision") : NULL;
    const cJSON *digest = payload ? cJSON_GetObjectItemCaseSensitive(payload, "configuration_digest") : NULL;
    const cJSON *claim = payload ? cJSON_GetObjectItemCaseSensitive(payload, "claim_id") : NULL;
    valid = valid && (cJSON_IsNull(claim) || (cJSON_IsString(claim) && telemetry_valid_uuid(claim->valuestring)));
    if (!strcmp(purpose, "confirm")) {
        valid = valid && cJSON_IsNumber(revision) && revision->valuedouble == config->revision &&
            cJSON_IsString(digest) && !strcmp(digest->valuestring, config->digest);
    } else if (!strcmp(purpose, "sync")) { valid = valid && cJSON_IsNull(revision) && cJSON_IsNull(digest); }
    else { valid = false; }
    esp_err_t result = ESP_ERR_INVALID_RESPONSE;
    if (valid && device_setup_sign(key, input, input_length, signature, sizeof(signature), &signature_length) == ESP_OK) {
        char encoded_signature[690]; size_t count;
        if (mbedtls_base64_encode((uint8_t *)encoded_signature, sizeof(encoded_signature), &count,
                signature, signature_length) == 0) {
            while (count && encoded_signature[count-1] == '=') { --count; }
            encoded_signature[count] = 0;
            for (size_t i = 0; i < count; ++i) {
                if (encoded_signature[i] == '+') { encoded_signature[i] = '-'; }
                if (encoded_signature[i] == '/') { encoded_signature[i] = '_'; }
            }
            int size = snprintf(out, capacity, "{\"challenge_id\":\"%s\",\"signature\":\"%s\"}", identity, encoded_signature);
            result = size > 0 && size < capacity ? ESP_OK : ESP_ERR_INVALID_SIZE;
        }
    }
    cJSON_Delete(decoded); cJSON_Delete(root); return result;
}

esp_err_t device_setup_sign(const char *key, const uint8_t *input, size_t length,
                            uint8_t *signature, size_t capacity, size_t *written)
{
    if (!key || !input || !length || !signature || !written) { return ESP_ERR_INVALID_ARG; }
    esp_err_t result = ESP_FAIL;
    mbedtls_pk_context pk; mbedtls_pk_init(&pk);
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    mbedtls_svc_key_id_t id = 0;
    uint8_t hash[32]; size_t hash_length;
    if (psa_crypto_init() != PSA_SUCCESS || mbedtls_pk_parse_key(&pk,
            (const uint8_t *)key, strlen(key) + 1, NULL, 0) != 0 ||
            mbedtls_pk_get_psa_attributes(&pk, PSA_KEY_USAGE_SIGN_HASH, &attributes) != 0) { goto done; }
    if (!PSA_KEY_TYPE_IS_RSA(psa_get_key_type(&attributes)) || psa_get_key_bits(&attributes) < 2048) { goto done; }
    /* PSA's standard PSS algorithm fixes salt length to the SHA-256 length. */
    psa_set_key_algorithm(&attributes, PSA_ALG_RSA_PSS(PSA_ALG_SHA_256));
    if (mbedtls_pk_import_into_psa(&pk, &attributes, &id) != 0 ||
            psa_hash_compute(PSA_ALG_SHA_256, input, length, hash, sizeof(hash), &hash_length) != PSA_SUCCESS ||
            psa_sign_hash(id, PSA_ALG_RSA_PSS(PSA_ALG_SHA_256), hash, hash_length,
                signature, capacity, written) != PSA_SUCCESS) { goto done; }
    result = ESP_OK;
done:
    if (id) { psa_destroy_key(id); }
    psa_reset_key_attributes(&attributes); mbedtls_pk_free(&pk);
    return result;
}
