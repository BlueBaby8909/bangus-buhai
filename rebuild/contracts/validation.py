"""Bounded wire parsing and pure checks against explicitly supplied context."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import ValidationError

from .models import (
    DEFAULT_PREFIX, DEVICE_PATTERN, MAX_DEPTH, MAX_PAYLOAD_BYTES, MODELS,
    UUID_PATTERN, Acknowledgement, CommandResult, Event, Message, RelayCommand,
    Telemetry, utc_datetime,
)


class ContractError(ValueError):
    """Stable code and bounded path only: never expose input values or JSON."""

    def __init__(self, code: str, field_path: str = "$") -> None:
        self.code = code
        self.field_path = re.sub(r"[^A-Za-z0-9_.$\[\]-]", "_", field_path)[:128]
        super().__init__(f"{self.code}: {self.field_path}")

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field_path": self.field_path}


@dataclass(frozen=True)
class ValidationContext:
    device_id: str
    binding_ids: frozenset[str] = frozenset()
    prefix: str = DEFAULT_PREFIX

    def __post_init__(self) -> None:
        if type(self.device_id) is not str or re.fullmatch(DEVICE_PATTERN, self.device_id) is None:
            raise ContractError("invalid_context", "$.device_id")
        if type(self.prefix) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.prefix) is None:
            raise ContractError("invalid_context", "$.prefix")
        if type(self.binding_ids) is not frozenset or any(
            type(binding) is not str or re.fullmatch(UUID_PATTERN, binding) is None
            for binding in self.binding_ids
        ):
            raise ContractError("invalid_context", "$.binding_ids")


def _check_depth(text: str) -> None:
    depth = 0
    in_string = escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "{[":
            depth += 1
            if depth > MAX_DEPTH:
                raise ContractError("nesting_too_deep")
        elif character in "}]":
            depth -= 1
            if depth < 0:
                raise ContractError("invalid_json")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise ContractError("invalid_number")


def _float(token: str) -> float:
    value = float(token)
    # Inspect the mantissa rather than constructing an unbounded Decimal exponent.
    nonzero_mantissa = any(character in "123456789" for character in token.lower().split("e", 1)[0])
    if not math.isfinite(value) or (value == 0 and nonzero_mantissa):
        raise ContractError("invalid_number")
    return value


def decode_payload(payload: bytes) -> dict:
    """Decode before validation so duplicate keys cannot silently disappear."""
    if type(payload) is not bytes:
        raise ContractError("invalid_payload")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ContractError("payload_too_large")
    try:
        text = payload.decode("utf-8", errors="strict")
        _check_depth(text)
        document = json.loads(text, object_pairs_hook=_unique_object,
                              parse_constant=_constant, parse_float=_float)
        # Escaped lone surrogates parse in Python but cannot form UTF-8 JSON.
        json.dumps(document, ensure_ascii=False).encode("utf-8")
    except ContractError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise ContractError("invalid_json") from None
    if type(document) is not dict:
        raise ContractError("invalid_schema")
    return document


def validate_message(topic: str, payload: bytes, context: ValidationContext) -> Message:
    if not isinstance(context, ValidationContext):
        raise ContractError("invalid_context")
    document = decode_payload(payload)
    if "schema_version" in document and (
        type(document["schema_version"]) is not int or document["schema_version"] != 1
    ):
        raise ContractError("unsupported_version", "$.schema_version")
    if type(topic) is not str or len(topic) > 256:
        raise ContractError("invalid_topic")
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != context.prefix or parts[1] != "devices":
        raise ContractError("invalid_topic")
    device_id, suffix = parts[2:]
    if re.fullmatch(DEVICE_PATTERN, device_id) is None or suffix not in MODELS:
        raise ContractError("invalid_topic")
    if device_id != context.device_id:
        raise ContractError("identity_mismatch", "$.device_id")
    try:
        message = MODELS[suffix].model_validate(document)
    except ValidationError as error:
        first_location = error.errors(include_input=False, include_url=False)[0]["loc"]
        path = "$" + "".join(f".{component}" for component in first_location)
        raise ContractError("invalid_schema", path) from None
    if message.device_id != device_id:
        raise ContractError("identity_mismatch", "$.device_id")
    if hasattr(message, "binding_id") and message.binding_id not in context.binding_ids:
        raise ContractError("binding_mismatch", "$.binding_id")
    return message


def _event_key(event: Event) -> tuple[str, str, int]:
    if not isinstance(event, (Telemetry, CommandResult)):
        raise ContractError("invalid_context")
    return event.device_id, event.boot_id, event.seq


def classify_event(candidate: Event, previous: Event | None) -> Literal["new", "duplicate"]:
    """Compare one retained event; no state, ordering assumptions or persistence."""
    key = _event_key(candidate)
    if previous is None or key != _event_key(previous):
        return "new"
    if candidate.kind != previous.kind or candidate.model_dump() != previous.model_dump():
        raise ContractError("event_conflict")
    return "duplicate"


def validate_command_delivery(command: RelayCommand, *, now: datetime | None,
                              clock_synchronized: bool) -> None:
    if not isinstance(command, RelayCommand) or type(clock_synchronized) is not bool:
        raise ContractError("invalid_context")
    if not clock_synchronized:
        raise ContractError("clock_unsynchronized")
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ContractError("invalid_context", "$.now")
    if now < utc_datetime(command.issued_at):
        raise ContractError("command_not_yet_valid", "$.issued_at")
    if now >= utc_datetime(command.expires_at):
        raise ContractError("command_expired", "$.expires_at")


def validate_command_result(result: CommandResult, command: RelayCommand) -> None:
    if not isinstance(result, CommandResult) or not isinstance(command, RelayCommand):
        raise ContractError("invalid_context")
    for field in ("device_id", "binding_id", "command_id"):
        if getattr(result, field) != getattr(command, field):
            raise ContractError("correlation_mismatch", f"$.{field}")
    if result.result == "applied" and command.type == "relay.set" and result.observed_on != command.desired_on:
        raise ContractError("correlation_mismatch", "$.observed_on")


def validate_acknowledgement(ack: Acknowledgement, event: Event) -> None:
    if not isinstance(ack, Acknowledgement):
        raise ContractError("invalid_context")
    _event_key(event)
    for field in ("device_id", "boot_id", "seq"):
        if getattr(ack, field) != getattr(event, field):
            raise ContractError("correlation_mismatch", f"$.{field}")
    if ack.event_kind != event.kind:
        raise ContractError("correlation_mismatch", "$.event_kind")
