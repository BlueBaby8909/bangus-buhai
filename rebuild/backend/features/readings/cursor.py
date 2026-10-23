"""Scope-bound authenticated cursors; independent of browser session lifetime."""
import base64
import hmac
import json
from datetime import datetime
from uuid import UUID

from .errors import ReadingsError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class Cursor:
    def __init__(self, key):
        self.key = hmac.digest(key, b"bb-reading-history-cursor-v1", "sha256")

    def seal(self, scope, position, last):
        payload = canonical(dict(v=1, scope=scope, position=position, last=last))
        return encode(payload) + "." + encode(hmac.digest(self.key, payload, "sha256"))

    def open(self, token, scope):
        try:
            if not isinstance(token, str) or len(token) > 4096:
                raise ValueError()
            body, signature = token.split(".")
            def decode(value):
                return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
            payload = decode(body)
            if not hmac.compare_digest(decode(signature), hmac.digest(self.key, payload, "sha256")):
                raise ValueError()
            value = json.loads(payload)
            if value["v"] != 1 or value["scope"] != scope or type(value["position"]) is not int or value["position"] < 0:
                raise ValueError()
            clock, origin, identity = value["last"]
            clock = datetime.fromisoformat(clock)
            if clock.tzinfo is None or origin not in ("manual", "device"):
                raise ValueError()
            return value["position"], (clock, origin, UUID(identity))
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError):
            raise ReadingsError(422, "invalid_cursor") from None
