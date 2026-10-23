"""Authenticated, opaque tank cursors; independent of history pagination tokens."""
import base64
import hashlib
import hmac
import json


class InvalidStreamCursor(ValueError):
    pass


class StreamCursor:
    def __init__(self, key):
        self.key = hmac.digest(key, b"bb-tank-stream-cursor-v1", hashlib.sha256)

    def seal(self, hatchery_id, tank_id, position):
        payload = json.dumps(dict(v=1, hatchery=str(hatchery_id),
            tank=str(tank_id), position=position), separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(payload + hmac.digest(self.key, payload, hashlib.sha256)).decode()

    def open(self, value, hatchery_id, tank_id):
        try:
            if not isinstance(value, str) or not 1 <= len(value) <= 2048:
                raise ValueError()
            raw = base64.b64decode(value.encode(), altchars=b"-_", validate=True)
            payload, signature = raw[:-32], raw[-32:]
            if not hmac.compare_digest(signature, hmac.digest(self.key, payload, hashlib.sha256)):
                raise ValueError()
            data = json.loads(payload)
            if (set(data) != {"v", "hatchery", "tank", "position"} or data["v"] != 1
                or data["hatchery"] != str(hatchery_id) or data["tank"] != str(tank_id)
                or type(data["position"]) is not int or not 0 <= data["position"] <= 2**63 - 1):
                raise ValueError()
            return data["position"]
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise InvalidStreamCursor("invalid_stream_cursor") from None
