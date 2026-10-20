#include <math.h>
#include <string.h>
#include "unity.h"
#include "relay_driver.h"
#include "relay_control.h"
#include "lcd_display.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "sdkconfig.h"

static esp_err_t s_gpio_init_error;
static esp_err_t s_gpio_write_error;
static int s_gpio_level = -1;
static unsigned s_gpio_init_calls;
static esp_err_t s_lcd_init_error;
static unsigned s_lcd_writes;
static unsigned s_lcd_fail_at;
static uint32_t s_lcd_timeout;
static unsigned s_lcd_bus_token;
static unsigned s_lcd_device_token;
static unsigned s_lcd_bus_created;
static unsigned s_lcd_bus_deleted;
static unsigned s_lcd_device_added;
static unsigned s_lcd_device_removed;
static unsigned s_lcd_transmits;
static unsigned s_lcd_fail_tx_at;
static esp_err_t s_lcd_remove_error;

/* Preserve unrelated SDK startup GPIO setup; only the demo pin is simulated. */
esp_err_t __real_gpio_config(const gpio_config_t *config);
esp_err_t __real_gpio_set_level(gpio_num_t gpio, uint32_t level);

esp_err_t __wrap_gpio_config(const gpio_config_t *config)
{
    if ((config->pin_bit_mask & (UINT64_C(1) << CONFIG_BB_GPIO_RELAY)) == 0) {
        return __real_gpio_config(config);
    }
    ++s_gpio_init_calls;
    TEST_ASSERT_EQUAL_HEX64(UINT64_C(1) << CONFIG_BB_GPIO_RELAY, config->pin_bit_mask);
    TEST_ASSERT_EQUAL(GPIO_MODE_OUTPUT, config->mode);
    TEST_ASSERT_EQUAL_INT(1, s_gpio_level); /* OFF latch precedes output enable. */
    return s_gpio_init_error;
}

esp_err_t __wrap_gpio_set_level(gpio_num_t gpio, uint32_t level)
{
    if (gpio != CONFIG_BB_GPIO_RELAY) { return __real_gpio_set_level(gpio, level); }
    TEST_ASSERT_EQUAL_INT(CONFIG_BB_GPIO_RELAY, gpio);
    if (s_gpio_write_error == ESP_OK) { s_gpio_level = (int)level; }
    return s_gpio_write_error;
}

esp_err_t __wrap_i2c_new_master_bus(const i2c_master_bus_config_t *config,
                                    i2c_master_bus_handle_t *out)
{
    TEST_ASSERT_EQUAL_INT(CONFIG_BB_GPIO_I2C_SDA, config->sda_io_num);
    TEST_ASSERT_EQUAL_INT(CONFIG_BB_GPIO_I2C_SCL, config->scl_io_num);
    ++s_lcd_bus_created;
    *out = (i2c_master_bus_handle_t)&s_lcd_bus_token;
    return ESP_OK;
}

esp_err_t __wrap_i2c_del_master_bus(i2c_master_bus_handle_t bus)
{
    (void)bus;
    ++s_lcd_bus_deleted;
    return ESP_OK;
}

esp_err_t __wrap_i2c_master_bus_add_device(i2c_master_bus_handle_t bus,
    const i2c_device_config_t *config, i2c_master_dev_handle_t *out)
{
    (void)bus;
    TEST_ASSERT_EQUAL_UINT(CONFIG_BB_LCD_I2C_ADDRESS, config->device_address);
    TEST_ASSERT_EQUAL_UINT(100000, config->scl_speed_hz);
    ++s_lcd_device_added;
    *out = (i2c_master_dev_handle_t)&s_lcd_device_token;
    return ESP_OK;
}

esp_err_t __wrap_i2c_master_bus_rm_device(i2c_master_dev_handle_t device)
{
    (void)device;
    if (s_lcd_remove_error != ESP_OK) { return s_lcd_remove_error; }
    ++s_lcd_device_removed;
    return ESP_OK;
}

