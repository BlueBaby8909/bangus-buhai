#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>
#include "esp_err.h"

typedef struct {
    uint32_t magic, version, revision, confirmed;
    char device_id[16], hatchery_id[37], tank_id[37], binding_id[37], digest[65];
    uint32_t archived, crc;
} device_setup_config_t;

/* Strict canonical configuration, storage and crypto are also used by Unity. */
esp_err_t device_setup_parse(const char *json, size_t length, const char *device, device_setup_config_t *out);
esp_err_t device_setup_load(const char *device, device_setup_config_t *out);
esp_err_t device_setup_save(const device_setup_config_t *value);
esp_err_t device_setup_sha256(const void *data, size_t length, char hex[65]);
esp_err_t device_setup_sign(const char *key, const uint8_t *input, size_t length,
                            uint8_t *signature, size_t capacity, size_t *written);
esp_err_t device_setup_proof(const char *challenge, size_t length, const char *device,
                            const char *purpose, const device_setup_config_t *config, time_t now,
                            const char *key, char *out, size_t capacity);
/* Local operation never waits on HTTPS. Only the MQTT owner reads this snapshot. */
esp_err_t device_setup_start(const char *device);
bool device_setup_binding(char out[37]);
