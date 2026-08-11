"""
Centralised application configuration via pydantic-settings.

All values can be overridden with environment variables or a .env file.
Example .env:

    MQTT_BROKER_HOST=192.168.1.100
    MQTT_BROKER_PORT=1883
    MQTT_USERNAME=bangus_backend
    MQTT_PASSWORD=your_secure_password
    CORS_ORIGINS=http://localhost:5173,http://localhost:5174
    DATABASE_URL=sqlite:///./database/bangusbuhai.db
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App metadata
    app_name: str    = "BANGUS BUHAI API"
    app_version: str = "1.0.0"

    # CORS — comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # Database
    database_url: str | None = None

    # MQTT Broker
    # -------------------------------------------------------------------------
    # For local development with plain Mosquitto (no TLS):
    #   MQTT_BROKER_HOST=localhost
    #   MQTT_BROKER_PORT=1883
    #   MQTT_USE_TLS=false
    #
    # For production with TLS:
    #   MQTT_BROKER_HOST=your-server.com
    #   MQTT_BROKER_PORT=8883
    #   MQTT_USE_TLS=true
    # -------------------------------------------------------------------------
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str    = ""
    mqtt_password: str    = ""
    mqtt_topic_prefix: str = "bangusbuhai"
    mqtt_use_tls: bool    = False

    # pH default (used by MQTT subscriber if device doesn't send pH)
    # Matches CONFIG_BB_PH_DEFAULT / 100.0 in firmware
    ph_default: float = 7.80

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
