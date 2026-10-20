#include "turbidity_sensor.h"
#include "sdkconfig.h"

#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"

static const char *TAG = "TURBIDITY_SENSOR";

static adc_oneshot_unit_handle_t s_adc_handle = NULL;
static adc_cali_handle_t s_cali_handle = NULL;
static adc_channel_t s_channel;

esp_err_t turbidity_sensor_init(void)
{
    if (s_adc_handle != NULL && s_cali_handle != NULL) {
        return ESP_OK;
    }

    adc_unit_t unit;
    adc_channel_t channel;
    adc_oneshot_unit_handle_t adc = NULL;
    adc_cali_handle_t calibration = NULL;

    esp_err_t ret = adc_oneshot_io_to_channel(
        CONFIG_BB_GPIO_TURBIDITY, &unit, &channel
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Invalid ADC GPIO: %s", esp_err_to_name(ret));
        return ret;
    }

    adc_oneshot_unit_init_cfg_t unit_config = {
        .unit_id = unit,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };

    ret = adc_oneshot_new_unit(&unit_config, &adc);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "ADC initialization failed: %s",
                 esp_err_to_name(ret));
        return ret;
    }

    adc_oneshot_chan_cfg_t channel_config = {
        .bitwidth = ADC_BITWIDTH_12,
        .atten = ADC_ATTEN_DB_12,
    };

    ret = adc_oneshot_config_channel(adc, channel, &channel_config);
    if (ret != ESP_OK) {
        goto cleanup;
    }

    adc_cali_curve_fitting_config_t calibration_config = {
        .unit_id = unit,
        .chan = channel,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };

    ret = adc_cali_create_scheme_curve_fitting(
        &calibration_config, &calibration
    );
    if (ret != ESP_OK) {
        goto cleanup;
    }

    s_adc_handle = adc;
    s_cali_handle = calibration;
    s_channel = channel;

    ESP_LOGI(TAG, "Initialized on GPIO %d", CONFIG_BB_GPIO_TURBIDITY);
    return ESP_OK;

cleanup:
    ESP_LOGE(TAG, "Initialization failed: %s", esp_err_to_name(ret));

    esp_err_t cleanup_ret = adc_oneshot_del_unit(adc);
    if (cleanup_ret != ESP_OK) {
        ESP_LOGW(TAG, "ADC cleanup failed: %s",
                 esp_err_to_name(cleanup_ret));
    }

    return ret;
}

esp_err_t turbidity_sensor_read(int *out_voltage_mv)
{
    if (out_voltage_mv == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    if (s_adc_handle == NULL || s_cali_handle == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    int raw_value;
    esp_err_t ret = adc_oneshot_read(
        s_adc_handle, s_channel, &raw_value
    );
    if (ret != ESP_OK) {
        return ret;
    }

    int voltage_mv;
    ret = adc_cali_raw_to_voltage(
        s_cali_handle, raw_value, &voltage_mv
    );
    if (ret != ESP_OK) {
        return ret;
    }

    *out_voltage_mv = voltage_mv;
    return ESP_OK;
}