esp_err_t __wrap_i2c_master_probe(i2c_master_bus_handle_t bus, uint16_t address,
                                 int timeout_ms)
{
    (void)bus;
    TEST_ASSERT_EQUAL_UINT(CONFIG_BB_LCD_I2C_ADDRESS, address);
    s_lcd_timeout = (uint32_t)timeout_ms;
    return s_lcd_init_error;
}

esp_err_t __wrap_i2c_master_transmit(i2c_master_dev_handle_t device,
    const uint8_t *bytes, size_t length, int timeout_ms)
{
    (void)device;
    s_lcd_timeout = (uint32_t)timeout_ms;
    TEST_ASSERT_EQUAL_INT(50, timeout_ms);
    TEST_ASSERT_TRUE(length == 3 || length == 6 || length == 102);
    for (size_t i = 0; i < length; i += 3) {
        TEST_ASSERT_EQUAL_HEX8(bytes[i] | 0x04, bytes[i + 1]);
        TEST_ASSERT_EQUAL_HEX8(bytes[i], bytes[i + 2]);
        TEST_ASSERT_BITS_LOW(0x02, bytes[i]); /* RW remains low. */
        TEST_ASSERT_BITS_HIGH(0x08, bytes[i]); /* Backlight remains on. */
    }
    ++s_lcd_transmits;
    if (s_lcd_fail_tx_at == s_lcd_transmits) { return ESP_ERR_TIMEOUT; }
    if (length == 102) {
        ++s_lcd_writes;
        uint8_t cursor = (bytes[0] & 0xf0) | (bytes[3] >> 4);
        TEST_ASSERT_TRUE(cursor == 0x80 || cursor == 0xc0);
        TEST_ASSERT_BITS_LOW(0x01, bytes[0]);
        for (size_t i = 6; i < length; i += 6) {
            TEST_ASSERT_BITS_HIGH(0x01, bytes[i]);
        }
        if (s_lcd_fail_at == s_lcd_writes) { return ESP_ERR_TIMEOUT; }
    }
    return ESP_OK;
}

static sensor_reading_t healthy_reading(void)
{
    return (sensor_reading_t) {
        .capture_uptime_ms = 0,
        .temperature = {.value = 30.0f, .has_value = true, .validity = SENSOR_VALID,
            .source = "sensor", .unit = "degC", .sample_uptime_ms = 0, .error = ESP_OK},
        .turbidity = {.value = 1942.0f, .has_value = true, .validity = SENSOR_UNVERIFIED},
        .ph = {.value = 7.8f, .has_value = true, .validity = SENSOR_UNVERIFIED,
            .source = "default"},
    };
}

static void test_auto_thresholds_and_staleness(void)
{
    relay_policy_t policy;
    relay_policy_init(&policy);
    TEST_ASSERT_EQUAL(RELAY_MODE_AUTO, policy.mode);
    TEST_ASSERT_FALSE(policy.desired_on);
    relay_policy_step(&policy, NULL, 0);
    TEST_ASSERT_TRUE(policy.safety_inhibited);
    sensor_reading_t reading = healthy_reading();
    reading.temperature.value = 32.49f;
    relay_policy_step(&policy, &reading.temperature, 1);
    TEST_ASSERT_FALSE(policy.desired_on);
    reading.temperature.value = 32.5f;
    relay_policy_step(&policy, &reading.temperature, 2);
    TEST_ASSERT_TRUE(policy.desired_on);
    reading.temperature.value = 31.01f;
    relay_policy_step(&policy, &reading.temperature, 3);
    TEST_ASSERT_TRUE(policy.desired_on);
    reading.temperature.value = 31.0f;
    relay_policy_step(&policy, &reading.temperature, 4);
    TEST_ASSERT_FALSE(policy.desired_on);
    reading.temperature.value = 33.0f;
    relay_policy_step(&policy, &reading.temperature, 59999);
    TEST_ASSERT_TRUE(policy.desired_on);
    relay_policy_step(&policy, &reading.temperature, 60000);
    TEST_ASSERT_FALSE(policy.desired_on);
    TEST_ASSERT_TRUE(policy.safety_inhibited);
    relay_policy_step(&policy, &reading.temperature, 60001);
    TEST_ASSERT_FALSE(policy.desired_on);
    reading.temperature.sample_uptime_ms = 60001;
    relay_policy_step(&policy, &reading.temperature, 60001);
    TEST_ASSERT_TRUE(policy.desired_on);
}

