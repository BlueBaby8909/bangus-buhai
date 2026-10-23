"""Bounded committed journal reads, including exact immutable manual revisions."""
from sqlmodel import select

from backend.database.models import DeviceEvent, ManualReading, ManualReadingRevision, ReadingChange


def changes(session, hatchery_id, tank_id, after, watermark, limit):
    return session.exec(select(ReadingChange).where(ReadingChange.hatchery_id == hatchery_id,
        ReadingChange.tank_id == tank_id, ReadingChange.position > after,
        ReadingChange.position <= watermark).order_by(ReadingChange.position).limit(limit)).all()


def records(session, changes):
    devices = {row.id: row for row in session.exec(select(DeviceEvent).where(
        DeviceEvent.id.in_([c.device_event_id for c in changes if c.device_event_id]))).all()}
    revisions = {row.id: row for row in session.exec(select(ManualReadingRevision).where(
        ManualReadingRevision.id.in_([c.manual_revision_id for c in changes if c.manual_revision_id]))).all()}
    headers = {row.id: row for row in session.exec(select(ManualReading).where(
        ManualReading.id.in_([r.reading_id for r in revisions.values()]))).all()}
    return devices, revisions, headers
