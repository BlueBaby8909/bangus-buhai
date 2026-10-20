#include "sensor_service.h"
#include "sensor_service_clock.h"
#include "ds18b20_sensor.h"
#include "turbidity_sensor.h"
#include "sdkconfig.h"

#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#define TEMPERATURE_STALE_MS INT64_C(60000)
#define TEMPERATURE_ALPHA 0.2f
#define TURBIDITY_ALPHA 0.1f
#define DS18B20_MIN_C (-55.0f)
#define DS18B20_MAX_C 125.0f

typedef struct {
    float filtered;
    bool has_sample;
    bool last_read_ok;
    int64_t sample_ms;
    esp_err_t error;
} sample_state_t;

static SemaphoreHandle_t s_mutex;
static sample_state_t s_temperature;
static sample_state_t s_turbidity;

static void accept_sample(sample_state_t *state, float value, float alpha,
                          int64_t sample_ms)
{
    state->filtered = state->has_sample
        ? alpha * value + (1.0f - alpha) * state->filtered : value;
    state->has_sample = true;
    state->last_read_ok = true;
    state->sample_ms = sample_ms;
    state->error = ESP_OK;
}

static void reject_sample(sample_state_t *state, esp_err_t error)
{
    state->last_read_ok = false;
    state->error = error;
    /* Preserve the filter and last accepted sample time for diagnosis/recovery. */
}

static sensor_value_t make_value(const sample_state_t *state, const char *unit,
                                  bool temperature, int64_t now_ms)
{
    sensor_value_t result = {
        .validity = (state->error == ESP_ERR_NOT_FOUND ||
                     state->error == ESP_ERR_INVALID_STATE)
            ? SENSOR_MISSING : SENSOR_INVALID,
        .source = "sensor",
        .unit = unit,
        .sample_uptime_ms = -1,
        .sample_age_ms = -1,
        .last_valid_age_ms = -1,
        .error = state->error,
    };

    if (state->has_sample) {
        result.sample_uptime_ms = state->sample_ms;
        result.sample_age_ms = now_ms - state->sample_ms;
        /* Unverified NTU conversion does not establish a last valid NTU sample. */
        result.last_valid_age_ms = temperature ? result.sample_age_ms : -1;
        if (temperature && result.sample_age_ms >= TEMPERATURE_STALE_MS) {
            result.validity = SENSOR_STALE;
        } else if (state->last_read_ok) {
            result.value = state->filtered;
            result.has_value = true;
            result.validity = temperature ? SENSOR_VALID : SENSOR_UNVERIFIED;
        }
    }
    return result;
}

static void copy_snapshot(sensor_reading_t *out)
{
    int64_t now_ms = sensor_service_uptime_ms();
    *out = (sensor_reading_t) {
        .capture_uptime_ms = now_ms,
        .temperature = make_value(&s_temperature, "degC", true, now_ms),
        .turbidity = make_value(&s_turbidity, "NTU", false, now_ms),
        .ph = {
            .value = CONFIG_BB_PH_DEFAULT / 100.0f,
            .has_value = true,
            .validity = SENSOR_UNVERIFIED,
            .source = "default",
            .unit = "pH",
            .sample_uptime_ms = -1,
            .sample_age_ms = -1,
            .last_valid_age_ms = -1,
            .error = ESP_OK,
        },
    };
}

/* Prototype conversion only. The 2.28 scale and polynomial are NOT verified
 * sensor calibration. Successful converted values remain SENSOR_UNVERIFIED.
 */
static float prototype_ntu(int voltage_mv)
{
    float voltage = (voltage_mv / 1000.0f) * 2.28f;
    if (voltage < 2.5f) {
        return 3000.0f;
    }
    if (voltage > 4.2f) {
        return 0.0f;
    }
    float ntu = -1120.4f * voltage * voltage + 5742.3f * voltage - 4352.9f;
    return fminf(3000.0f, fmaxf(0.0f, ntu));
}

esp_err_t sensor_service_init(void)
{
    if (s_mutex != NULL) {
        return ESP_OK;
    }
    s_mutex = xSemaphoreCreateMutex();
    if (s_mutex == NULL) {
        return ESP_ERR_NO_MEM;
    }
    s_temperature.error = ESP_ERR_NOT_FOUND;
    s_turbidity.error = ESP_ERR_NOT_FOUND;
    return ESP_OK;
}

esp_err_t sensor_service_read(sensor_reading_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_mutex == NULL) {
        return ESP_ERR_INVALID_STATE;
    }
    float temperature = NAN;
    esp_err_t temperature_error = ds18b20_sensor_init();
    if (temperature_error == ESP_OK) {
        temperature_error = ds18b20_sensor_read(&temperature);
    }
    /* Sensor operating range, not a biological water-quality policy. */
    if (temperature_error == ESP_OK && (!isfinite(temperature) ||
                         temperature < DS18B20_MIN_C ||
                         temperature > DS18B20_MAX_C)) {
        temperature_error = ESP_ERR_INVALID_RESPONSE;
    }
    int64_t temperature_ms = sensor_service_uptime_ms();

    int voltage_mv = -1;
    esp_err_t turbidity_error = turbidity_sensor_init();
    if (turbidity_error == ESP_OK) {
        turbidity_error = turbidity_sensor_read(&voltage_mv);
    }
    if (turbidity_error == ESP_OK && voltage_mv < 0) {
        turbidity_error = ESP_ERR_INVALID_RESPONSE;
    }
    int64_t turbidity_ms = sensor_service_uptime_ms();

    /* Only the sensing task acquires hardware. Readers keep access to the
     * previous complete snapshot while driver conversions are in progress.
     */
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    if (temperature_error == ESP_OK) {
        bool was_stale = s_temperature.has_sample &&
            temperature_ms - s_temperature.sample_ms >= TEMPERATURE_STALE_MS;
        accept_sample(&s_temperature, temperature,
                      was_stale ? 1.0f : TEMPERATURE_ALPHA, temperature_ms);
    } else {
        reject_sample(&s_temperature, temperature_error);
    }
    if (turbidity_error == ESP_OK) {
        accept_sample(&s_turbidity, prototype_ntu(voltage_mv), TURBIDITY_ALPHA,
                      turbidity_ms);
    } else {
        reject_sample(&s_turbidity, turbidity_error);
    }

    copy_snapshot(out);
    xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t sensor_service_get_latest(sensor_reading_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_mutex == NULL) {
        return ESP_ERR_INVALID_STATE;
    }
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    copy_snapshot(out);
    xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t sensor_service_try_get_latest(sensor_reading_t *out, uint32_t timeout_ms)
{
    if (out == NULL) { return ESP_ERR_INVALID_ARG; }
    if (s_mutex == NULL) { return ESP_ERR_INVALID_STATE; }
    if (xSemaphoreTake(s_mutex, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    copy_snapshot(out);
    xSemaphoreGive(s_mutex);
    return ESP_OK;
}

const char *sensor_validity_name(sensor_validity_t validity)
{
    switch (validity) {
    case SENSOR_VALID: return "valid";
    case SENSOR_INVALID: return "invalid";
    case SENSOR_MISSING: return "missing";
    case SENSOR_STALE: return "stale";
    case SENSOR_UNVERIFIED: return "unverified";
    default: return "unknown";
    }
}
