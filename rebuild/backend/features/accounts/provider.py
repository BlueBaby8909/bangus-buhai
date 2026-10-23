"""Bounded, stateless Supabase REST adapter; provider tokens never reach browsers."""
import json
import threading
import time
from dataclasses import dataclass, field
from uuid import UUID

import httpx
import jwt

from backend.core.config import AuthSettings
from .errors import AuthError


@dataclass(repr=False)
class TokenBundle:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    claims: dict = field(repr=False)


class SupabaseProvider:
    def __init__(self, settings: AuthSettings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(timeout=5, follow_redirects=False)
        self.owns_client = client is None
        self._keys = {}
        self._cached_at = float("-inf")
        self._fetched_at = float("-inf")
        self._lock = threading.Lock()

    def close(self):
        if self.owns_client:
            self.client.close()

    def _request(self, method, suffix, *, body=None, access=None):
        headers = {"apikey": self.settings.publishable_key, "Accept": "application/json"}
        if access:
            headers["Authorization"] = "Bearer " + access
        try:
            with self.client.stream(method, self.settings.issuer + suffix, headers=headers,
                                    json=body, timeout=5, follow_redirects=False) as response:
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "60")
                    raise AuthError(429, "authentication_throttled", min(60, max(1, int(retry))) if retry.isdigit() else 60)
                if response.status_code in (400, 401, 403):
                    if suffix.startswith("/.well-known/"):
                        raise AuthError(503, "authentication_unavailable")
                    raise AuthError(401, "authentication_failed")
                if not 200 <= response.status_code < 300:
                    raise AuthError(503, "authentication_unavailable")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 65536:
                        raise AuthError(503, "authentication_unavailable")
                return json.loads(raw) if raw else {}
        except (httpx.HTTPError, ValueError, UnicodeError):
            raise AuthError(503, "authentication_unavailable") from None

    def _key(self, kid):
        with self._lock:
            clock = time.monotonic()
            expired = clock - self._cached_at >= 300
            if expired or (kid not in self._keys and clock - self._fetched_at >= 5):
                self._fetched_at = clock
                document = self._request("GET", "/.well-known/jwks.json")
                if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
                    raise AuthError(503, "authentication_unavailable")
                keys = {}
                try:
                    for key in document["keys"][:20]:
                        if key.get("alg") == self.settings.algorithm and key.get("use", "sig") == "sig":
                            keys[key["kid"]] = jwt.PyJWK.from_dict(key, algorithm=self.settings.algorithm).key
                except (ValueError, KeyError, TypeError, AttributeError, jwt.PyJWTError):
                    raise AuthError(503, "authentication_unavailable") from None
                self._keys, self._cached_at = keys, clock
            if kid not in self._keys:
                raise AuthError(401, "invalid_token")
            return self._keys[kid]

    def verify(self, token, *, subject=None, session_id=None):
        try:
            if not isinstance(token, str) or len(token) > 16384:
                raise ValueError()
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self.settings.algorithm or not isinstance(header.get("kid"), str) or len(header["kid"]) > 128:
                raise ValueError()
            claims = jwt.decode(token, self._key(header["kid"]), algorithms=[self.settings.algorithm],
                issuer=self.settings.issuer, audience=self.settings.audience,
                options={"require": ["iss", "aud", "sub", "exp", "iat", "session_id"]})
            if claims["aud"] != self.settings.audience or any(type(claims[x]) is not int for x in ("iat", "exp")):
                raise ValueError()
            if not 0 < claims["exp"] - claims["iat"] <= 900:
                raise ValueError()
            for name in ("sub", "session_id"):
                if str(UUID(claims[name])) != claims[name]:
                    raise ValueError()
            if subject is not None and claims["sub"] != str(subject):
                raise ValueError()
            if session_id is not None and claims["session_id"] != str(session_id):
                raise ValueError()
            return claims
        except jwt.ExpiredSignatureError:
            raise AuthError(401, "access_expired") from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
            raise AuthError(401, "invalid_token") from None

    def _tokens(self, response, *, subject=None, session_id=None):
        if not isinstance(response, dict) or any(not isinstance(response.get(k), str) or not 1 <= len(response[k]) <= 16384
                                                for k in ("access_token", "refresh_token")):
            raise AuthError(503, "authentication_unavailable")
        claims = self.verify(response["access_token"], subject=subject, session_id=session_id)
        return TokenBundle(response["access_token"], response["refresh_token"], claims)

    def sign_in(self, email, password):
        return self._tokens(self._request("POST", "/token?grant_type=password", body={"email": email, "password": password}))

    def refresh(self, refresh_token, subject, session_id):
        return self._tokens(self._request("POST", "/token?grant_type=refresh_token", body={"refresh_token": refresh_token}),
                            subject=subject, session_id=session_id)

    def sign_out(self, access):
        self._request("POST", "/logout?scope=local", access=access)
