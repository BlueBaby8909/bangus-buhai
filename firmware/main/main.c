#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "app_events.h"

#include "relay_driver.h"
#include "ds18b20_sensor.h"
#include "turbidity_sensor.h"
#include "lcd_display.h"

static const char *TAG = "APP_MAIN";

// Define Event Bases here (declared in app_events.h)
ESP_EVENT_DEFINE_BASE(SENSOR_EVENTS);
ESP_EVENT_DEFINE_BASE(SYSTEM_EVENTS);

void app_main(void)
{
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Create default event loop
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    ESP_LOGI(TAG, "Bangus Buhai Firmware Started");
    ESP_LOGI(TAG, "Configured Tank ID: %d", CONFIG_BB_TANK_ID);

    // Initialize Actuators
    relay_driver_init();

    // Initialize Sensors
    ESP_LOGI(TAG, "Initializing Sensors...");
    if (ds18b20_sensor_init() != ESP_OK) {
        ESP_LOGW(TAG, "Temperature sensor not found. Continuing without it...");
    }
    ESP_ERROR_CHECK(turbidity_sensor_init());

    // Initialize LCD
    ESP_LOGI(TAG, "Initializing LCD...");
    if (lcd_display_init() == ESP_OK) {
        lcd_display_set_cursor(0, 0);
        lcd_display_write_string("BangusBuhai");
        lcd_display_set_cursor(0, 1);
        lcd_display_write_string("Initializing...");
    } else {
        ESP_LOGE(TAG, "LCD Initialization failed!");
    }

    // TODO: Connect WiFi

    ESP_LOGI(TAG, "Entering Main Loop...");
    while (1) {
        float temp = 0.0f;
        int voltage = 0;

        if (ds18b20_sensor_read(&temp) == ESP_OK) {
            ESP_LOGI(TAG, "Temperature: %.2f C", temp);
            
            // Format for LCD (e.g. "Temp: 24.5C")
            char lcd_buf[17];
            snprintf(lcd_buf, sizeof(lcd_buf), "Temp: %.1fC     ", temp); // Pad with spaces to clear old text
            lcd_display_set_cursor(0, 0);
            lcd_display_write_string(lcd_buf);
        } else {
            ESP_LOGW(TAG, "Failed to read temperature");
        }

        if (turbidity_sensor_read(&voltage) == ESP_OK) {
            float voltage_v = (float)voltage / 1000.0f;
            ESP_LOGI(TAG, "Turbidity Voltage: %.2f V", voltage_v);

            // Format for LCD (e.g. "Turb: 2.15V")
            char lcd_buf[17];
            snprintf(lcd_buf, sizeof(lcd_buf), "Turb: %.2fV     ", voltage_v);
            lcd_display_set_cursor(0, 1);
            lcd_display_write_string(lcd_buf);
        } else {
            ESP_LOGW(TAG, "Failed to read turbidity");
        }

        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
