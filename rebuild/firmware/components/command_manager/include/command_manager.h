#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#define COMMAND_RESULT_MAX 768U
#define COMMAND_CAPACITY 8U
typedef struct { size_t length; char payload[COMMAND_RESULT_MAX]; } command_result_wire_t;
/* All storage/parser operations belong to the MQTT owner. Callback only checks
 * the thread-safe setup snapshot, and also runs in the relay owner task. */
esp_err_t command_manager_init(const char *device, const char *boot,
                              bool (*binding_current)(const char *binding));
void command_manager_close(void);
esp_err_t command_manager_receive(const char *payload, size_t length, const char *binding,
                                  int64_t utc_us, int64_t uptime_ms);
void command_manager_poll(int64_t utc_us, int64_t uptime_ms);
esp_err_t command_manager_peek(const command_result_wire_t **out);
esp_err_t command_manager_ack(const char *payload, size_t length);
/* Pure canonical parser; exposed for regression tests. */
bool command_timestamp(const char *text, int64_t *microseconds);