static void test_manual_priority_and_fault_latch(void)
{
    relay_policy_t policy;
    relay_policy_init(&policy);
    sensor_reading_t reading = healthy_reading();
    TEST_ASSERT_EQUAL(ESP_OK, relay_policy_manual(&policy, true, &reading.temperature, 0));
    TEST_ASSERT_TRUE(policy.desired_on); /* Below AUTO threshold: manual wins. */
    reading.temperature.value = 10.0f;
    relay_policy_step(&policy, &reading.temperature, 1);
    TEST_ASSERT_TRUE(policy.desired_on);
    reading.temperature.validity = SENSOR_INVALID;
    relay_policy_step(&policy, &reading.temperature, 2);
    TEST_ASSERT_FALSE(policy.desired_on);
    TEST_ASSERT_EQUAL(RELAY_MODE_MANUAL, policy.mode);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE,
        relay_policy_manual(&policy, true, &reading.temperature, 2));
    reading.temperature.validity = SENSOR_VALID;
    relay_policy_step(&policy, &reading.temperature, 3);
    TEST_ASSERT_FALSE(policy.desired_on); /* Recovery does not reapply old ON. */
    TEST_ASSERT_EQUAL(ESP_OK, relay_policy_manual(&policy, true, &reading.temperature, 3));
    reading.temperature.value = 32.0f;
    relay_policy_auto(&policy);
    relay_policy_step(&policy, &reading.temperature, 4);
    TEST_ASSERT_TRUE(policy.desired_on); /* Preserve ON in the hysteresis band. */
    TEST_ASSERT_EQUAL(ESP_OK, relay_policy_manual(&policy, false, &reading.temperature, 5));
    reading.temperature.value = 40.0f;
    relay_policy_step(&policy, &reading.temperature, 6);
    TEST_ASSERT_FALSE(policy.desired_on); /* Manual OFF overrides high temperature. */
    relay_policy_auto(&policy);
    relay_policy_step(&policy, &reading.temperature, 7);
    TEST_ASSERT_TRUE(policy.desired_on);
}

static void test_bad_temperature_never_authorizes_on(void)
{
    relay_policy_t policy;
    relay_policy_init(&policy);
    sensor_reading_t reading = healthy_reading();
    sensor_validity_t rejected[] = {SENSOR_INVALID, SENSOR_MISSING, SENSOR_STALE,
                                    SENSOR_UNVERIFIED};
    for (unsigned i = 0; i < sizeof(rejected) / sizeof(rejected[0]); ++i) {
        reading.temperature.validity = rejected[i];
        TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE,
            relay_policy_manual(&policy, true, &reading.temperature, 1));
        TEST_ASSERT_FALSE(policy.desired_on);
    }
    reading = healthy_reading();
    reading.temperature.value = NAN;
    TEST_ASSERT_FALSE(relay_temperature_usable(&reading.temperature, 1));
    reading.temperature.value = INFINITY;
    TEST_ASSERT_FALSE(relay_temperature_usable(&reading.temperature, 1));
    reading = healthy_reading();
    reading.temperature.has_value = false;
    TEST_ASSERT_FALSE(relay_temperature_usable(&reading.temperature, 1));
    reading = healthy_reading();
    reading.temperature.sample_uptime_ms = -1;
    TEST_ASSERT_FALSE(relay_temperature_usable(&reading.temperature, 1));
    reading.temperature.sample_uptime_ms = 2;
    TEST_ASSERT_FALSE(relay_temperature_usable(&reading.temperature, 1));
    reading.temperature.sample_uptime_ms = INT64_C(4294967296);
    TEST_ASSERT_TRUE(relay_temperature_usable(&reading.temperature, INT64_C(4294967297)));
}

