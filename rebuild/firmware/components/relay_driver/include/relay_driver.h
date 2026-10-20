#pragma once

#include <stdbool.h>
#include "esp_err.h"

typedef struct {
    bool known;
    bool on;
    esp_err_t error;
} relay_driver_state_t;

/* Only the relay control task calls these functions. First successful init
 * establishes OFF; repeated init preserves a known state.
 * State is a successful output command, not contact feedback.
 */
esp_err_t relay_driver_init(void);
esp_err_t relay_driver_set_state(bool on);
relay_driver_state_t relay_driver_get_state(void);
