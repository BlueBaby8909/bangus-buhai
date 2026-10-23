"""Ingestion SQL and bounded quarantine; caller owns the transaction."""
import sqlalchemy as sa
from sqlmodel import select

from backend.database.models import DeviceEvent, IngestionQuarantine
from backend.features.registry.security import digest

# Fixed signed bigint namespaces, shared by all worker processes.
QUARANTINE_LOCK = 0x424251554152


def previous(session, device_id, event):
    return session.exec(select(DeviceEvent).where(DeviceEvent.device_id == device_id,
        DeviceEvent.boot_id == event.boot_id, DeviceEvent.seq == event.seq)).one_or_none()


def quarantined_candidate(session, event):
    fingerprint = digest(dict(kind=event.kind, payload=event.model_dump(mode="json")))
    return session.exec(select(IngestionQuarantine).where(
        IngestionQuarantine.external_id == event.device_id,
        IngestionQuarantine.boot_id == event.boot_id,
        IngestionQuarantine.seq == event.seq,
        IngestionQuarantine.digest == fingerprint)).one_or_none()


def quarantine(session, event, reason, received_at, limits):
    payload = event.model_dump(mode="json")
    fingerprint = digest(dict(kind=event.kind, payload=payload))
    # Global capacity and per-device capacity must remain correct across workers.
    session.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'), {'key': QUARANTINE_LOCK})
    if session.exec(select(IngestionQuarantine.id).where(IngestionQuarantine.external_id == event.device_id,
            IngestionQuarantine.boot_id == event.boot_id, IngestionQuarantine.seq == event.seq,
            IngestionQuarantine.digest == fingerprint)).first():
        return "quarantined"
    per_device = session.scalar(sa.select(sa.func.count()).select_from(IngestionQuarantine).where(
        IngestionQuarantine.external_id == event.device_id))
    total = session.scalar(sa.select(sa.func.count()).select_from(IngestionQuarantine))
    if per_device >= limits[0] or total >= limits[1]:
        return "quarantine_full"
    session.add(IngestionQuarantine(external_id=event.device_id, boot_id=event.boot_id, seq=event.seq,
        kind=event.kind, payload=payload, digest=fingerprint, reason=reason, received_at=received_at))
    session.flush()
    return "quarantined"
