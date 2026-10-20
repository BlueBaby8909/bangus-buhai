#include "lcd_display.h"
#include "driver/i2c_master.h"
#include "esp_rom_sys.h"
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdbool.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static bool s_ready;
static bool s_row_valid[2];
static lcd_frame_t s_previous;
static i2c_master_bus_handle_t s_bus;
static i2c_master_dev_handle_t s_device;

#define LCD_TIMEOUT_MS 50
#define LCD_BACKLIGHT 0x08
#define LCD_ENABLE 0x04

static esp_err_t release_bus(void)
{
    if (s_device != NULL) {
        esp_err_t ret = i2c_master_bus_rm_device(s_device);
        if (ret != ESP_OK) { return ret; }
        s_device = NULL;
    }
    if (s_bus != NULL) {
        esp_err_t ret = i2c_del_master_bus(s_bus);
        if (ret != ESP_OK) { return ret; }
        s_bus = NULL;
    }
    return ESP_OK;
}

/* Same PCF8574 wiring as the working prototype: D4..D7=P4..P7,
 * RS=P0, RW=P1 (kept low), EN=P2, backlight=P3.
 * At 100 kHz each I2C byte holds the output for about 90 us, satisfying the
 * enable-pulse and ordinary LCD instruction timing without unlimited waits.
 */
static void encode_nibble(uint8_t out[3], uint8_t nibble, bool data)
{
    uint8_t base = (nibble & 0xf0) | LCD_BACKLIGHT | (data ? 1 : 0);
    out[0] = base;
    out[1] = base | LCD_ENABLE;
    out[2] = base;
}

static void encode_byte(uint8_t out[6], uint8_t value, bool data)
{
    encode_nibble(out, value, data);
    encode_nibble(out + 3, (uint8_t)(value << 4), data);
}

static esp_err_t write_nibble(uint8_t value)
{
    uint8_t bytes[3];
    encode_nibble(bytes, value, false);
    return i2c_master_transmit(s_device, bytes, sizeof(bytes), LCD_TIMEOUT_MS);
}

static esp_err_t write_command(uint8_t value)
{
    uint8_t bytes[6];
    encode_byte(bytes, value, false);
    return i2c_master_transmit(s_device, bytes, sizeof(bytes), LCD_TIMEOUT_MS);
}

esp_err_t lcd_display_init(void)
{
    if (s_ready) { return ESP_OK; }
    s_row_valid[0] = false;
    s_row_valid[1] = false;
    esp_err_t ret = release_bus();
    if (ret != ESP_OK) { return ret; }
    i2c_master_bus_config_t bus_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = -1,
        .sda_io_num = CONFIG_BB_GPIO_I2C_SDA,
        .scl_io_num = CONFIG_BB_GPIO_I2C_SCL,
        .flags.enable_internal_pullup = true,
    };
    ret = i2c_new_master_bus(&bus_config, &s_bus);
    if (ret != ESP_OK) { return ret; }
    i2c_device_config_t device_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = CONFIG_BB_LCD_I2C_ADDRESS,
        .scl_speed_hz = 100000,
    };
    ret = i2c_master_bus_add_device(s_bus, &device_config, &s_device);
    if (ret != ESP_OK) { goto failed; }
    vTaskDelay(pdMS_TO_TICKS(50));
    ret = i2c_master_probe(s_bus, CONFIG_BB_LCD_I2C_ADDRESS, LCD_TIMEOUT_MS);
    if (ret != ESP_OK) { goto failed; }
    const uint8_t nibbles[] = {0x30, 0x30, 0x30, 0x20};
    for (unsigned i = 0; i < sizeof(nibbles); ++i) {
        ret = write_nibble(nibbles[i]);
        if (ret != ESP_OK) { goto failed; }
        esp_rom_delay_us(i == 0 ? 5000 : 1000);
    }
    const uint8_t commands[] = {0x28, 0x08, 0x01, 0x06, 0x0c};
    for (unsigned i = 0; i < sizeof(commands); ++i) {
        ret = write_command(commands[i]);
        if (ret != ESP_OK) { goto failed; }
        esp_rom_delay_us(commands[i] == 0x01 ? 2000 : 50);
    }
    s_ready = true;
    return ESP_OK;

failed:
    /* Failed deletion retains its handle; the next init retries cleanup first. */
    (void)release_bus();
    return ret;
}

