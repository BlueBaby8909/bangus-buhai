#ifndef RELAY_DRIVER_H
#define RELAY_DRIVER_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize the relay GPIO pin
 */
void relay_driver_init(void);

/**
 * @brief Turn the relay on or off
 * 
 * @param turn_on true to turn on the heating element, false to turn it off
 */
void relay_driver_set_state(bool turn_on);

/**
 * @brief Get the current relay state
 * 
 * @return true if on, false if off
 */
bool relay_driver_get_state(void);

#ifdef __cplusplus
}
#endif

#endif // RELAY_DRIVER_H