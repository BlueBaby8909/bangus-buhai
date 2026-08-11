# Bangus Buhai Firmware

## Wi-Fi Provisioning

This firmware uses **ESP-IDF Network Provisioning** to securely connect the device to your local Wi-Fi network.

### Provisioning via BLE

For the prototype, we use **BLE Provisioning** (`network_prov_scheme_ble`) for provisioning to allow easy testing.

#### Steps to Provision:
1. Download the **ESP BLE Provisioning** app on your iOS or Android smartphone.
2. Power on the device. If it has no saved Wi-Fi credentials, the LCD will display "Connecting WiFi / Please wait...".
3. Open the ESP BLE Provisioning app and scan for devices (it should appear as `BB-SETUP-XXXXXX`).
4. Follow the prompts to provision the device. The Proof of Possession (PoP) is the last 8 characters of the device's MAC address.
5. Provide your local Wi-Fi SSID and password through the app.
6. The device will connect to your Wi-Fi, store the credentials in its NVS flash memory, and begin publishing telemetry to the MQTT broker.

If you ever need to reset the credentials, you can erase the NVS flash using:
```bash
idf.py erase-flash
```
