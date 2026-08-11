/**
 * @file sensor_service.c
 * @brief Sensor aggregation: reads physical sensors, applies EMA filtering,
 *        validates ranges, tracks staleness, and exposes thread-safe readings.
 *
 * PHYSICAL SENSORS vs. SOFT SENSORS
 * ===================================
 * This device currently has two physical sensors:
 *   1. DS18B20  → temperature (°C)
 *   2. Turbidity sensor → NTU (via ADC + polynomial)
 *
 * pH is NOT measured. It is filled with the CONFIG_BB_PH_DEFAULT / 100.0f
 * constant and tagged ph_source = "default".
 *
 * All other water quality parameters (dissolved oxygen, ammonia, etc.) are
 * "soft sensors" — they are PREDICTED by the LSTM model on the backend, not
 * measured here. This file must not pretend to measure what it does not.
 *
 * EMA FILTER (Exponential Moving Average):
 *   new_filtered = α × raw + (1 − α) × prev_filtered
 *   α = 0.2 (temperature) and 0.1 (turbidity) give a good balance of
 *   responsiveness vs. noise rejection for aquaculture monitoring intervals.
 *
 * RANGE VALIDATION:
 *   Temperature: 0–60 °C (physically possible in an aquaculture context)
 *   Turbidity  : 0–3000 NTU (full sensor range)
 *   Out-of-range values are clamped and logged as warnings.
 *
 * THREAD SAFETY:
 *   s_latest is protected by s_mutex. sensor_service_read() takes the mutex
 *   for the entire read-filter-validate-store cycle.
 *   sensor_service_get_latest() takes it only to copy the struct out.
 *
 * SENSOR STALENESS:
 *   If no successful temperature read occurs within SENSOR_STALE_TIMEOUT_MS,
 *   sensor_service_is_temperature_stale() returns true. The control_task uses
 *   this to place the relay in a safe (OFF) state rather than running on a
 *   frozen EMA value.
 */

#include "sensor_service.h"
#include "ds18b20_sensor.h"
#include "turbidity_sensor.h"
#include "app_events.h"
#include "sdkconfig.h"

#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_timer.h"

static const char *TAG = "SENSOR_SVC";

/* ── EMA smoothing factors ──────────────────────────────────────────────────
 * α closer to 1 = faster response, more noise
 * α closer to 0 = smoother, slower to react
 * Values chosen for 2-second sensor polling interval. */
#define EMA_ALPHA_TEMP  0.2f
#define EMA_ALPHA_TURB  0.1f

/* ── Physical sensor valid ranges ──────────────────────────────────────────── */
#define TEMP_MIN_VALID   0.0f
#define TEMP_MAX_VALID  60.0f
#define TURB_MIN_VALID   0.0f
#define TURB_MAX_VALID  3000.0f

/* ── Staleness timeout ─────────────────────────────────────────────────────── */
#define SENSOR_STALE_TIMEOUT_MS (60UL * 1000UL)   /* 60 seconds */

/* ── Module state ──────────────────────────────────────────────────────────── */
static SemaphoreHandle_t s_mutex = NULL;
static sensor_reading_t  s_latest;
static bool              s_has_reading      = false;
static bool              s_ema_initialized  = false;
static float             s_ema_temp         = 0.0f;
static float             s_ema_turb         = 0.0f;
static uint32_t          s_last_temp_ok_ms  = 0;   /* time of last good temp read */

/* ── Clamp helper ──────────────────────────────────────────────────────────── */
static float clamp(float v, float lo, float hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* ── Public API ────────────────────────────────────────────────────────────── */

esp_err_t sensor_service_init(void)
{
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        ESP_LOGE(TAG, "Failed to create mutex");
        return ESP_ERR_NO_MEM;
    }
    memset(&s_latest, 0, sizeof(s_latest));
    ESP_LOGI(TAG, "Sensor service initialised");
    return ESP_OK;
}

