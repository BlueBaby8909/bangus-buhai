#include "lcd_display.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "driver/i2c_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define LCD_RS_CMD  0x00 // Register Select: 0 = Command
#define LCD_RS_DATA 0x01 // Register Select: 1 = Data
#define LCD_RW  0x02 // Read/Write
#define LCD_EN  0x04 // Enable
#define LCD_BL  0x08 // Backlight

static i2c_master_dev_handle_t dev_handle;

static esp_err_t lcd_send_i2c_byte(uint8_t data){
    return i2c_master_transmit(dev_handle, &data, 1, -1);
}

static void lcd_pulse_enable(uint8_t data){
    lcd_send_i2c_byte(data | LCD_BL | LCD_EN);

    esp_rom_delay_us(1);

    lcd_send_i2c_byte((data & ~LCD_EN) | LCD_BL);

    esp_rom_delay_us(50);
}

static void lcd_write_nibble(uint8_t nibble, uint8_t rs_mode) {
    uint8_t i2c_data = (nibble & 0xF0) | rs_mode | LCD_BL;
    
    lcd_send_i2c_byte(i2c_data);
    lcd_pulse_enable(i2c_data);
}

static void lcd_write_byte(uint8_t data, uint8_t rs_mode) {
    lcd_write_nibble(data & 0xF0, rs_mode);
    lcd_write_nibble(data << 4, rs_mode);
}



esp_err_t lcd_display_init(void) {
    i2c_master_bus_config_t i2c_mst_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = -1,
        .scl_io_num = CONFIG_BB_GPIO_I2C_SCL,
        .sda_io_num = CONFIG_BB_GPIO_I2C_SDA,
        .flags.enable_internal_pullup = true
    };

    i2c_master_bus_handle_t bus_handle;
    ESP_ERROR_CHECK(i2c_new_master_bus(&i2c_mst_config, &bus_handle));

    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = 0x27,
        .scl_speed_hz = 100000,
    };

    
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus_handle, &dev_config, &dev_handle));

    vTaskDelay(pdMS_TO_TICKS(50));

    lcd_write_nibble(0x30, LCD_RS_CMD);
    esp_rom_delay_us(5000);
    lcd_write_nibble(0x30, LCD_RS_CMD);
    esp_rom_delay_us(1000);
    lcd_write_nibble(0x30, LCD_RS_CMD);
    esp_rom_delay_us(1000);
    lcd_write_nibble(0x20, LCD_RS_CMD);
    esp_rom_delay_us(1000);

    // Configure Screen
    lcd_write_byte(0x28, LCD_RS_CMD); // Function Set: 4-bit, 2 lines, 5x8 font
    lcd_write_byte(0x08, LCD_RS_CMD); // Display off
    
    lcd_write_byte(0x01, LCD_RS_CMD); // Clear Display
    esp_rom_delay_us(2000);           // Clear requires 2ms delay
    
    lcd_write_byte(0x06, LCD_RS_CMD); // Entry mode: increment cursor
    lcd_write_byte(0x0C, LCD_RS_CMD); // Display ON, Cursor OFF

    return ESP_OK; 
}

void lcd_display_clear(void){
     lcd_write_byte(0x01, LCD_RS_CMD);
     esp_rom_delay_us(2000);
}

void lcd_display_write_string(const char *str) {
    while (*str) {
        lcd_write_byte(*str, LCD_RS_DATA);
        str++;
    }
}

void lcd_display_set_cursor(uint8_t col, uint8_t row) {
    uint8_t row_offsets[] = {0x00, 0x40};

    if (row > 1) {
        row = 1;
    }

    lcd_write_byte(0x80 | (col + row_offsets[row]), LCD_RS_CMD);
}