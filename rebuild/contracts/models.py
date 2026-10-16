"""Version 1 wire models. No application, transport or database imports."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

MAX_PAYLOAD_BYTES = 4096
MAX_DEPTH = 8  # The root object is depth one; objects and arrays both count.
MAX_SAFE_INTEGER = 2**53 - 1
DEFAULT_PREFIX = "bangusbuhai-rebuild"
DEVICE_PATTERN = r"BB-[0-9A-F]{12}"
UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
UTC_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z"


def utc_datetime(value: str) -> datetime:
    """Parse canonical UTC text, rejecting impossible dates and non-UTC offsets."""
    if type(value) is not str or re.fullmatch(UTC_PATTERN, value) is None:
        raise ValueError("Expected a UTC timestamp ending in Z")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _timestamp(value: object) -> str:
    utc_datetime(value)
    return value


def _number(value: object) -> int | float:
    if type(value) not in (int, float):
        raise ValueError("Expected a JSON number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("Expected a finite number")
    return value


DeviceId = Annotated[str, Field(min_length=15, max_length=15, pattern=f"^{DEVICE_PATTERN}$")]
Uuid = Annotated[str, Field(min_length=36, max_length=36, pattern=f"^{UUID_PATTERN}$")]
Uint32 = Annotated[int, Field(ge=0, le=2**32 - 1)]
Milliseconds = Annotated[int, Field(ge=0, le=MAX_SAFE_INTEGER)]
UtcTimestamp = Annotated[str, BeforeValidator(_timestamp), Field(min_length=20, max_length=27, pattern=f"^{UTC_PATTERN}$")]
Measurement = Annotated[float, BeforeValidator(_number)]
Reason = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")]
Validity = Literal["valid", "invalid", "stale", "missing", "unverified"]


class WireModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class Envelope(WireModel):
    schema_version: Annotated[int, Field(ge=1, le=1)]
    device_id: DeviceId
    kind: ClassVar[str]


class BoundEnvelope(Envelope):
    binding_id: Uuid


class EventEnvelope(BoundEnvelope):
    boot_id: Uuid
    seq: Uint32
    capture_uptime_ms: Milliseconds
    time_quality: Literal["synchronized", "unsynchronized"]

    def check_time(self, timestamp: str | None) -> None:
        if (timestamp is not None) != (self.time_quality == "synchronized"):
            raise ValueError("Event time must agree with clock synchronization")


class Reading(WireModel):
    value: Measurement | None
    source: Literal["sensor", "default"]
    validity: Validity
    sample_age_ms: Milliseconds | None
    last_valid_age_ms: Milliseconds | None

    @model_validator(mode="after")
    def consistent_reading(self) -> Self:
        if self.source == "default":
            if self.validity != "unverified" or self.value is None:
                raise ValueError("A default must be an unverified numeric value")
            if self.sample_age_ms is not None or self.last_valid_age_ms is not None:
                raise ValueError("A default is not a sensor sample")
            return self
        if self.validity in ("invalid", "missing") and self.value is not None:
            raise ValueError("Invalid and missing readings must have null values")
        if self.validity in ("valid", "unverified") and self.value is None:
            raise ValueError("Valid and unverified readings require a value")
        if self.value is not None and self.sample_age_ms is None and self.validity != "unverified":
            raise ValueError("An unknown sample age requires unverified validity")
        if self.validity == "valid":
            if self.sample_age_ms is None or self.last_valid_age_ms is None:
                raise ValueError("Valid readings require both ages")
            if self.sample_age_ms != self.last_valid_age_ms:
                raise ValueError("A valid sample is also the last valid sample")
        return self


class TemperatureReading(Reading):
    unit: Literal["degC"]
    source: Literal["sensor"]

    @model_validator(mode="after")
    def temperature_age(self) -> Self:
        if self.validity == "valid" and self.sample_age_ms >= 60000:
            raise ValueError("Temperature at least 60 seconds old cannot be valid")
        return self


class TurbidityReading(Reading):
    unit: Literal["NTU"]
    source: Literal["sensor"]


class PhReading(Reading):
    unit: Literal["pH"]


class Readings(WireModel):
    temperature: TemperatureReading
    turbidity: TurbidityReading
    ph: PhReading


class RelaySnapshot(WireModel):
    on: bool | None
    mode: Literal["demo"]
    reason: Reason


class Diagnostics(WireModel):
    queue_dropped: Uint32
    reconnects: Uint32


class Telemetry(EventEnvelope):
    kind = "telemetry"
    fw_version: Annotated[str, Field(min_length=1, max_length=64)]
    measured_at: UtcTimestamp | None
    readings: Readings
    relay: RelaySnapshot
    diagnostics: Diagnostics

    @model_validator(mode="after")
    def consistent_capture(self) -> Self:
        self.check_time(self.measured_at)
        for reading in (self.readings.temperature, self.readings.turbidity, self.readings.ph):
            for age in (reading.sample_age_ms, reading.last_valid_age_ms):
                if age is not None and age > self.capture_uptime_ms:
                    raise ValueError("Sample ages cannot exceed capture uptime")
        return self


class Status(Envelope):
    kind = "status"
    boot_id: Uuid
    connection_id: Uuid
    state: Literal["online", "offline"]


class RelayCommand(BoundEnvelope):
    kind = "command"
    command_id: Uuid
    type: Literal["relay.set"]
    desired_on: bool
    issued_at: UtcTimestamp
    expires_at: UtcTimestamp

    @model_validator(mode="after")
    def ordered_times(self) -> Self:
        if utc_datetime(self.expires_at) <= utc_datetime(self.issued_at):
            raise ValueError("Expiry must follow issue time")
        return self


class CommandResult(EventEnvelope):
    kind = "command_result"
    command_id: Uuid
    created_at: UtcTimestamp | None
    result: Literal["accepted", "applied", "rejected", "failed"]
    reason: Reason
    observed_on: bool | None

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        self.check_time(self.created_at)
        if self.result == "applied" and self.observed_on is None:
            raise ValueError("Applied results require a known observed state")
        return self


class Acknowledgement(Envelope):
    kind = "ack"
    boot_id: Uuid
    seq: Uint32
    event_kind: Literal["telemetry", "command_result"]
    result: Literal["stored", "duplicate"]


Message = Telemetry | Status | RelayCommand | CommandResult | Acknowledgement
Event = Telemetry | CommandResult
MODELS = {
    "telemetry": Telemetry,
    "status": Status,
    "cmd": RelayCommand,
    "command-results": CommandResult,
    "acks": Acknowledgement,
}
