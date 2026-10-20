#pragma once

#include "esp_err.h"
#include "relay_control.h"

#define LCD_COLUMNS 16
typedef struct { char rows[2][LCD_COLUMNS + 1]; } lcd_frame_t;

/* One display-task owner. Cache is valid only after successful full row writes. */
esp_err_t lcd_display_init(void);
esp_err_t lcd_display_write_frame(const lcd_frame_t *frame);

/* Pure page formatting. No GPIO, I2C or sensor acquisition. */
esp_err_t lcd_display_format(const sensor_reading_t *reading,
                             const relay_control_state_t *relay,
                             int64_t now_ms, lcd_frame_t *out);