esp_err_t sensor_service_read(sensor_reading_t *out)
{
    if (!s_mutex || !out) {
        return ESP_ERR_INVALID_STATE;
    }

    uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000ULL);

    /* ── 1. Read temperature ──────────────────────────────────────────────── */
    float raw_temp = 0.0f;
    bool  temp_ok  = false;

    esp_err_t ret = ds18b20_sensor_read(&raw_temp);
    if (ret == ESP_OK) {
        /* Validate range before accepting */
        if (raw_temp < TEMP_MIN_VALID || raw_temp > TEMP_MAX_VALID) {
            ESP_LOGW(TAG, "Temperature %.1f°C out of valid range [%.0f, %.0f] — clamping",
                     raw_temp, TEMP_MIN_VALID, TEMP_MAX_VALID);
            raw_temp = clamp(raw_temp, TEMP_MIN_VALID, TEMP_MAX_VALID);
        }
        temp_ok = true;
        s_last_temp_ok_ms = now_ms;
    } else {
        ESP_LOGW(TAG, "DS18B20 read failed (%s) — using EMA hold value",
                 esp_err_to_name(ret));
        /* Fall through: EMA keeps last value; validity flag is false */
    }

    /* ── 2. Read turbidity ────────────────────────────────────────────────── */
    int   raw_turb_mv = 0;
    float raw_ntu     = 0.0f;
    bool  turb_ok     = false;

    ret = turbidity_sensor_read(&raw_turb_mv);
    if (ret == ESP_OK) {
        float voltage = (float)raw_turb_mv / 1000.0f;   /* mV → V */

        /* Polynomial NTU conversion (DFRobot standard curve) */
        if (voltage < 2.5f) {
            raw_ntu = TURB_MAX_VALID;
        } else if (voltage > 4.2f) {
            raw_ntu = 0.0f;
        } else {
            raw_ntu = -1120.4f * (voltage * voltage) + 5742.3f * voltage - 4352.9f;
        }
        raw_ntu = clamp(raw_ntu, TURB_MIN_VALID, TURB_MAX_VALID);
        turb_ok = true;
    } else {
        ESP_LOGW(TAG, "Turbidity read failed (%s) — using EMA hold value",
                 esp_err_to_name(ret));
    }

    /* ── 3. Apply EMA filter ─────────────────────────────────────────────── */
    xSemaphoreTake(s_mutex, portMAX_DELAY);

    if (!s_ema_initialized) {
        s_ema_temp = temp_ok ? raw_temp : 0.0f;
        s_ema_turb = turb_ok ? raw_ntu  : 0.0f;
        s_ema_initialized = true;
    } else {
        if (temp_ok) {
            s_ema_temp = (EMA_ALPHA_TEMP * raw_temp) + ((1.0f - EMA_ALPHA_TEMP) * s_ema_temp);
        }
        /* If temp read failed, s_ema_temp holds the last good filtered value. */

        if (turb_ok) {
            s_ema_turb = (EMA_ALPHA_TURB * raw_ntu) + ((1.0f - EMA_ALPHA_TURB) * s_ema_turb);
        }
    }

    /* ── 4. Build result struct ─────────────────────────────────────────── */
    s_latest.temperature          = s_ema_temp;
    s_latest.turbidity            = s_ema_turb;
    s_latest.ph                   = CONFIG_BB_PH_DEFAULT / 100.0f;
    s_latest.temperature_valid    = temp_ok;
    s_latest.turbidity_valid      = turb_ok;
    s_latest.timestamp_ms         = now_ms;

    /* Track consecutive failures (both sensors must succeed for a clean read) */
    if (temp_ok && turb_ok) {
        s_latest.consecutive_failures = 0;
    } else {
        s_latest.consecutive_failures++;
        if (s_latest.consecutive_failures % 10 == 0) {
            ESP_LOGE(TAG, "%lu consecutive partial read failures",
                     (unsigned long)s_latest.consecutive_failures);
        }
    }

    /* pH source is always "default" until a real sensor is added. */
    strlcpy(s_latest.ph_source, "default", sizeof(s_latest.ph_source));

    *out = s_latest;
    s_has_reading = true;

    xSemaphoreGive(s_mutex);

    ESP_LOGD(TAG, "Reading: T=%.1f°C[%s] Turb=%.1fNTU[%s] pH=%.2f[%s]",
             out->temperature,  temp_ok ? "ok" : "stale",
             out->turbidity,    turb_ok ? "ok" : "stale",
             out->ph, out->ph_source);

    /* Post event so event-driven tasks (like the telemetry task) can react
     * without polling — more CPU efficient than a tight polling loop. */
    esp_event_post(SENSOR_EVENTS, SENSOR_EVENT_DATA_READY,
                   out, sizeof(sensor_reading_t), 0);

    return ESP_OK;
}

esp_err_t sensor_service_get_latest(sensor_reading_t *out)
{
    if (!s_mutex || !out) return ESP_ERR_INVALID_STATE;

    xSemaphoreTake(s_mutex, portMAX_DELAY);
    if (!s_has_reading) {
        xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    *out = s_latest;
    xSemaphoreGive(s_mutex);
    return ESP_OK;
}

bool sensor_service_is_temperature_stale(void)
{
    if (!s_has_reading) return true;   /* no reading at all = stale */

    uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000ULL);
    return (now_ms - s_last_temp_ok_ms) > SENSOR_STALE_TIMEOUT_MS;
}
