#include "relay_driver.h"
#include "driver/gpio.h"
#include "sdkconfig.h"
#include <stdint.h>

static relay_driver_state_t s_state = {.error = ESP_ERR_INVALID_STATE};

esp_err_t relay_driver_init(void)
{
    if (s_state.known) {
        return ESP_OK;
    }
    /* Preload OFF before enabling the active-low GPIO output. */
    esp_err_t ret = gpio_set_level(CONFIG_BB_GPIO_RELAY, 1);
    if (ret == ESP_OK) {
        gpio_config_t config = {
            .pin_bit_mask = UINT64_C(1) << CONFIG_BB_GPIO_RELAY,
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        ret = gpio_config(&config);
    }
    s_state.known = ret == ESP_OK;
    s_state.error = ret;
    if (ret == ESP_OK) {
        s_state.on = false;
    }
    return ret;
}

esp_err_t relay_driver_set_state(bool on)
{
    if (!s_state.known) {
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t ret = gpio_set_level(CONFIG_BB_GPIO_RELAY, on ? 0 : 1);
    s_state.error = ret;
    if (ret == ESP_OK) {
        s_state.on = on;
    } else {
        s_state.known = false;
    }
    return ret;
}

relay_driver_state_t relay_driver_get_state(void)
{
    return s_state;
}
