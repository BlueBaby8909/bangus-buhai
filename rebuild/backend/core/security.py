"""Opaque session identifiers and session-bound CSRF; no credentials in logs."""
import hashlib
import hmac
import secrets


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def csrf_token(token: str) -> str:
    return hmac.new(token.encode("ascii"), b"bangus-buhai-csrf-v1", hashlib.sha256).hexdigest()


def valid_token(token: str | None) -> bool:
    return isinstance(token, str) and len(token) == 43 and all(c.isascii() and (c.isalnum() or c in "-_") for c in token)
