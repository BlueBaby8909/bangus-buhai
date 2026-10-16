"""Wire, context and artifact regressions; no application or transport required."""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from pydantic import ValidationError

from contracts import (
    ContractError, ValidationContext, classify_event, decode_payload,
    validate_acknowledgement, validate_command_delivery, validate_command_result,
    validate_message,
)
from contracts.__main__ import main
from contracts.artifacts import (
    FIXTURES, SCHEMAS, check_artifacts, execute_case, fixture_bytes, load_catalog,
    schema_documents,
)
from contracts.models import MAX_SAFE_INTEGER, utc_datetime

DEVICE = "BB-AABBCC112233"
BINDING = "97fcde45-4112-41d4-a509-17e5bb1c0d91"
OTHER_UUID = "ffffffff-ffff-4fff-8fff-ffffffffffff"
CONTEXT = ValidationContext(DEVICE, frozenset({BINDING}))


def topic(suffix):
    return f"bangusbuhai-rebuild/devices/{DEVICE}/{suffix}"


def document(name="telemetry-default-ph"):
    return json.loads(fixture_bytes(f"valid/{name}.json"))


def validate(data, suffix="telemetry", context=CONTEXT):
    return validate_message(topic(suffix), json.dumps(data, ensure_ascii=False).encode("utf-8"), context)


class ContractTest(unittest.TestCase):
    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception


class FixtureTests(ContractTest):
    def test_every_declared_fixture(self):
        catalog = load_catalog()
        for case in catalog["cases"]:
            with self.subTest(case=case["id"]):
                if "expected_error" in case:
                    self.error(case["expected_error"], execute_case, case, catalog["context"])
                else:
                    self.assertEqual(execute_case(case, catalog["context"]), case.get("expected_result"))

    def test_catalog_has_unique_ids_and_no_unreferenced_payloads(self):
        cases = load_catalog()["cases"]
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        referenced = {case[key] for case in cases for key in ("file", "reference") if key in case}
        actual = {path.relative_to(FIXTURES).as_posix() for path in FIXTURES.rglob("*")
                  if path.is_file() and path.name != "catalog.json"}
        self.assertEqual(actual, referenced)

    def test_fixture_paths_cannot_escape(self):
        with self.assertRaises(ValueError):
            fixture_bytes("../README.md")


