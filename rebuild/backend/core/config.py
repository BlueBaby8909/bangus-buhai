"""Authentication settings read only from process env or backend/.env."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet

AUTH_ENV = Path(__file__).resolve().parents[1] / ".env"


def values() -> dict[str, str]:
    result = {}
    if AUTH_ENV.is_file():
        for line in AUTH_ENV.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and not key.startswith("#"):
                result[key] = value
    result.update(os.environ)
    return result


@dataclass(frozen=True)
class AuthSettings:
    provider_url: str
    publishable_key: str = field(repr=False)
    token_key: bytes = field(repr=False)
    origins: tuple[str, ...]
    development: bool = False
    algorithm: str = "ES256"
    audience: str = "authenticated"

    def __post_init__(self):
        parsed = urlsplit(self.provider_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("Invalid managed authentication URL")
        if (not self.publishable_key or "YOUR-" in self.publishable_key or "YOUR-" in self.provider_url
                or not self.origins or self.algorithm not in ("ES256", "RS256")):
            raise ValueError("Missing or invalid authentication settings")
        Fernet(self.token_key)
        for origin in self.origins:
            parts = urlsplit(origin)
            if (parts.username or parts.password or not parts.hostname or parts.path
                    or parts.query or parts.fragment or parts.scheme not in ("https", "http")):
                raise ValueError("Invalid allowed origin")
            if self.development:
                if parts.hostname not in ("127.0.0.1", "localhost", "::1"):
                    raise ValueError("HTTP development is restricted to loopback origins")
            elif parts.scheme != "https":
                raise ValueError("Production requires HTTPS origins")

    @property
    def issuer(self):
        return self.provider_url.rstrip("/") + "/auth/v1"

    @property
    def cookie_name(self):
        return "bb_session_dev" if self.development else "__Host-bb_session"

    @classmethod
    def load(cls):
        data = values()
        mode = data.get("BB_AUTH_MODE", "production")
        if mode not in ("production", "development"):
            raise ValueError("Invalid authentication mode")
        return cls(
            provider_url=data.get("BB_SUPABASE_URL", ""),
            publishable_key=data.get("BB_SUPABASE_PUBLISHABLE_KEY", ""),
            token_key=data.get("BB_AUTH_TOKEN_KEY", "").encode("ascii"),
            origins=tuple(x.strip() for x in data.get("BB_AUTH_ALLOWED_ORIGINS", "").split(",") if x.strip()),
            development=mode == "development",
            algorithm=data.get("BB_AUTH_JWT_ALGORITHM", "ES256"),
        )
