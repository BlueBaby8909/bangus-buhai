from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field,
    StringConstraints, field_validator, model_validator)

from contracts import Telemetry
from contracts.models import Measurement

Metric = Literal["temperature_c", "ph", "turbidity_ntu"]
Reason = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)]


def timestamp(value):
    # Reject epoch numbers and date-only/coerced timestamps at the HTTP boundary.
    if isinstance(value, str):
        # Pydantic also accepts numeric strings as epoch seconds; these do not
        # supply the explicit timezone required for a reported measurement.
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("Timezone-aware timestamp required")
    return value


Timestamp = Annotated[AwareDatetime, BeforeValidator(timestamp)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MeasurementContent(Input):
    measured_at: Timestamp
    temperature_c: Measurement | None = None
    ph: Measurement | None = None
    turbidity_ntu: Measurement | None = None
    notes: str | None = Field(default=None, max_length=2000, strict=True)
    instrument: str | None = Field(default=None, max_length=200, strict=True)

    @field_validator("measured_at")
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def measured(self):
        if all(getattr(self, field) is None for field in ("temperature_c", "ph", "turbidity_ntu")):
            raise ValueError("At least one measured value required")
        return self


class CreateMeasurement(MeasurementContent):
    request_id: UUID


class RevisionAction(Input):
    expected_version: int = Field(strict=True, ge=1)
    reason: Reason


class CorrectMeasurement(MeasurementContent, RevisionAction):
    pass


class ManualResponse(MeasurementContent):
    origin: Literal["manual"] = "manual"
    id: UUID
    hatchery_id: UUID
    tank_id: UUID
    received_at: datetime
    created_by: UUID
    version: int
    revision_id: UUID
    actor_id: UUID
    changed_at: datetime
    reason: str | None
    voided: bool
    provenance: Literal["operator_reported_measurement"] = "operator_reported_measurement"
    missing_metrics: list[Metric]


class DeviceResponse(BaseModel):
    origin: Literal["device"] = "device"
    id: UUID
    hatchery_id: UUID
    tank_id: UUID
    device_id: str
    binding_id: UUID
    measured_at: datetime | None
    received_at: datetime
    telemetry: Telemetry


ReadingResponse = Annotated[ManualResponse | DeviceResponse, Field(discriminator="origin")]


class HistoryResponse(BaseModel):
    items: list[ReadingResponse]
    next_cursor: str | None
    time_basis: Literal["measured", "received"]
    snapshot_position: int
    stream_cursor: str
    unknown_capture_times: Literal["excluded", "included"]


class RevisionsResponse(BaseModel):
    items: list[ManualResponse]
    next_before_version: int | None


from backend.features.registry.schemas import DeviceResponse as RegistryDeviceResponse, TankResponse


class SummaryDevice(RegistryDeviceResponse):
    latest: DeviceResponse | None
    connectivity: Literal['unknown'] = 'unknown'


class TankSummary(BaseModel):
    tank: TankResponse
    devices: list[SummaryDevice]


class SummaryResponse(BaseModel):
    items: list[TankSummary]
    next_cursor: str | None
    server_time: datetime
    temperature_stale_after_ms: Literal[60000] = 60000
