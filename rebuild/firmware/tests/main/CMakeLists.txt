idf_component_register(
    SRCS "test_sensor_service.c" "test_t06.c"
    INCLUDE_DIRS "."
    REQUIRES unity sensor_service relay_control relay_driver lcd_display
)

# Replace only the acquisition and service clock calls in this test binary.
target_link_options(${COMPONENT_LIB} INTERFACE
    "-Wl,--wrap=ds18b20_sensor_init"
    "-Wl,--wrap=ds18b20_sensor_read"
    "-Wl,--wrap=turbidity_sensor_init"
    "-Wl,--wrap=turbidity_sensor_read"
    "-Wl,--wrap=sensor_service_uptime_ms"
    "-Wl,--wrap=gpio_config"
    "-Wl,--wrap=gpio_set_level"
    "-Wl,--wrap=i2c_new_master_bus"
    "-Wl,--wrap=i2c_del_master_bus"
    "-Wl,--wrap=i2c_master_bus_add_device"
    "-Wl,--wrap=i2c_master_bus_rm_device"
    "-Wl,--wrap=i2c_master_probe"
    "-Wl,--wrap=i2c_master_transmit"
)
