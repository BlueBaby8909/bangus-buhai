#include <math.h>
#include "unity.h"
#include "sensor_service.h"
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

static int64_t s_now_us;
static float s_temperature;
static int s_voltage_mv;
static esp_err_t s_temp_init_error = ESP_OK;
static esp_err_t s_temp_error = ESP_OK;
static esp_err_t s_turb_error = ESP_OK;
static bool s_block_temperature;
static SemaphoreHandle_t s_conversion_entered;
static SemaphoreHandle_t s_conversion_release;
static SemaphoreHandle_t s_read_done;
static esp_err_t s_background_read_error;

int64_t __wrap_sensor_service_uptime_ms(void) { return s_now_us / 1000; }
esp_err_t __wrap_ds18b20_sensor_init(void) { return s_temp_init_error; }
esp_err_t __wrap_turbidity_sensor_init(void) { return ESP_OK; }

esp_err_t __wrap_ds18b20_sensor_read(float *out)
{
    if (s_block_temperature) {
        xSemaphoreGive(s_conversion_entered);
        if (xSemaphoreTake(s_conversion_release, pdMS_TO_TICKS(1000)) != pdTRUE) {
            return ESP_ERR_TIMEOUT;
        }
    }
    *out = s_temperature;
    return s_temp_error;
}

esp_err_t __wrap_turbidity_sensor_read(int *out)
{
    if (s_temp_init_error == ESP_OK) {
        s_now_us += 1000;  /* Capture follows temperature acquisition by 1 ms. */
    }
    *out = s_voltage_mv;
    return s_turb_error;
}

void setUp(void) {}
void tearDown(void) {}

static void test_snapshot_lifecycle(void)
{
    sensor_reading_t reading;
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, sensor_service_get_latest(&reading));
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_init());
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_init());
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, sensor_service_read(NULL));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, sensor_service_get_latest(NULL));

    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_get_latest(&reading));
    TEST_ASSERT_EQUAL(SENSOR_MISSING, reading.temperature.validity);
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    TEST_ASSERT_EQUAL_INT64(-1, reading.temperature.sample_age_ms);
    TEST_ASSERT_EQUAL(SENSOR_MISSING, reading.turbidity.validity);
    TEST_ASSERT_EQUAL(SENSOR_UNVERIFIED, reading.ph.validity);
    TEST_ASSERT_EQUAL_STRING("default", reading.ph.source);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, CONFIG_BB_PH_DEFAULT / 100.0f, reading.ph.value);
    TEST_ASSERT_EQUAL_INT64(-1, reading.ph.sample_age_ms);
    TEST_ASSERT_EQUAL_INT64(-1, reading.ph.last_valid_age_ms);

    /* A missing temperature sensor must not prevent turbidity acquisition. */
    s_temp_init_error = ESP_ERR_NOT_FOUND;
    s_voltage_mv = 1840;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_EQUAL(SENSOR_MISSING, reading.temperature.validity);
    TEST_ASSERT_TRUE(reading.turbidity.has_value);
    TEST_ASSERT_EQUAL(SENSOR_UNVERIFIED, reading.turbidity.validity);
    TEST_ASSERT_EQUAL_INT64(-1, reading.turbidity.last_valid_age_ms);

    /* A genuine zero at uptime zero is a sample, not missing data. */
    s_temp_init_error = ESP_OK;
    s_temperature = 0.0f;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_TRUE(reading.temperature.has_value);
    TEST_ASSERT_EQUAL(SENSOR_VALID, reading.temperature.validity);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, reading.temperature.value);
    TEST_ASSERT_EQUAL_INT64(0, reading.temperature.sample_uptime_ms);
    TEST_ASSERT_EQUAL_INT64(1, reading.temperature.sample_age_ms);
    TEST_ASSERT_EQUAL_INT64(0, reading.turbidity.sample_age_ms);
    float first_turbidity = reading.turbidity.value;
    sensor_reading_t frozen = reading;

    s_now_us = INT64_C(2000000);
    s_temperature = 10.0f;
    s_voltage_mv = 1000;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 2.0f, reading.temperature.value);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.9f * first_turbidity + 300.0f,
                             reading.turbidity.value);
    TEST_ASSERT_EQUAL_INT64(1, frozen.capture_uptime_ms);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, frozen.temperature.value);

    /* Rejected values neither update the filter nor the last-success time. */
    s_now_us = INT64_C(3000000);
    s_temperature = NAN;
    s_turb_error = ESP_ERR_TIMEOUT;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    TEST_ASSERT_EQUAL(SENSOR_INVALID, reading.temperature.validity);
    TEST_ASSERT_EQUAL_INT64(2000, reading.temperature.sample_uptime_ms);
    TEST_ASSERT_FALSE(reading.turbidity.has_value);
    s_temperature = INFINITY;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    TEST_ASSERT_EQUAL_INT64(2000, reading.temperature.sample_uptime_ms);

    s_temperature = 126.0f;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    TEST_ASSERT_EQUAL_INT64(2000, reading.temperature.sample_uptime_ms);

    s_turb_error = ESP_OK;
    s_voltage_mv = -1;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FALSE(reading.turbidity.has_value);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_RESPONSE, reading.turbidity.error);

    s_now_us = INT64_C(4000000);
    s_temperature = 12.0f;
    s_voltage_mv = 1840;
    s_turb_error = ESP_OK;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 4.0f, reading.temperature.value);

    /* Staleness must advance even when no new acquisition happens. */
    s_now_us = INT64_C(63999000);
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_get_latest(&reading));
    TEST_ASSERT_EQUAL(SENSOR_VALID, reading.temperature.validity);
    TEST_ASSERT_EQUAL_INT64(59999, reading.temperature.sample_age_ms);
    s_now_us = INT64_C(64000000);
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_get_latest(&reading));
    TEST_ASSERT_EQUAL(SENSOR_STALE, reading.temperature.validity);
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    s_now_us = INT64_C(64001000);
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_get_latest(&reading));
    TEST_ASSERT_EQUAL(SENSOR_STALE, reading.temperature.validity);

    /* Recovery after staleness reseeds the filter instead of reusing old data. */
    s_now_us = INT64_C(65000000);
    s_temperature = 30.0f;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_EQUAL(SENSOR_VALID, reading.temperature.validity);
    TEST_ASSERT_EQUAL_FLOAT(30.0f, reading.temperature.value);

    /* A failed temperature read does not invalidate the other sensor. */
    s_temp_error = ESP_ERR_INVALID_CRC;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_FALSE(reading.temperature.has_value);
    TEST_ASSERT_TRUE(reading.turbidity.has_value);

    /* Ages must remain correct beyond the 32-bit millisecond boundary. */
    s_temp_error = ESP_OK;
    s_now_us = (INT64_C(4294967296) + 1000) * 1000;
    TEST_ASSERT_EQUAL(ESP_OK, sensor_service_read(&reading));
    TEST_ASSERT_EQUAL_INT64(INT64_C(4294968296), reading.temperature.sample_uptime_ms);
    TEST_ASSERT_EQUAL_INT64(1, reading.temperature.last_valid_age_ms);
}

