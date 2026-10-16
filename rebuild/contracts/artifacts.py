"""Portable fixture catalog and deterministic JSON Schema snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from .models import MODELS, utc_datetime
from .validation import (
    ContractError, ValidationContext, classify_event, validate_acknowledgement,
    validate_command_delivery, validate_command_result, validate_message,
)

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
SCHEMAS = ROOT / "schemas"


def schema_documents() -> dict[str, str]:
    documents = {}
    for model in MODELS.values():
        schema = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:bangusbuhai:device:v1:{model.kind}"
        documents[f"{model.kind}.v1.schema.json"] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    return documents


def export_schemas() -> None:
    SCHEMAS.mkdir(exist_ok=True)
    for name, text in schema_documents().items():
        (SCHEMAS / name).write_text(text, encoding="utf-8", newline="\n")


def load_catalog() -> dict:
    return json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))


def fixture_bytes(name: str) -> bytes:
    path = (FIXTURES / name).resolve()
    if not path.is_relative_to(FIXTURES.resolve()):
        raise ValueError("Fixture path must stay inside the fixture directory")
    return path.read_bytes()


def execute_case(case: dict, default_context: dict) -> str | None:
    config = case.get("context", default_context)
    context = ValidationContext(device_id=config["device_id"],
                                binding_ids=frozenset(config["binding_ids"]),
                                prefix=config["prefix"])
    message = validate_message(case["topic"], fixture_bytes(case["file"]), context)
    operation = case["operation"]
    if operation == "message":
        return message.kind
    if operation == "delivery":
        now = None if case["now"] is None else utc_datetime(case["now"])
        validate_command_delivery(message, now=now, clock_synchronized=case["clock_synchronized"])
        return None
    reference = validate_message(case["reference_topic"], fixture_bytes(case["reference"]), context)
    if operation == "retry":
        return classify_event(message, reference)
    if operation == "result":
        validate_command_result(message, reference)
        return None
    if operation == "ack":
        validate_acknowledgement(message, reference)
        return None
    raise ValueError("Unknown fixture operation")


def fixture_failures() -> tuple[int, list[str]]:
    catalog = load_catalog()
    cases = catalog["cases"]
    failures = []
    if not cases:
        failures.append("catalog: no cases")
    identifiers = [case["id"] for case in cases]
    if len(set(identifiers)) != len(identifiers):
        failures.append("catalog: duplicate case IDs")
    for case in cases:
        expected = case.get("expected_error")
        try:
            result = execute_case(case, catalog["context"])
        except ContractError as error:
            if error.code != expected:
                failures.append(f"{case['id']}: expected {expected or 'success'}, got {error.code}")
        else:
            if expected is not None:
                failures.append(f"{case['id']}: expected {expected}, got success")
            elif result != case.get("expected_result"):
                failures.append(f"{case['id']}: unexpected result")
    return len(cases), failures


def check_artifacts() -> tuple[int, list[str]]:
    count, failures = fixture_failures()
    expected = schema_documents()
    actual_names = {path.name for path in SCHEMAS.glob("*.json")}
    if actual_names != set(expected):
        failures.append("schemas: missing or unexpected snapshot files")
    for name, text in expected.items():
        path = SCHEMAS / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            failures.append(f"schemas: stale snapshot {name}")
    return count, failures
