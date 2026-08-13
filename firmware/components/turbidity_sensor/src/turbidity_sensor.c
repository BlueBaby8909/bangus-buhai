#include "turbidity_sensor.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "esp_adc/adc_oneshot.h"
#include "hal/adc_types.h"

#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"

static const char *TAG = "TURBIDITY_SENSOR";

static adc_oneshot_unit_handle_t s_adc_handle = NULL;
static adc_cali_handle_t s_cali_handle = NULL;
static adc_channel_t s_channel;

esp_err_t turbidity_sensor_init(void)
{
    ESP_LOGI(TAG, "Initializing Turbidity Sensor on GPIO %d", CONFIG_BB_GPIO_TURBIDITY);

    adc_unit_t unit;
    ESP_ERROR_CHECK(adc_oneshot_io_to_channel(CONFIG_BB_GPIO_TURBIDITY, &unit, &s_channel));

    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = unit,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config, &s_adc_handle));

    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_12,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(s_adc_handle, s_channel, &config));

    adc_cali_curve_fitting_config_t cali_config = {
        .unit_id = unit,
        .chan = s_channel,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_ERROR_CHECK(adc_cali_create_scheme_curve_fitting(&cali_config, &s_cali_handle));

    ESP_LOGI(TAG, "Turbidity Sensor initialized successfully");
    return ESP_OK;
}

esp_err_t turbidity_sensor_read(int *out_voltage)
{
    if (s_adc_handle == NULL || s_cali_handle == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    int raw_val = 0;

    esp_err_t ret = adc_oneshot_read(s_adc_handle, s_channel, &raw_val);
    if (ret != ESP_OK) {
        return ret;
    }
    
    ret = adc_cali_raw_to_voltage(s_cali_handle, raw_val, out_voltage);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Diagnostic - ADC Raw: %d | Voltage: %d mV", raw_val, *out_voltage);
    }
    
    return ret;
}