void run_t06_tests(void);

static void background_sensor_read(void *argument)
{
    (void)argument;
    sensor_reading_t reading;
    s_background_read_error = sensor_service_read(&reading);
    xSemaphoreGive(s_read_done);
    vTaskDelete(NULL);
}

static void test_snapshot_access_during_conversion(void)
{
    s_conversion_entered = xSemaphoreCreateBinary();
    s_conversion_release = xSemaphoreCreateBinary();
    s_read_done = xSemaphoreCreateBinary();
    TEST_ASSERT_NOT_NULL(s_conversion_entered);
    TEST_ASSERT_NOT_NULL(s_conversion_release);
    TEST_ASSERT_NOT_NULL(s_read_done);
    s_block_temperature = true;
    BaseType_t created = xTaskCreate(background_sensor_read, "test_read", 4096,
                                     NULL, 5, NULL);
    if (created != pdPASS) {
        s_block_temperature = false;
        vSemaphoreDelete(s_conversion_entered);
        vSemaphoreDelete(s_conversion_release);
        vSemaphoreDelete(s_read_done);
        TEST_FAIL_MESSAGE("Could not create simulated sensing task");
    }
    BaseType_t entered = xSemaphoreTake(s_conversion_entered, pdMS_TO_TICKS(1000));
    sensor_reading_t reading;
    esp_err_t snapshot_error = sensor_service_try_get_latest(&reading, 20);
    xSemaphoreGive(s_conversion_release);
    BaseType_t finished = xSemaphoreTake(s_read_done, pdMS_TO_TICKS(2000));
    if (finished == pdTRUE) {
        s_block_temperature = false;
        vSemaphoreDelete(s_conversion_entered);
        vSemaphoreDelete(s_conversion_release);
        vSemaphoreDelete(s_read_done);
    }
    TEST_ASSERT_EQUAL(pdTRUE, entered);
    TEST_ASSERT_EQUAL(pdTRUE, finished);
    TEST_ASSERT_EQUAL(ESP_OK, snapshot_error);
    TEST_ASSERT_EQUAL(ESP_OK, s_background_read_error);
}

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_snapshot_lifecycle);
    RUN_TEST(test_snapshot_access_during_conversion);
    run_t06_tests();
    UNITY_END();
}
