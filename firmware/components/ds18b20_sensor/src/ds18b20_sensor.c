#include "ds18b20_sensor.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "onewire_bus.h"
#include "ds18b20.h"

static const char *TAG = "DS18B20_SENSOR";

static ds18b20_device_handle_t s_ds18b20_handle = NULL;

esp_err_t ds18b20_sensor_init(void)
{
    ESP_LOGI(TAG, "Initializing DS18B20 on GPIO %d", CONFIG_BB_GPIO_DS18B20);

    onewire_bus_handle_t bus = NULL;
    onewire_bus_config_t bus_config = {
        .bus_gpio_num = CONFIG_BB_GPIO_DS18B20,
    };
    onewire_bus_rmt_config_t rmt_config = {
        .max_rx_bytes = 10, 
    };

    esp_err_t ret = onewire_new_bus_rmt(&bus_config, &rmt_config, &bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create 1-Wire bus");
        return ret;
    }

    onewire_device_iter_handle_t iter = NULL;
    onewire_device_t next_onewire_device;
    bool found = false;

    ESP_ERROR_CHECK(onewire_new_device_iter(bus, &iter));

    while (onewire_device_iter_get_next(iter, &next_onewire_device) == ESP_OK) {
        if ((next_onewire_device.address & 0xFF) == 0x28) {
            found = true;
            break;
        }
    }

    onewire_del_device_iter(iter);

    if (!found) {
        ESP_LOGE(TAG, "No DS18B20 sensor found!");
        return ESP_ERR_NOT_FOUND;
    }

    ds18b20_config_t ds_cfg = {};
    
    ESP_ERROR_CHECK(ds18b20_new_device_from_enumeration(&next_onewire_device, &ds_cfg, &s_ds18b20_handle));
    ESP_ERROR_CHECK(ds18b20_set_resolution(s_ds18b20_handle, DS18B20_RESOLUTION_10B));

    ESP_LOGI(TAG, "DS18B20 initialized successfully");
    return ESP_OK;
}

esp_err_t ds18b20_sensor_read(float *out_temperature)
{
    if (s_ds18b20_handle == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t ret = ds18b20_trigger_temperature_conversion(s_ds18b20_handle);
    if (ret != ESP_OK) {
        return ret;
    }

    vTaskDelay(pdMS_TO_TICKS(200));

    ret = ds18b20_get_temperature(s_ds18b20_handle, out_temperature);
    return ret;
}