esp_err_t lcd_display_write_frame(const lcd_frame_t *frame)
{
    if (frame == NULL || strnlen(frame->rows[0], LCD_COLUMNS + 1) != LCD_COLUMNS ||
        strnlen(frame->rows[1], LCD_COLUMNS + 1) != LCD_COLUMNS) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!s_ready) { return ESP_ERR_INVALID_STATE; }
    for (unsigned row = 0; row < 2; ++row) {
        if (s_row_valid[row] &&
            memcmp(s_previous.rows[row], frame->rows[row], LCD_COLUMNS) == 0) {
            continue;
        }
        uint8_t bytes[(LCD_COLUMNS + 1) * 6];
        encode_byte(bytes, row == 0 ? 0x80 : 0xc0, false);
        for (unsigned column = 0; column < LCD_COLUMNS; ++column) {
            encode_byte(bytes + (column + 1) * 6, (uint8_t)frame->rows[row][column], true);
        }
        esp_err_t ret = i2c_master_transmit(s_device, bytes, sizeof(bytes), LCD_TIMEOUT_MS);
        if (ret != ESP_OK) {
            s_ready = false;
            s_row_valid[0] = false;
            s_row_valid[1] = false;
            return ret;
        }
        memcpy(s_previous.rows[row], frame->rows[row], LCD_COLUMNS + 1);
        s_row_valid[row] = true;
    }
    return ESP_OK;
}

static void row_text(char row[LCD_COLUMNS + 1], const char *format, ...)
{
    char text[80];
    va_list arguments;
    va_start(arguments, format);
    vsnprintf(text, sizeof(text), format, arguments);
    va_end(arguments);
    memset(row, ' ', LCD_COLUMNS);
    size_t length = strnlen(text, LCD_COLUMNS);
    memcpy(row, text, length);
    row[LCD_COLUMNS] = '\0';
}

static const char *temperature_status(const sensor_value_t *temperature, int64_t now_ms)
{
    if (temperature == NULL) { return "MISSING"; }
    if (temperature->validity == SENSOR_STALE ||
        (temperature->sample_uptime_ms >= 0 && now_ms >= temperature->sample_uptime_ms &&
         now_ms - temperature->sample_uptime_ms >= INT64_C(60000))) {
        return "STALE";
    }
    return temperature->validity == SENSOR_MISSING ? "MISSING" : "INVALID";
}

esp_err_t lcd_display_format(const sensor_reading_t *reading,
                                 const relay_control_state_t *relay,
                                 int64_t now_ms, lcd_frame_t *out)
{
    if (out == NULL || now_ms < 0) { return ESP_ERR_INVALID_ARG; }
    const sensor_value_t *temperature = reading == NULL ? NULL : &reading->temperature;
    bool healthy = relay_temperature_usable(temperature, now_ms);
    bool fault = !healthy || relay == NULL || relay->safety_inhibited ||
                 !relay->known || relay->error != ESP_OK;
    unsigned page = fault ? 0 : (unsigned)((now_ms / 3000) % 2);
    if (page == 0) {
        if (healthy) {
            /* HD44780 degree glyph; UTF-8 would occupy two LCD cells. */
            row_text(out->rows[0], "Temp: %.1f %cC", (double)temperature->value, 0xdf);
        } else {
            row_text(out->rows[0], "Temp: %s", temperature_status(temperature, now_ms));
        }
        if (relay == NULL || !relay->known || relay->error != ESP_OK) {
            row_text(out->rows[1], "Relay: UNKNOWN");
        } else if (fault && relay->on) {
            /* Never render an OFF claim while the controller still reports ON. */
            row_text(out->rows[1], "Relay: ON UNSAFE");
        } else {
            row_text(out->rows[1], "Relay:%s %s", relay->on ? "ON" : "OFF",
                     relay->mode == RELAY_MODE_MANUAL ? "MANUAL" : "AUTO");
        }
    } else {
        const sensor_value_t *turbidity = &reading->turbidity;
        if (turbidity->has_value && isfinite(turbidity->value) &&
            turbidity->value >= 0.0f && turbidity->value <= 3000.0f &&
            (turbidity->validity == SENSOR_UNVERIFIED ||
             turbidity->validity == SENSOR_VALID)) {
            row_text(out->rows[0], "Turb: %.0f NTU", (double)turbidity->value);
        } else {
            const char *status = turbidity->validity == SENSOR_MISSING ? "NONE" :
                turbidity->validity == SENSOR_STALE ? "STALE" : "ERROR";
            row_text(out->rows[0], "Turb: %s", status);
        }
        const sensor_value_t *ph = &reading->ph;
        if (ph->has_value && isfinite(ph->value) && ph->value >= 0.0f &&
            ph->value <= 14.0f && ph->source != NULL &&
            strcmp(ph->source, "default") == 0 && ph->validity == SENSOR_UNVERIFIED) {
            row_text(out->rows[1], "pH: %.2f", (double)ph->value);
        } else {
            row_text(out->rows[1], "pH: UNAVAILABLE");
        }
    }
    return ESP_OK;
}
