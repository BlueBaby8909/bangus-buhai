#include "relay_driver.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "sdkconfig.h"

static const char *TAG = "RELAY_DRIVER";

#define RELAY_ON_LEVEL  0
#define RELAY_OFF_LEVEL 1

static bool s_relay_state = false;

void relay_driver_init(void)
{
    ESP_LOGI(TAG, "Initializing Relay on GPIO %d", CONFIG_BB_GPIO_RELAY);

    gpio_set_level(CONFIG_BB_GPIO_RELAY, RELAY_OFF_LEVEL);
    
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CONFIG_BB_GPIO_RELAY),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };

    gpio_config(&io_conf);
}

void relay_driver_set_state(bool turn_on)
{
    s_relay_state = turn_on;
    if (turn_on){
        gpio_set_level(CONFIG_BB_GPIO_RELAY, RELAY_ON_LEVEL);
        ESP_LOGI(TAG, "RELAY: ON");
    }else{
        gpio_set_level(CONFIG_BB_GPIO_RELAY, RELAY_OFF_LEVEL);
        ESP_LOGI(TAG, "RELAY: OFF");
    }
}

bool relay_driver_get_state(void)
{
    return s_relay_state;
}