#include "relay_control.h"
#include "relay_driver.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include <math.h>
#include <string.h>

void relay_policy_init(relay_policy_t *policy)
{
    *policy = (relay_policy_t) {.mode = RELAY_MODE_AUTO, .safety_inhibited = true};
}

bool relay_temperature_usable(const sensor_value_t *temperature, int64_t now_ms)
{
    return temperature != NULL && temperature->has_value &&
        temperature->validity == SENSOR_VALID && temperature->source != NULL &&
        strcmp(temperature->source, "sensor") == 0 && temperature->unit != NULL &&
        strcmp(temperature->unit, "degC") == 0 && temperature->error == ESP_OK &&
        isfinite(temperature->value) && temperature->value >= -55.0f &&
        temperature->value <= 125.0f && temperature->sample_uptime_ms >= 0 &&
        now_ms >= temperature->sample_uptime_ms &&
        now_ms - temperature->sample_uptime_ms < INT64_C(60000);
}

void relay_policy_latch_off(relay_policy_t *policy)
{
    policy->manual_on = false;
    policy->auto_on = false;
    policy->desired_on = false;
}

void relay_policy_step(relay_policy_t *policy, const sensor_value_t *temperature,
                       int64_t now_ms)
{
    policy->safety_inhibited = !relay_temperature_usable(temperature, now_ms);
    if (policy->safety_inhibited) {
        relay_policy_latch_off(policy);
        return;
    }
    if (policy->mode == RELAY_MODE_MANUAL) {
        policy->desired_on = policy->manual_on;
        return;
    }
    if (temperature->value >= 32.5f) {
        policy->auto_on = true;
    } else if (temperature->value <= 31.0f) {
        policy->auto_on = false;
    }
    policy->desired_on = policy->auto_on;
}

esp_err_t relay_policy_manual(relay_policy_t *policy, bool on,
                               const sensor_value_t *temperature, int64_t now_ms)
{
    if (on && !relay_temperature_usable(temperature, now_ms)) {
        relay_policy_step(policy, temperature, now_ms);
        return ESP_ERR_INVALID_STATE;
    }
    policy->mode = RELAY_MODE_MANUAL;
    policy->manual_on = on;
    relay_policy_step(policy, temperature, now_ms);
    return ESP_OK;
}

void relay_policy_auto(relay_policy_t *policy)
{
    /* Switching from a healthy manual mode preserves output in the dead band. */
    policy->auto_on = policy->desired_on;
    policy->mode = RELAY_MODE_AUTO;
}

typedef enum { REQUEST_AUTO, REQUEST_MANUAL_OFF, REQUEST_MANUAL_ON } request_t;
static QueueHandle_t s_requests;
static SemaphoreHandle_t s_state_mutex;
static bool s_started;
static relay_control_state_t s_state;
static const char *TAG = "RELAY_CONTROL";

static int64_t now_ms(void) { return esp_timer_get_time() / 1000; }

static void control_task(void *argument)
{
    (void)argument;
    relay_policy_t policy;
    relay_policy_init(&policy);
    TickType_t wake = xTaskGetTickCount();
    esp_err_t last_error = ESP_OK;

    for (;;) {
        sensor_reading_t reading;
        const sensor_value_t *temperature = NULL;
        if (sensor_service_try_get_latest(&reading, 20) == ESP_OK) {
            temperature = &reading.temperature;
        }
        relay_policy_step(&policy, temperature, now_ms());

        esp_err_t request_error = ESP_OK;
        bool processed_request = false;
        request_t request;
        /* Bound work even when producers continually refill the queue. */
        for (unsigned i = 0; i < 8 &&
             xQueueReceive(s_requests, &request, 0) == pdTRUE; ++i) {
            processed_request = true;
            if (request == REQUEST_AUTO) {
                relay_policy_auto(&policy);
                relay_policy_step(&policy, temperature, now_ms());
                request_error = ESP_OK;
            } else {
                request_error = relay_policy_manual(&policy,
                    request == REQUEST_MANUAL_ON, temperature, now_ms());
            }
        }

        relay_driver_state_t driver = relay_driver_get_state();
        esp_err_t ret = driver.known ? ESP_OK : relay_driver_init();
        if (ret == ESP_OK) {
            /* Recheck age immediately before issuing an output command. */
            relay_policy_step(&policy, temperature, now_ms());
            driver = relay_driver_get_state();
            if (driver.on != policy.desired_on) {
                ret = relay_driver_set_state(policy.desired_on);
            }
        }
        if (ret != ESP_OK) {
            relay_policy_latch_off(&policy);
            if (ret != last_error) {
                ESP_LOGE(TAG, "Relay output unavailable: %s", esp_err_to_name(ret));
            }
        }
        last_error = ret;
        driver = relay_driver_get_state();
        xSemaphoreTake(s_state_mutex, portMAX_DELAY);
        s_state.mode = policy.mode;
        s_state.known = driver.known;
        s_state.on = driver.on;
        s_state.safety_inhibited = policy.safety_inhibited;
        s_state.error = ret;
        if (processed_request) {
            s_state.last_request_error = request_error != ESP_OK ? request_error : ret;
        }
        xSemaphoreGive(s_state_mutex);
        xTaskDelayUntil(&wake, pdMS_TO_TICKS(250));
    }
}

esp_err_t relay_control_init(void)
{
    if (s_started) {
        return ESP_OK;
    }
    s_requests = xQueueCreate(8, sizeof(request_t));
    s_state_mutex = xSemaphoreCreateMutex();
    if (s_requests == NULL || s_state_mutex == NULL) {
        if (s_requests != NULL) { vQueueDelete(s_requests); s_requests = NULL; }
        if (s_state_mutex != NULL) { vSemaphoreDelete(s_state_mutex); s_state_mutex = NULL; }
        return ESP_ERR_NO_MEM;
    }
    s_state = (relay_control_state_t) {
        .mode = RELAY_MODE_AUTO, .safety_inhibited = true,
        .error = ESP_ERR_INVALID_STATE,
    };
    if (xTaskCreate(control_task, "relay_control", 4096, NULL, 6, NULL) != pdPASS) {
        vQueueDelete(s_requests);
        vSemaphoreDelete(s_state_mutex);
        s_requests = NULL;
        s_state_mutex = NULL;
        return ESP_ERR_NO_MEM;
    }
    s_started = true;
    return ESP_OK;
}

static esp_err_t enqueue_request(request_t request)
{
    if (!s_started) {
        return ESP_ERR_INVALID_STATE;
    }
    if (request == REQUEST_MANUAL_ON) {
        sensor_reading_t reading;
        if (sensor_service_try_get_latest(&reading, 20) != ESP_OK ||
            !relay_temperature_usable(&reading.temperature, now_ms())) {
            return ESP_ERR_INVALID_STATE;
        }
    }
    return xQueueSend(s_requests, &request, 0) == pdTRUE ? ESP_OK : ESP_ERR_TIMEOUT;
}

esp_err_t relay_control_request_manual(bool on)
{
    return enqueue_request(on ? REQUEST_MANUAL_ON : REQUEST_MANUAL_OFF);
}

esp_err_t relay_control_request_auto(void)
{
    return enqueue_request(REQUEST_AUTO);
}

esp_err_t relay_control_get_state(relay_control_state_t *out)
{
    if (out == NULL) { return ESP_ERR_INVALID_ARG; }
    if (!s_started) { return ESP_ERR_INVALID_STATE; }
    if (xSemaphoreTake(s_state_mutex, pdMS_TO_TICKS(20)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    *out = s_state;
    xSemaphoreGive(s_state_mutex);
    return ESP_OK;
}