static void test_relay_driver_mapping_and_errors(void)
{
    s_gpio_init_error = ESP_FAIL;
    TEST_ASSERT_EQUAL(ESP_FAIL, relay_driver_init());
    TEST_ASSERT_FALSE(relay_driver_get_state().known);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, relay_driver_set_state(true));
    s_gpio_init_error = ESP_OK;
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_init());
    TEST_ASSERT_TRUE(relay_driver_get_state().known);
    TEST_ASSERT_FALSE(relay_driver_get_state().on);
    TEST_ASSERT_EQUAL_INT(1, s_gpio_level);
    unsigned calls = s_gpio_init_calls;
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_init());
    TEST_ASSERT_EQUAL_UINT(calls, s_gpio_init_calls);
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_set_state(true));
    TEST_ASSERT_EQUAL_INT(0, s_gpio_level);
    TEST_ASSERT_TRUE(relay_driver_get_state().on);
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_set_state(false));
    TEST_ASSERT_EQUAL_INT(1, s_gpio_level);
    s_gpio_write_error = ESP_FAIL;
    TEST_ASSERT_EQUAL(ESP_FAIL, relay_driver_set_state(true));
    TEST_ASSERT_FALSE(relay_driver_get_state().known);
    TEST_ASSERT_FALSE(relay_driver_get_state().on); /* Failed write didn't claim ON. */
    s_gpio_write_error = ESP_OK;
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_init());
    TEST_ASSERT_EQUAL_INT(1, s_gpio_level);
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_set_state(true));
    s_gpio_write_error = ESP_FAIL;
    TEST_ASSERT_EQUAL(ESP_FAIL, relay_driver_set_state(false));
    TEST_ASSERT_FALSE(relay_driver_get_state().known);
    TEST_ASSERT_TRUE(relay_driver_get_state().on); /* No false OFF after failure. */
    s_gpio_write_error = ESP_OK;
    TEST_ASSERT_EQUAL(ESP_OK, relay_driver_init());
}

static void assert_frame_width(const lcd_frame_t *frame)
{
    TEST_ASSERT_EQUAL_UINT(16, strlen(frame->rows[0]));
    TEST_ASSERT_EQUAL_UINT(16, strlen(frame->rows[1]));
}

static void test_display_pages_and_faults(void)
{
    sensor_reading_t reading = healthy_reading();
    relay_control_state_t relay = {.mode = RELAY_MODE_MANUAL, .known = true};
    lcd_frame_t frame;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 0, &frame));
    TEST_ASSERT_EQUAL_STRING("Temp: 30.0 \xdf" "C   ", frame.rows[0]);
    TEST_ASSERT_EQUAL_STRING("Relay:OFF MANUAL", frame.rows[1]);
    assert_frame_width(&frame);
    relay.mode = RELAY_MODE_AUTO;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 0, &frame));
    TEST_ASSERT_EQUAL_STRING("Relay:OFF AUTO  ", frame.rows[1]);
    relay.on = true;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 0, &frame));
    TEST_ASSERT_EQUAL_STRING("Relay:ON AUTO   ", frame.rows[1]);
    relay.mode = RELAY_MODE_MANUAL;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 0, &frame));
    TEST_ASSERT_EQUAL_STRING("Relay:ON MANUAL ", frame.rows[1]);
    relay.on = false;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 3000, &frame));
    TEST_ASSERT_EQUAL_STRING("Turb: 1942 NTU  ", frame.rows[0]);
    TEST_ASSERT_EQUAL_STRING("pH: 7.80        ", frame.rows[1]);
    assert_frame_width(&frame);
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 6000, &frame));
    TEST_ASSERT_EQUAL_STRING("Temp: 30.0 \xdf" "C   ", frame.rows[0]);
    TEST_ASSERT_EQUAL_STRING("Relay:OFF MANUAL", frame.rows[1]);
    assert_frame_width(&frame);
    reading.turbidity.validity = SENSOR_INVALID;
    reading.turbidity.has_value = false;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 3000, &frame));
    TEST_ASSERT_EQUAL_STRING("Turb: ERROR     ", frame.rows[0]);
    TEST_ASSERT_NULL(strstr(frame.rows[0], "1942"));
    reading.turbidity.validity = SENSOR_MISSING;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 3000, &frame));
    TEST_ASSERT_EQUAL_STRING("Turb: NONE      ", frame.rows[0]);
    reading.turbidity.validity = SENSOR_STALE;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 3000, &frame));
    TEST_ASSERT_EQUAL_STRING("Turb: STALE     ", frame.rows[0]);
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 60000, &frame));
    TEST_ASSERT_NOT_NULL(strstr(frame.rows[0], "STALE"));
    TEST_ASSERT_EQUAL_STRING("Relay:OFF MANUAL", frame.rows[1]);
    relay.on = true;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 60001, &frame));
    TEST_ASSERT_NOT_NULL(strstr(frame.rows[1], "ON UNSAFE"));
    relay.known = false;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 60001, &frame));
    TEST_ASSERT_NOT_NULL(strstr(frame.rows[1], "UNKNOWN"));
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(NULL, NULL, 0, &frame));
    TEST_ASSERT_NOT_NULL(strstr(frame.rows[0], "MISSING"));
    assert_frame_width(&frame);
}

