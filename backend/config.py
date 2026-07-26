"""
Centralized app configuration.

Values can be overridden via environment variables or a .env file placed
next to this file, e.g.:

    CORS_ORIGINS=http://localhost:5174,https://mybangusapp.com
    DATABASE_URL=sqlite:///./database/bangusbuhai.db
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BANGUS BUHAI API"
    app_version: str = "1.0.0"

    # Comma-separated list of allowed frontend origins.
    # Includes common Vite/CRA dev ports in addition to the original 5174.
    cors_origins: str = "http://localhost:5174,http://localhost:5173,http://localhost:3000"

    # Optional override; if unset, database/db.py falls back to its local sqlite file.
    database_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
