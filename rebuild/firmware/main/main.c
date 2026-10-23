#include "esp_log.h"
#include "sensor_service.h"
#include "relay_control.h"
#include "lcd_display.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "bootloader_random.h"
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "MAIN";

static void log_value(const char *name, const sensor_value_t *reading)
{
    if (reading->has_value) {
        ESP_LOGI(TAG, "%s=%.2f %s source=%s state=%s age=%lld ms", name,
                 (double)reading->value, reading->unit, reading->source,
                 sensor_validity_name(reading->validity),
                 (long long)reading->sample_age_ms);
    } else {
        ESP_LOGW(TAG, "%s unavailable state=%s last_valid_age=%lld ms error=%s",
                 name, sensor_validity_name(reading->validity),
                 (long long)reading->last_valid_age_ms,
                 esp_err_to_name(reading->error));
    }
}

static void sensor_task(void *argument)
{
    (void)argument;
    TickType_t last_wake = xTaskGetTickCount();
    for (;;) {
        sensor_reading_t reading;
        esp_err_t ret = sensor_service_read(&reading);
        if (ret == ESP_OK) {
            log_value("temperature", &reading.temperature);
            log_value("turbidity", &reading.turbidity);
            log_value("pH", &reading.ph);
        } else {
            ESP_LOGE(TAG, "Snapshot failed: %s", esp_err_to_name(ret));
        }
        xTaskDelayUntil(&last_wake, pdMS_TO_TICKS(2000));
    }
}

static void display_task(void *argument)
{
    (void)argument;
    TickType_t wake = xTaskGetTickCount();
    int64_t retry_at_ms = 0;
    for (;;) {
        int64_t now_ms = esp_timer_get_time() / 1000;
        if (now_ms >= retry_at_ms) {
            esp_err_t ret = lcd_display_init();
            if (ret == ESP_OK) {
                sensor_reading_t reading;
                relay_control_state_t relay;
                const sensor_reading_t *sensors = NULL;
                const relay_control_state_t *control = NULL;
                if (sensor_service_try_get_latest(&reading, 20) == ESP_OK) {
                    sensors = &reading;
                }
                if (relay_control_get_state(&relay) == ESP_OK) {
                    control = &relay;
                }
                lcd_frame_t frame;
                ret = lcd_display_format(sensors, control,
                    esp_timer_get_time() / 1000, &frame);
                if (ret == ESP_OK) { ret = lcd_display_write_frame(&frame); }
            }
            if (ret != ESP_OK) {
                ESP_LOGW(TAG, "LCD unavailable: %s", esp_err_to_name(ret));
                retry_at_ms = esp_timer_get_time() / 1000 + 5000;
            }
        }
        xTaskDelayUntil(&wake, pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Bangus Buhai firmware starting");
    /* Temporary entropy source must be off before ADC/radio drivers start. */
    uint8_t random[16];
    char boot_id[37];
    bootloader_random_enable();
    esp_fill_random(random, sizeof(random));
    bootloader_random_disable();
    random[6] = (random[6] & 15) | 0x40;
    random[8] = (random[8] & 63) | 0x80;
    snprintf(boot_id, sizeof(boot_id), "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
             random[0], random[1], random[2], random[3], random[4], random[5], random[6], random[7],
             random[8], random[9], random[10], random[11], random[12], random[13], random[14], random[15]);
    esp_err_t ret = sensor_service_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Sensor service initialization failed: %s", esp_err_to_name(ret));
        return;
    }
    if (xTaskCreate(sensor_task, "sensor", 4096, NULL, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "Could not create sensing task");
    }
    ret = relay_control_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Relay control startup failed: %s", esp_err_to_name(ret));
    }
    ret = xTaskCreate(display_task, "display", 4096, NULL, 3, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Display startup failed: %s", esp_err_to_name(ret));
    }
    ret = wifi_manager_init();
    bool wifi_initialized = ret == ESP_OK;
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Wi-Fi initialization failed: %s", esp_err_to_name(ret));
    }
    ret = mqtt_manager_start(boot_id, wifi_initialized);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "MQTT/telemetry startup failed: %s", esp_err_to_name(ret));
    }
    if (wifi_initialized) {
        ret = wifi_manager_start();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Wi-Fi startup failed: %s", esp_err_to_name(ret));
        }
    }
}
