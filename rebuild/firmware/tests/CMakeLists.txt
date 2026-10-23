cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/../components")
set(BB_SETUP_TEST_ONLY ON)
set(EXCLUDE_COMPONENTS wifi_manager mqtt_manager)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(bangus_buhai_sensor_tests)