class ParsingTests(ContractTest):
    def test_payload_must_be_bytes(self):
        for value in ("{}", bytearray(b"{}"), None, 0):
            with self.subTest(value=type(value).__name__):
                self.error("invalid_payload", decode_payload, value)

    def test_depth_limit_is_inclusive_and_counts_arrays(self):
        self.assertIsInstance(decode_payload(b'{"x":'*8 + b"0" + b"}"*8), dict)
        self.error("nesting_too_deep", decode_payload, b'{"x":' + b"["*8 + b"0" + b"]"*8 + b"}")

    def test_brackets_and_escaped_quotes_inside_strings_do_not_count(self):
        data = {"text": '[[[{{{ \\" a quote " then a backslash \\'}
        self.assertEqual(decode_payload(json.dumps(data).encode()), data)

    def test_nested_and_escaped_duplicate_keys(self):
        for raw in (b'{"x":{"v":1,"v":2}}', b'{"x":1,"\\u0078":2}'):
            with self.subTest(raw=raw):
                self.error("duplicate_key", decode_payload, raw)

    def test_malformed_unicode_syntax_and_nonobject_roots(self):
        for raw in (b"", b"{", b"}", b'{"x":1,}', b'\xef\xbb\xbf{}', b'{"x":"\xff"}',
                    b'{"x":"\\ud800"}', b'{"\\udfff":0}'):
            with self.subTest(raw=raw):
                self.error("invalid_json", decode_payload, raw)
        for raw in (b"null", b"[]", b"true", b"1", b'"text"'):
            with self.subTest(raw=raw):
                self.error("invalid_schema", decode_payload, raw)

    def test_nonfinite_overflow_underflow_and_real_zero(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999", "1e-9999"):
            with self.subTest(token=token):
                self.error("invalid_number", decode_payload, ('{"x":'+token+'}').encode())
        self.assertEqual(decode_payload(b'{"x":-0e-9999}'), {"x": -0.0})

    def test_extremely_long_exponents_cannot_escape_contract_errors(self):
        exponent = "9"*1000
        for token in ("1e-"+exponent, "1e"+exponent, "-1e-"+exponent):
            with self.subTest(token_prefix=token[:4]):
                self.error("invalid_number", decode_payload, ('{"x":'+token+'}').encode())
        self.assertEqual(decode_payload(('{"x":0e-'+exponent+'}').encode()), {"x": 0.0})

    def test_utf8_byte_limit_not_character_limit(self):
        data = document()
        data["fw_version"] = "é"*64
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        raw += b" "*(4096-len(raw))
        self.assertEqual(len(raw), 4096)
        self.assertEqual(validate_message(topic("telemetry"), raw, CONTEXT).fw_version, "é"*64)
        self.error("payload_too_large", validate_message, topic("telemetry"), raw+b" ", CONTEXT)

    def test_schema_version_is_strict_integer_one(self):
        for version in (True, False, 1.0, "1", 0, 2, None):
            data = document()
            data["schema_version"] = version
            with self.subTest(version=version):
                self.error("unsupported_version", validate, data)

    def test_errors_are_bounded_and_do_not_echo_values(self):
        data = document()
        data["secret\n" + "x"*300] = "NEVER-ECHO-THIS-VALUE"
        error = self.error("invalid_schema", validate, data)
        self.assertLessEqual(len(error.field_path), 128)
        self.assertNotIn("\n", error.field_path)
        self.assertNotIn("NEVER-ECHO", str(error))
        self.assertEqual(set(error.as_dict()), {"code", "field_path"})


class ReadingTests(ContractTest):
    def test_unknown_age_is_preserved_as_unverified_without_zero_substitution(self):
        data = document("telemetry-unknown-sample-age")
        reading = validate(data).readings.temperature
        self.assertEqual(reading.value, 28.0)
        self.assertIsNone(reading.sample_age_ms)
        self.assertEqual(reading.validity, "unverified")
        data["readings"]["temperature"]["validity"] = "stale"
        self.error("invalid_schema", validate, data)

    def test_sensor_validity_does_not_imply_clock_synchronization(self):
        event = validate(document("telemetry-unsynchronized-clock"))
        self.assertIsNone(event.measured_at)
        self.assertEqual(event.readings.temperature.validity, "valid")

    def test_default_ph_is_not_a_sensor_observation(self):
        reading = validate(document()).readings.ph
        self.assertEqual((reading.source, reading.validity), ("default", "unverified"))
        self.assertIsNone(reading.sample_age_ms)
        self.assertIsNone(reading.last_valid_age_ms)

    def test_invalid_and_missing_values_remain_null(self):
        event = validate(document("telemetry-failed-sensor"))
        self.assertIsNone(event.readings.temperature.value)
        event = validate(document("telemetry-missing-sensor"))
        self.assertIsNone(event.readings.turbidity.value)

    def test_valid_temperature_age_boundary(self):
        for age in (0, 59999, 60000):
            data = document()
            data["readings"]["temperature"].update(sample_age_ms=age, last_valid_age_ms=age)
            with self.subTest(age=age):
                if age == 60000:
                    self.error("invalid_schema", validate, data)
                else:
                    self.assertEqual(validate(data).readings.temperature.sample_age_ms, age)

    def test_all_ages_are_bounded_by_capture_uptime(self):
        for metric in ("temperature", "turbidity", "ph"):
            data = document("telemetry-sensor-ph")
            reading = data["readings"][metric]
            reading.update(validity="unverified", sample_age_ms=300001, last_valid_age_ms=None)
            with self.subTest(metric=metric):
                self.error("invalid_schema", validate, data)

    def test_valid_sample_and_last_valid_ages_agree(self):
        data = document()
        data["readings"]["temperature"]["last_valid_age_ms"] = 999
        self.error("invalid_schema", validate, data)

    def test_numeric_measurements_accept_integers_but_not_boolean_or_text(self):
        data = document()
        data["readings"]["temperature"]["value"] = 0
        self.assertEqual(validate(data).readings.temperature.value, 0.0)
        for value in (False, "0", {}, [], None):
            data["readings"]["temperature"]["value"] = value
            with self.subTest(value=value):
                self.error("invalid_schema", validate, data)

    def test_no_biological_or_calibration_range_is_invented(self):
        data = document()
        data["readings"]["temperature"]["value"] = -100.0
        self.assertEqual(validate(data).readings.temperature.value, -100.0)

    def test_safe_integer_and_uint32_boundaries(self):
        data = document()
        data.update(capture_uptime_ms=MAX_SAFE_INTEGER, seq=2**32-1)
        data["diagnostics"].update(queue_dropped=2**32-1, reconnects=2**32-1)
        self.assertEqual(validate(data).seq, 2**32-1)
        for value in (-1, MAX_SAFE_INTEGER+1, True, 1000.0, "1000"):
            data["capture_uptime_ms"] = value
            with self.subTest(value=value):
                self.error("invalid_schema", validate, data)

    def test_models_are_immutable(self):
        event = validate(document())
        with self.assertRaises(ValidationError):
            event.seq = 42
        with self.assertRaises(ValidationError):
            event.readings.temperature.value = 0

    def test_string_and_reason_boundaries(self):
        data = document()
        data["fw_version"] = "x"*64
        data["relay"]["reason"] = "a"*64
        validate(data)
        for value in ("", "x"*65, "HasCaps", "has space", "startup\n"):
            data["relay"]["reason"] = value
            with self.subTest(value=value):
                self.error("invalid_schema", validate, data)


class ContextAndCorrelationTests(ContractTest):
    def test_context_is_explicit_and_immutable(self):
        for kwargs in ({"device_id": DEVICE.lower()}, {"device_id": DEVICE, "prefix": "bad/#"},
                       {"device_id": DEVICE, "binding_ids": {BINDING}},
                       {"device_id": DEVICE, "binding_ids": frozenset({"bad"})}):
            with self.subTest(kwargs=kwargs):
                self.error("invalid_context", ValidationContext, **kwargs)
        self.error("invalid_context", validate_message, topic("telemetry"), b"{}", None)

    def test_status_and_ack_do_not_claim_a_binding(self):
        context = ValidationContext(DEVICE)
        self.assertEqual(validate(document("status-online"), "status", context).kind, "status")
        self.assertEqual(validate(document("ack-stored-telemetry"), "acks", context).kind, "ack")
        self.error("binding_mismatch", validate, document(), context=context)

    def test_wrong_suffix_cannot_select_another_model(self):
        self.error("invalid_schema", validate, document(), "cmd")
        for wire_topic in (topic("telemetry")+"/", topic("+"), "bad", topic("telemetry").replace(DEVICE, "+")):
            with self.subTest(topic=wire_topic):
                self.error("invalid_topic", validate_message, wire_topic, fixture_bytes("valid/telemetry-default-ph.json"), CONTEXT)

    def test_different_configured_prefix_is_supported_without_network(self):
        context = ValidationContext(DEVICE, frozenset({BINDING}), "isolated-test")
        event = validate_message(topic("telemetry").replace("bangusbuhai-rebuild", context.prefix),
                                 fixture_bytes("valid/telemetry-default-ph.json"), context)
        self.assertEqual(event.device_id, DEVICE)

    def test_new_duplicate_and_conflicting_events(self):
        event = validate(document())
        self.assertEqual(classify_event(event, None), "new")
        self.assertEqual(classify_event(event, event), "duplicate")
        for field in ("device_id", "boot_id", "seq"):
            data = document()
            if field == "device_id":
                data[field] = "BB-112233445566"
                other = validate_message(topic("telemetry").replace(DEVICE, data[field]),
                                         json.dumps(data).encode(), ValidationContext(data[field], frozenset({BINDING})))
            else:
                data[field] = OTHER_UUID if field == "boot_id" else 6
                other = validate(data)
            with self.subTest(identity_field=field):
                self.assertEqual(classify_event(other, event), "new")
        changed = document()
        changed["readings"]["ph"]["value"] = 7.1
        self.error("event_conflict", classify_event, validate(changed), event)

    def test_delivery_clock_and_inclusive_exclusive_boundaries(self):
        command = validate(document("command-relay-on"), "cmd")
        issue = utc_datetime(command.issued_at)
        validate_command_delivery(command, now=issue, clock_synchronized=True)
        validate_command_delivery(command, now=issue.astimezone(timezone(timedelta(hours=8))), clock_synchronized=True)
        self.error("command_expired", validate_command_delivery, command,
                   now=utc_datetime(command.expires_at), clock_synchronized=True)
        self.error("invalid_context", validate_command_delivery, command,
                   now=datetime(2026, 10, 16), clock_synchronized=True)
        self.error("clock_unsynchronized", validate_command_delivery, command, now=None, clock_synchronized=False)

    def test_results_match_all_identity_fields(self):
        command = validate(document("command-relay-on"), "cmd")
        result = validate(document("result-applied"), "command-results")
        validate_command_result(result, command)
        for field, value in (("device_id", "BB-112233445566"), ("binding_id", OTHER_UUID), ("command_id", OTHER_UUID)):
            data = document("command-relay-on")
            data[field] = value
            other = type(command).model_validate(data)
            with self.subTest(field=field):
                self.error("correlation_mismatch", validate_command_result, result, other)

    def test_ack_matches_device_boot_sequence_and_kind(self):
        event = validate(document())
        ack = validate(document("ack-stored-telemetry"), "acks")
        for field, value in (("device_id", "BB-112233445566"), ("boot_id", OTHER_UUID),
                             ("seq", 8), ("event_kind", "command_result")):
            data = document("ack-stored-telemetry")
            data[field] = value
            other = type(ack).model_validate(data)
            with self.subTest(field=field):
                self.error("correlation_mismatch", validate_acknowledgement, other, event)

    def test_helpers_reject_wrong_message_kinds(self):
        event = validate(document())
        command = validate(document("command-relay-on"), "cmd")
        self.error("invalid_context", classify_event, command, event)
        self.error("invalid_context", validate_command_result, event, command)
        self.error("invalid_context", validate_acknowledgement, event, event)

    def test_timestamps_reject_impossible_or_noncanonical_values(self):
        for value in ("2026-02-30T03:00:00Z", "2026-10-16T03:00:00+00:00", "0000-01-01T00:00:00Z",
                      "2026-10-16T03:00:00.1234567Z", "2026-10-16T03:00:00Z\n"):
            data = document("command-relay-on")
            data["issued_at"] = value
            with self.subTest(value=value):
                self.error("invalid_schema", validate, data, "cmd")


class ArtifactTests(ContractTest):
    def test_exported_schemas_match_models_and_are_closed_objects(self):
        generated = schema_documents()
        self.assertEqual(len(generated), 5)
        for name, text in generated.items():
            with self.subTest(name=name):
                self.assertEqual((SCHEMAS / name).read_text(encoding="utf-8"), text)
                schema = json.loads(text)
                self.assertFalse(schema["additionalProperties"])
                self.assertTrue(schema["$id"].startswith("urn:bangusbuhai:device:v1:"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_check_is_offline_and_does_not_write_artifacts(self):
        paths = [path for directory in (FIXTURES, SCHEMAS) for path in directory.rglob("*") if path.is_file()]
        before = {path: path.read_bytes() for path in paths}
        with patch("socket.socket", side_effect=AssertionError("Unexpected network access")):
            count, failures = check_artifacts()
        self.assertGreater(count, 0)
        self.assertEqual(failures, [])
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.assertNotIn("fastapi", sys.modules)
        self.assertNotIn("uvicorn", sys.modules)
        self.assertNotIn("main", sys.modules)

    def test_stale_snapshot_is_detected_without_regeneration(self):
        generated = schema_documents()
        first = next(iter(generated))
        original = (SCHEMAS / first).read_bytes()
        generated[first] += " "
        with patch("contracts.artifacts.schema_documents", return_value=generated):
            _, failures = check_artifacts()
        self.assertIn(f"schemas: stale snapshot {first}", failures)
        self.assertEqual((SCHEMAS / first).read_bytes(), original)

    def test_empty_or_duplicate_catalog_cannot_report_success(self):
        catalog = load_catalog()
        with patch("contracts.artifacts.load_catalog", return_value={**catalog, "cases": []}):
            _, failures = check_artifacts()
        self.assertIn("catalog: no cases", failures)
        with patch("contracts.artifacts.load_catalog", return_value={**catalog, "cases": [catalog["cases"][0]]*2}):
            _, failures = check_artifacts()
        self.assertIn("catalog: duplicate case IDs", failures)

    def test_cli_check_success_and_failure_exit_codes(self):
        output = io.StringIO()
        with patch("sys.argv", ["contracts", "check"]), redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("PASS:", output.getvalue())
        with patch("sys.argv", ["contracts", "check"]), redirect_stderr(io.StringIO()):
            with patch("contracts.__main__.check_artifacts", return_value=(1, ["fixture failure"])):
                self.assertEqual(main(), 1)
            with patch("contracts.__main__.check_artifacts", side_effect=OSError("unreadable")):
                self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
