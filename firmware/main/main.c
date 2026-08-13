/**
 * @file main.c
 * @brief Bangus Buhai firmware — application entry point and task orchestration.
 *
 * ARCHITECTURE OVERVIEW
 * =====================
 *
 * Four FreeRTOS tasks run concurrently after boot:
 *
 *   sensor_task     (Priority 5, Core 1)
 *     Reads DS18B20 and turbidity sensor every 2 seconds.
 *     Applies EMA filtering. Posts SENSOR_EVENT_DATA_READY to the event loop.
 *     Registered with the Task Watchdog Timer (TWDT).
 *
 *   control_task    (Priority 4, Core 1)
 *     Reads the latest sensor reading every 5 seconds.
 *     Controls the relay with hysteresis (ON ≥ 32.5°C, OFF ≤ 31.0°C).
 *     If the temperature sensor is stale (>60 s), forces relay OFF (safe state).
 *     Registered with TWDT.
 *
 *   telemetry_task  (Priority 3, Core 0)
 *     Waits for MQTT to be connected, then publishes readings every 5 minutes.
 *     Uses telemetry_service_send_data() which handles offline buffering.
 *     Registered with TWDT.
 *
 *   display_task    (Priority 2, Core 1)
 *     Updates the 16×2 I2C LCD every second.
 *     Shows temperature, turbidity, Wi-Fi status, and MQTT status.
 *     NOT registered with TWDT (non-critical).
 *
 * Boot sequence:
 *   1. NVS flash init
 *   2. TCP/IP stack + default event loop
 *   3. Hardware peripheral init (relay, DS18B20, turbidity, LCD)
 *   4. Sensor service init (mutex, EMA state)
 *   5. Wi-Fi manager init (connects or enters SoftAP provisioning)
 *   6. [Task creation — starts running immediately]
 *   7. Telemetry service init waits in telemetry_task until Wi-Fi is connected
 *
 * WHY NO BLOCKING WAIT IN app_main():
 *   Previous firmware called wifi_manager_init() and blocked with
 *   portMAX_DELAY waiting for a connection. This is problematic because:
 *   - FreeRTOS tasks haven't started yet, so the watchdog idle task can't run.
 *   - If Wi-Fi never connects, the device hangs forever with no recovery.
 *   The new design starts tasks first, then uses the event loop for
 *   coordination. Tasks that need Wi-Fi wait on SYSTEM_EVENT_WIFI_CONNECTED.
 *
 * RELAY HYSTERESIS:
 *   Simple threshold control (on > 32°C, off ≤ 32°C) causes relay chattering
 *   when temperature hovers at the threshold — the relay clicks on and off
 *   every 5 seconds, which degrades relay lifetime and connected equipment.
 *   Hysteresis adds a dead-band: relay turns ON only when temp rises above
 *   32.5°C and turns OFF only when it drops below 31.0°C. This prevents
 *   rapid cycling.
 *
 * TASK CORE AFFINITY:
 *   Core 0 is shared with the Wi-Fi/lwIP/MQTT stack (which Espressif pins to
 *   Core 0 by default). Pinning sensor and control tasks to Core 1 prevents
 *   Wi-Fi interrupt handling from delaying time-sensitive sensor reads.
 */

#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_log.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_task_wdt.h"
#include "nvs_flash.h"

#include "app_events.h"
#include "wifi_manager.h"
#include "sensor_service.h"
#include "telemetry_service.h"
#include "relay_driver.h"
#include "ds18b20_sensor.h"
#include "turbidity_sensor.h"
#include "lcd_display.h"

/* ── Firmware logging tag ──────────────────────────────────────────────────── */
static const char *TAG = "APP_MAIN";

/* ── Define event bases (matching ESP_EVENT_DECLARE_BASE in app_events.h) ──── */
ESP_EVENT_DEFINE_BASE(SENSOR_EVENTS);
ESP_EVENT_DEFINE_BASE(SYSTEM_EVENTS);

