idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_event esp_netif esp_wifi nvs_flash relay_driver ds18b20_sensor turbidity_sensor lcd_display
)
