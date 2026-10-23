import unittest
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from backend.features.readings.cursor import Cursor
from backend.features.readings.errors import ReadingsError
from backend.features.readings.schemas import CreateMeasurement, RevisionAction


class ReadingUnitTests(unittest.TestCase):
    def test_strict_measurement_and_explicit_timezone(self):
        valid = dict(request_id=str(uuid4()), measured_at="2026-10-21T08:00:00+08:00", ph=7)
        reading = CreateMeasurement.model_validate(valid)
        self.assertEqual(reading.measured_at.hour, 0)
        for changes in ({"ph": True}, {"ph": "7"}, {"ph": float("nan")}, {"ph": float("inf")},
                        {"ph": -float("inf")}, {"ph": None}, {"source": "estimated"},
                        {"measured_at": "2026-10-21T08:00:00"}, {"measured_at": 123456789},
                        {"measured_at": "123456789"}, {"measured_at": "20261021"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                CreateMeasurement.model_validate(valid | changes)

    def test_revision_reason_and_version(self):
        self.assertEqual(RevisionAction(expected_version=1, reason="  typo  ").reason, "typo")
        for body in ({"expected_version": True, "reason": "typo"}, {"expected_version": 1, "reason": "  "},
                     {"expected_version": 0, "reason": "typo"}, {"expected_version": 1, "reason": "a" * 501}):
            with self.assertRaises(ValidationError):
                RevisionAction.model_validate(body)

    def test_cursor_authentication_scope_and_restart(self):
        key = bytes(range(32))
        scope = {"tank": str(uuid4()), "time_basis": "measured"}
        boundary = [datetime.now(timezone.utc).isoformat(), "manual", str(uuid4())]
        token = Cursor(key).seal(scope, 8, boundary)
        self.assertEqual(Cursor(key).open(token, scope)[0], 8)
        for cursor, owner, secret in ((token[:-4] + "AAAA", scope, key), (token, scope | {"tank": "other"}, key),
                                     (token, scope, b"wrong"), ("bad", scope, key), ("a" * 4097, scope, key)):
            with self.assertRaises(ReadingsError):
                Cursor(secret).open(cursor, owner)


if __name__ == "__main__":
    unittest.main()