/* ── Task configuration ────────────────────────────────────────────────────── */
#define SENSOR_TASK_STACK       5120
#define CONTROL_TASK_STACK      3072
#define TELEMETRY_TASK_STACK    6144    /* larger: JSON, MQTT, cJSON allocation */
#define DISPLAY_TASK_STACK      3072

#define SENSOR_TASK_PRIORITY    5
#define CONTROL_TASK_PRIORITY   4
#define TELEMETRY_TASK_PRIORITY 3
#define DISPLAY_TASK_PRIORITY   2

#define SENSOR_INTERVAL_MS      2000
#define CONTROL_INTERVAL_MS     5000
#define TELEMETRY_INTERVAL_MS   (5UL * 1000UL)          /* 5 seconds */
#define DISPLAY_INTERVAL_MS     1000

/* ── Relay hysteresis thresholds ───────────────────────────────────────────── */
#define RELAY_ON_THRESHOLD      32.5f   /* relay turns ON  above this temp °C */
#define RELAY_OFF_THRESHOLD     31.0f   /* relay turns OFF below this temp °C */

/* ── Wi-Fi / MQTT connection tracking (set by event loop handlers) ─────────── */
static volatile bool s_wifi_up = false;
static volatile bool s_telemetry_inited = false;

/* ── LCD status line helpers ───────────────────────────────────────────────── */
static void lcd_show_status(const char *line1, const char *line2)
{
    char buf[17];

    lcd_display_set_cursor(0, 0);
    snprintf(buf, sizeof(buf), "%-16s", line1);
    lcd_display_write_string(buf);

    lcd_display_set_cursor(0, 1);
    snprintf(buf, sizeof(buf), "%-16s", line2);
    lcd_display_write_string(buf);
}

/* ── System event handler ──────────────────────────────────────────────────── */
static void system_event_handler(void *arg, esp_event_base_t event_base,
                                 int32_t event_id, void *event_data)
{
    if (event_base == SYSTEM_EVENTS) {
        switch ((system_event_id_t)event_id) {
            case SYSTEM_EVENT_WIFI_CONNECTED:
                s_wifi_up = true;
                ESP_LOGI(TAG, "System: Wi-Fi up");
                break;
            case SYSTEM_EVENT_WIFI_DISCONNECTED:
                s_wifi_up = false;
                ESP_LOGW(TAG, "System: Wi-Fi down");
                break;
            default:
                break;
        }
    }
}

/* ── Tasks ─────────────────────────────────────────────────────────────────── */

/**
 * Sensor task — reads and filters sensor data, posts events.
 * Pinned to Core 1 to avoid interference from Wi-Fi interrupts on Core 0.
 */
static void sensor_task(void *pvParameters)
{
    ESP_LOGI(TAG, "[sensor_task] started on core %d", xPortGetCoreID());
    esp_task_wdt_add(NULL);   /* register this task with the watchdog */

    while (1) {
        sensor_reading_t reading;
        esp_err_t ret = sensor_service_read(&reading);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "[sensor_task] sensor_service_read error: %s",
                     esp_err_to_name(ret));
        }

        esp_task_wdt_reset();  /* feed the watchdog */
        vTaskDelay(pdMS_TO_TICKS(SENSOR_INTERVAL_MS));
    }
}

/**
 * Control task — relay management with hysteresis and safe-state fallback.
 * Pinned to Core 1 alongside the sensor task.
 */
static void control_task(void *pvParameters)
{
    ESP_LOGI(TAG, "[control_task] started on core %d", xPortGetCoreID());
    esp_task_wdt_add(NULL);

    bool relay_state = false;   /* track to implement hysteresis */

    while (1) {
        /* If temperature sensor is stale, go to safe state (relay OFF) */
        if (sensor_service_is_temperature_stale()) {
            if (relay_state) {
                relay_driver_set_state(false);
                relay_state = false;
                ESP_LOGW(TAG, "[control_task] Temp sensor STALE — relay forced OFF (safe state)");
            }
            esp_task_wdt_reset();
            vTaskDelay(pdMS_TO_TICKS(CONTROL_INTERVAL_MS));
            continue;
        }

        sensor_reading_t reading;
        if (sensor_service_get_latest(&reading) == ESP_OK) {
            float temp = reading.temperature;

            /* Hysteresis: only change state at the appropriate threshold */
            if (!relay_state && temp >= RELAY_ON_THRESHOLD) {
                relay_driver_set_state(true);
                relay_state = true;
                ESP_LOGI(TAG, "[control_task] Relay ON  (%.1f°C ≥ %.1f°C)",
                         temp, RELAY_ON_THRESHOLD);
            } else if (relay_state && temp <= RELAY_OFF_THRESHOLD) {
                relay_driver_set_state(false);
                relay_state = false;
                ESP_LOGI(TAG, "[control_task] Relay OFF (%.1f°C ≤ %.1f°C)",
                         temp, RELAY_OFF_THRESHOLD);
            }
        }

        esp_task_wdt_reset();
        vTaskDelay(pdMS_TO_TICKS(CONTROL_INTERVAL_MS));
    }
}

