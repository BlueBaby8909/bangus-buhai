#pragma once

#include "esp_err.h"

esp_err_t lcd_display_init(void);
void lcd_display_clear(void);
void lcd_display_set_cursor(uint8_t col, uint8_t row);
void lcd_display_write_string(const char *str);