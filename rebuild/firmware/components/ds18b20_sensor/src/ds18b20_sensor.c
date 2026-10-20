#include "ds18b20_sensor.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include <stdbool.h>

#include "onewire_bus.h"
#include "ds18b20.h"

static const char *TAG = "DS18B20_SENSOR";

static ds18b20_device_handle_t s_ds18b20_handle = NULL;

esp_err_t ds18b20_sensor_init(void)
{
    if (s_ds18b20_handle != NULL) {
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing DS18B20 on GPIO %d", CONFIG_BB_GPIO_DS18B20);

    onewire_bus_handle_t bus = NULL;
    onewire_device_iter_handle_t iter = NULL;
    ds18b20_device_handle_t device = NULL;
    onewire_device_t next_onewire_device;
    ds18b20_config_t ds_cfg = {};
    bool found = false;
    onewire_bus_config_t bus_config = {
        .bus_gpio_num = CONFIG_BB_GPIO_DS18B20,
    };
    onewire_bus_rmt_config_t rmt_config = {
        .max_rx_bytes = 10,
    };

    esp_err_t ret = onewire_new_bus_rmt(&bus_config, &rmt_config, &bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create 1-Wire bus: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = onewire_new_device_iter(bus, &iter);
    if (ret != ESP_OK) {
        goto cleanup;
    }

    while ((ret = onewire_device_iter_get_next(iter, &next_onewire_device)) == ESP_OK) {
        if ((next_onewire_device.address & 0xFF) == 0x28) {
            found = true;
            break;
        }
    }

    if (!found) {
        if (ret == ESP_ERR_NOT_FOUND) {
            ESP_LOGW(TAG, "No DS18B20 sensor found");
        }
        goto cleanup;
    }

    ret = onewire_del_device_iter(iter);
    if (ret != ESP_OK) {
        goto cleanup;
    }
    iter = NULL;

    ret = ds18b20_new_device_from_enumeration(&next_onewire_device, &ds_cfg, &device);
    if (ret != ESP_OK) {
        goto cleanup;
    }
    ret = ds18b20_set_resolution(device, DS18B20_RESOLUTION_10B);
    if (ret != ESP_OK) {
        goto cleanup;
    }

    s_ds18b20_handle = device;
    ESP_LOGI(TAG, "DS18B20 initialized successfully");
    return ESP_OK;

cleanup:
    ESP_LOGE(TAG, "DS18B20 initialization failed: %s", esp_err_to_name(ret));
    if (iter != NULL) {
        esp_err_t cleanup_ret = onewire_del_device_iter(iter);
        if (cleanup_ret != ESP_OK) {
            ESP_LOGW(TAG, "Failed to release device iterator: %s", esp_err_to_name(cleanup_ret));
        }
    }
    if (device != NULL) {
        esp_err_t cleanup_ret = ds18b20_del_device(device);
        if (cleanup_ret != ESP_OK) {
            ESP_LOGW(TAG, "Failed to release DS18B20 device: %s", esp_err_to_name(cleanup_ret));
        }
    }
    if (bus != NULL) {
        esp_err_t cleanup_ret = onewire_bus_del(bus);
        if (cleanup_ret != ESP_OK) {
            ESP_LOGW(TAG, "Failed to release 1-Wire bus: %s", esp_err_to_name(cleanup_ret));
        }
    }
    return ret;
}

esp_err_t ds18b20_sensor_read(float *out_temperature)
{
    if (out_temperature == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    if (s_ds18b20_handle == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t ret = ds18b20_trigger_temperature_conversion(s_ds18b20_handle);
    if (ret != ESP_OK) {
        return ret;
    }

    ret = ds18b20_get_temperature(s_ds18b20_handle, out_temperature);
    return ret;
}
