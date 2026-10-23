#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "sensor_service.h"

typedef enum { RELAY_MODE_AUTO, RELAY_MODE_MANUAL } relay_mode_t;

typedef struct {
    relay_mode_t mode;
    bool manual_on;
    bool auto_on;
    bool desired_on;
    bool safety_inhibited;
} relay_policy_t;

void relay_policy_init(relay_policy_t *policy);
bool relay_temperature_usable(const sensor_value_t *temperature, int64_t now_ms);
void relay_policy_step(relay_policy_t *policy, const sensor_value_t *temperature,
                       int64_t now_ms);
esp_err_t relay_policy_manual(relay_policy_t *policy, bool on,
                               const sensor_value_t *temperature, int64_t now_ms);
void relay_policy_auto(relay_policy_t *policy);
/* Cancel remembered ON requests after an output failure as well as sensor faults. */
void relay_policy_latch_off(relay_policy_t *policy);

typedef struct {
    relay_mode_t mode;
    bool known;
    bool on;
    bool safety_inhibited;
    esp_err_t error;
    esp_err_t last_request_error;
} relay_control_state_t;

/* Call once before other tasks use the API. Creates the only relay writer task. */
esp_err_t relay_control_init(void);
/* ESP_OK means queued, not applied; execution rechecks sensor quality.
 * Full queue returns ESP_ERR_TIMEOUT without replacing older commands.
 */
esp_err_t relay_control_request_manual(bool on);
esp_err_t relay_control_request_auto(void);
esp_err_t relay_control_get_state(relay_control_state_t *out);

typedef struct {
    uint32_t token;
    bool automatic, on;
    int64_t issued_us, expires_us, deadline_ms;
    char binding_id[37];
    bool (*binding_current)(const char *binding);
} relay_command_request_t;
typedef struct {
    uint32_t token;
    relay_control_state_t state;
    const char *result, *reason;
    int64_t completed_us, completed_uptime_ms;
} relay_command_completion_t;
/* Correlated requests are applied individually by the sole control task. */
esp_err_t relay_control_request_command(const relay_command_request_t *request);
bool relay_control_take_completion(relay_command_completion_t *out);
const char *relay_command_rejection(const relay_command_request_t *request,
                                    int64_t utc_us, int64_t uptime_ms);
