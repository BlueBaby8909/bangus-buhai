# Bangus Buhai Mosquitto Setup

This directory contains the configuration for a production-ready Mosquitto MQTT broker.

## Local Development (No TLS)
For local development, you can run Mosquitto without TLS. The backend and the firmware must be configured to connect to `mqtt://` on port 1883 instead of `mqtts://` on port 8883.

1. Generate a password file (requires `mosquitto_passwd` tool installed locally):
   ```bash
   mkdir -p config
   mosquitto_passwd -c config/passwd bangus_device
   # Enter password when prompted. Remember to update firmware Kconfig and backend .env
   ```
2. Start Mosquitto using Docker:
   ```bash
   docker-compose up -d
   ```

## Production (TLS Enabled)
For production, the ESP32 firmware communicates over the internet, so TLS is required to prevent eavesdropping and man-in-the-middle attacks.

1. Obtain SSL certificates (e.g. from Let's Encrypt using Certbot) for your broker's domain name (e.g. `mqtt.your-server.com`).
2. Copy the certificates into `mosquitto/config/certs/`:
   - `ca.crt` (Root CA)
   - `server.crt` (Certificate)
   - `server.key` (Private Key)
3. Copy the `ca.crt` file into the firmware codebase at `firmware/components/telemetry_service/certs/mosquitto_ca.crt`. This is required for the ESP32 to verify the broker.
4. Uncomment the TLS listener settings (port 8883) in `mosquitto.conf`.
5. Restart Mosquitto:
   ```bash
   docker-compose restart
   ```