/**
 * Telemetry task — waits for Wi-Fi + initialises MQTT, then publishes data.
 * Pinned to Core 0 alongside the Wi-Fi/MQTT stack.
 */
static void telemetry_task(void *pvParameters)
{
    ESP_LOGI(TAG, "[telemetry_task] started on core %d", xPortGetCoreID());
    esp_task_wdt_add(NULL);

    /* Wait until Wi-Fi is connected before initialising the MQTT client.
     * We poll s_wifi_up (set by the event handler) with a short delay.
     * Using xEventGroupWaitBits() would be slightly cleaner but this
     * approach keeps the event group creation out of app_main scope. */
    ESP_LOGI(TAG, "[telemetry_task] waiting for Wi-Fi...");
    while (!s_wifi_up) {
        esp_task_wdt_reset();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    ESP_LOGI(TAG, "[telemetry_task] Wi-Fi up — initialising MQTT");
    esp_err_t ret = telemetry_service_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "[telemetry_task] telemetry_service_init failed: %s",
                 esp_err_to_name(ret));
        /* Keep task alive so watchdog is fed; MQTT will auto-reconnect */
    }
    s_telemetry_inited = true;

    while (1) {
        sensor_reading_t reading;
        if (sensor_service_get_latest(&reading) == ESP_OK) {
            telemetry_service_send_data(
                reading.temperature,
                reading.turbidity,
                reading.ph,
                reading.ph_source,
                relay_driver_get_state()
            );
        } else {
            ESP_LOGD(TAG, "[telemetry_task] No sensor reading yet — skipping");
        }

        /* Sleep in 5-second chunks to keep the 30-second watchdog happy */
        const uint32_t chunk_ms = 5000;
        const uint32_t chunks = TELEMETRY_INTERVAL_MS / chunk_ms;
        for (uint32_t i = 0; i < chunks; i++) {
            esp_task_wdt_reset();
            vTaskDelay(pdMS_TO_TICKS(chunk_ms));
        }
    }
}

/**
 * Display task — updates the 16×2 LCD every second.
 * Shows readings and connection status so a field technician can diagnose
 * problems without a serial monitor.
 */
static void display_task(void *pvParameters)
{
    ESP_LOGI(TAG, "[display_task] started on core %d", xPortGetCoreID());

    char line1[17];
    char line2[17];

    while (1) {
        sensor_reading_t reading;
        bool has_reading = (sensor_service_get_latest(&reading) == ESP_OK);

        if (!s_wifi_up) {
            /* Wi-Fi not connected yet */
            if (!s_telemetry_inited) {
                lcd_show_status("Connecting WiFi ", "Please wait...  ");
            } else {
                lcd_show_status("WiFi Offline    ", "Reconnecting... ");
            }
        } else if (has_reading) {
            /* Normal operation — show sensor readings */
            snprintf(line1, sizeof(line1), "T:%5.1fC       ",
                     reading.temperature);
            snprintf(line2, sizeof(line2), "Tb:%6.1f NTU  ",
                     reading.turbidity);
            lcd_show_status(line1, line2);
        } else {
            lcd_show_status("WiFi: OK        ", "Reading sensors ");
        }

        vTaskDelay(pdMS_TO_TICKS(DISPLAY_INTERVAL_MS));
    }
}