static void test_lcd_failure_and_row_cache(void)
{
    s_lcd_init_error = ESP_ERR_NOT_FOUND;
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, lcd_display_init());
    TEST_ASSERT_EQUAL_UINT(s_lcd_bus_created, s_lcd_bus_deleted);
    TEST_ASSERT_EQUAL_UINT(s_lcd_device_added, s_lcd_device_removed);
    s_lcd_init_error = ESP_OK;
    s_lcd_fail_tx_at = s_lcd_transmits + 2;
    TEST_ASSERT_EQUAL(ESP_ERR_TIMEOUT, lcd_display_init());
    TEST_ASSERT_EQUAL_UINT(s_lcd_bus_created, s_lcd_bus_deleted);
    TEST_ASSERT_EQUAL_UINT(s_lcd_device_added, s_lcd_device_removed);
    s_lcd_fail_tx_at = 0;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_init());
    sensor_reading_t reading = healthy_reading();
    relay_control_state_t relay = {.known = true};
    lcd_frame_t frame;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 0, &frame));
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_write_frame(&frame));
    TEST_ASSERT_EQUAL_UINT(2, s_lcd_writes);
    TEST_ASSERT_EQUAL_UINT(50, s_lcd_timeout);
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_write_frame(&frame));
    TEST_ASSERT_EQUAL_UINT(2, s_lcd_writes); /* No writes for unchanged cells/rows. */
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_format(&reading, &relay, 3000, &frame));
    s_lcd_fail_at = s_lcd_writes + 1;
    TEST_ASSERT_EQUAL(ESP_ERR_TIMEOUT, lcd_display_write_frame(&frame));
    TEST_ASSERT_EQUAL_UINT(3, s_lcd_writes); /* No second-row write after error. */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, lcd_display_write_frame(&frame));

    relay_policy_t policy;
    relay_policy_init(&policy);
    reading.temperature.value = 33.0f;
    relay_policy_step(&policy, &reading.temperature, 1);
    TEST_ASSERT_TRUE(policy.desired_on); /* LCD failure is not a control input. */
    relay_policy_step(&policy, &reading.temperature, 60000);
    TEST_ASSERT_FALSE(policy.desired_on);

    s_lcd_fail_at = 0;
    s_lcd_remove_error = ESP_FAIL;
    unsigned buses = s_lcd_bus_created;
    TEST_ASSERT_EQUAL(ESP_FAIL, lcd_display_init());
    TEST_ASSERT_EQUAL_UINT(buses, s_lcd_bus_created);
    s_lcd_remove_error = ESP_OK;
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_init());
    TEST_ASSERT_EQUAL(ESP_OK, lcd_display_write_frame(&frame));
    TEST_ASSERT_EQUAL_UINT(5, s_lcd_writes); /* Failed-frame cache was discarded. */
}

void run_t06_tests(void)
{
    RUN_TEST(test_auto_thresholds_and_staleness);
    RUN_TEST(test_manual_priority_and_fault_latch);
    RUN_TEST(test_bad_temperature_never_authorizes_on);
    RUN_TEST(test_relay_driver_mapping_and_errors);
    RUN_TEST(test_display_pages_and_faults);
    RUN_TEST(test_lcd_failure_and_row_cache);
}
