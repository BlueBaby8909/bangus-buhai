"""Transaction-scoped persistence only; this is not an authenticated ingestion endpoint."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from contracts import CommandResult, Telemetry, classify_event
from contracts.models import Event, utc_datetime

from .models import Binding, Device, DeviceEvent


def persist_event(session: Session, event: Event) -> str:
    """Store or compare an event. Caller owns commit/rollback and any later ACK.

    T13 must authenticate publisher/registry and decide capture-window admission
    before invoking this operation, particularly for closed/unsynchronized bindings.
    T12's PostgreSQL trigger records newly inserted telemetry in the history
    journal atomically; duplicates and command results do not allocate positions.
    """
    if not isinstance(event, (Telemetry, CommandResult)):
        raise ValueError("Expected a validated telemetry or command result")
    # Revalidate even model_construct/model_copy callers; frozen nested JSON is
    # not a substitute for validation at the persistence boundary.
    event = type(event).model_validate(event.model_dump())
    binding = session.exec(select(Binding).join(Device, Binding.device_id == Device.id).where(
        Binding.id == UUID(event.binding_id), Device.external_id == event.device_id,
    )).one_or_none()
    if binding is None:
        raise ValueError("Unknown device/binding association")
    capture = event.measured_at if isinstance(event, Telemetry) else event.created_at
    values = dict(
        device_id=binding.device_id, tank_id=binding.tank_id, hatchery_id=binding.hatchery_id,
        binding_id=binding.id, boot_id=UUID(event.boot_id), seq=event.seq,
        kind=event.kind, payload=event.model_dump(mode="json"), time_quality=event.time_quality,
        captured_at=utc_datetime(capture) if capture else None,
    )
    inserted = session.execute(insert(DeviceEvent).values(**values).on_conflict_do_nothing(
        constraint="device_event_identity").returning(DeviceEvent.id)).scalar_one_or_none()
    if inserted is not None:
        return "stored"
    previous = session.exec(select(DeviceEvent).where(
        DeviceEvent.device_id == binding.device_id,
        DeviceEvent.boot_id == UUID(event.boot_id), DeviceEvent.seq == event.seq,
    )).one()
    model = Telemetry if previous.kind == "telemetry" else CommandResult
    return classify_event(event, model.model_validate(previous.payload))