/* ── Application entry point ───────────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "=========================================");
    ESP_LOGI(TAG, "  Bangus Buhai Firmware v1.0.0");
    ESP_LOGI(TAG, "  Tank ID: %d", CONFIG_BB_TANK_ID);
    ESP_LOGI(TAG, "=========================================");

    /* ── 1. NVS flash ────────────────────────────────────────────────────── */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_LOGI(TAG, "NVS initialised");

    /* ── 2. TCP/IP stack + default event loop ────────────────────────────── */
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    /* Register system event handler so s_wifi_up stays current */
    ESP_ERROR_CHECK(esp_event_handler_register(
        SYSTEM_EVENTS, ESP_EVENT_ANY_ID, system_event_handler, NULL));

    /* ── 3. Task Watchdog Timer ───────────────────────────────────────────── */
    esp_task_wdt_config_t twdt_config = {
        .timeout_ms     = 30000,   /* 30 second timeout */
        .idle_core_mask = (1 << 0) | (1 << 1),  /* watch both cores */
        .trigger_panic  = true,    /* hard reset on watchdog trip */
    };
    ESP_ERROR_CHECK(esp_task_wdt_reconfigure(&twdt_config));
    ESP_LOGI(TAG, "Task Watchdog Timer configured (30 s)");

    /* ── 4. Hardware peripheral initialisation ───────────────────────────── */
    relay_driver_init();
    ESP_LOGI(TAG, "Relay driver ready (GPIO %d)", CONFIG_BB_GPIO_RELAY);

    ret = ds18b20_sensor_init();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "DS18B20 not found — temperature readings unavailable");
    }

    ESP_ERROR_CHECK(turbidity_sensor_init());

    if (lcd_display_init() == ESP_OK) {
        lcd_show_status("BangusBuhai v1.0", "Booting...      ");
    } else {
        ESP_LOGE(TAG, "LCD init failed — continuing without display");
    }

    /* ── 5. Sensor service ───────────────────────────────────────────────── */
    ESP_ERROR_CHECK(sensor_service_init());

    /* ── 6. Wi-Fi manager ────────────────────────────────────────────────── */
    /* This either:
     *   a) connects using NVS-stored credentials, or
     *   b) enters SoftAP provisioning mode.
     * Does NOT block — returns immediately after starting the process. */
    ESP_ERROR_CHECK(wifi_manager_init());

    /* ── 7. Start FreeRTOS tasks ─────────────────────────────────────────── */
    /* sensor_task and control_task → Core 1 (away from Wi-Fi stack on Core 0)
     * telemetry_task and display_task → Core 0 (can share with Wi-Fi) */

    BaseType_t task_ret;

    task_ret = xTaskCreatePinnedToCore(
        sensor_task, "sensor", SENSOR_TASK_STACK, NULL,
        SENSOR_TASK_PRIORITY, NULL, 1 /* Core 1 */);
    configASSERT(task_ret == pdPASS);

    task_ret = xTaskCreatePinnedToCore(
        control_task, "control", CONTROL_TASK_STACK, NULL,
        CONTROL_TASK_PRIORITY, NULL, 1 /* Core 1 */);
    configASSERT(task_ret == pdPASS);

    task_ret = xTaskCreatePinnedToCore(
        telemetry_task, "telemetry", TELEMETRY_TASK_STACK, NULL,
        TELEMETRY_TASK_PRIORITY, NULL, 0 /* Core 0 */);
    configASSERT(task_ret == pdPASS);

    task_ret = xTaskCreatePinnedToCore(
        display_task, "display", DISPLAY_TASK_STACK, NULL,
        DISPLAY_TASK_PRIORITY, NULL, 0 /* Core 0 */);
    configASSERT(task_ret == pdPASS);

    ESP_LOGI(TAG, "All tasks started. app_main returning to idle.");
    /* app_main returns; the FreeRTOS scheduler takes over.
     * The idle task on each core feeds the watchdog for tasks that don't
     * register themselves. Our critical tasks (sensor, control, telemetry)
     * are all registered with TWDT and feed it explicitly. */
}
