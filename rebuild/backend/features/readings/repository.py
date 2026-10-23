"""Bound SQL queries; service owns scope, transactions and presentation."""
import sqlalchemy as sa
from sqlmodel import select

from backend.database.models import DeviceEvent, ManualReading, ManualReadingRevision, ReadingChange


def current_revision(session, reading_id):
    return session.exec(select(ManualReadingRevision).where(ManualReadingRevision.reading_id == reading_id)
        .order_by(ManualReadingRevision.version.desc()).limit(1)).one()


def request_reading(session, hatchery_id, actor_id, request_id):
    return session.exec(select(ManualReading).where(ManualReading.hatchery_id == hatchery_id,
        ManualReading.created_by == actor_id, ManualReading.request_id == request_id)).one_or_none()


def history(session, hatchery_id, tank_id, position, *, basis, origin, include_voided, since, until, last, limit):
    e, r, m, c = DeviceEvent.__table__, ManualReadingRevision.__table__, ManualReading.__table__, ReadingChange.__table__
    eligible = sa.select(c).where(c.c.hatchery_id == hatchery_id, c.c.tank_id == tank_id,
        c.c.position <= position).cte("eligible_changes")
    devices = sa.select(e.c.id.label("ref"), e.c.id, sa.literal("device").label("origin"),
        e.c.captured_at.label("measured_at"), e.c.received_at).join(eligible, eligible.c.device_event_id == e.c.id)
    ranked = sa.select(r.c.id.label("ref"), m.c.id, sa.literal("manual").label("origin"), r.c.measured_at,
        m.c.received_at, r.c.voided, sa.func.row_number().over(partition_by=r.c.reading_id,
            order_by=r.c.version.desc()).label("rank")).join(m, m.c.id == r.c.reading_id).join(
                eligible, eligible.c.manual_revision_id == r.c.id).subquery()
    manuals = sa.select(ranked.c.ref, ranked.c.id, ranked.c.origin, ranked.c.measured_at,
        ranked.c.received_at).where(ranked.c.rank == 1)
    if not include_voided:
        manuals = manuals.where(ranked.c.voided.is_(False))
    records = sa.union_all(devices, manuals).subquery()
    clock = records.c.measured_at if basis == "measured" else records.c.received_at
    statement = sa.select(records).where(clock.is_not(None))
    if origin != "all":
        statement = statement.where(records.c.origin == origin)
    if since is not None:
        statement = statement.where(clock >= since)
    if until is not None:
        statement = statement.where(clock < until)
    if last is not None:
        statement = statement.where(sa.tuple_(clock, records.c.origin, records.c.id) < sa.tuple_(*last))
    return session.execute(statement.order_by(clock.desc(), records.c.origin.desc(), records.c.id.desc())
        .limit(limit + 1)).mappings().all()


def summary_records(session, hatchery, limit, cursor, include_archived):
    from backend.database.models import Tank, Binding, Device, DeviceInventory, DeviceConfiguration
    from backend.features.registry import repository
    query = select(Tank).where(Tank.hatchery_id == hatchery)
    if not include_archived: query = query.where(Tank.archived_at.is_(None))
    tanks, following = repository.page(session, query, Tank, Tank.created_at, limit, cursor)
    pairs = session.exec(select(Device, Binding).join(Binding, Binding.device_id == Device.id).where(
        Binding.tank_id.in_([t.id for t in tanks]), Binding.hatchery_id == hatchery, Binding.ended_at.is_(None))).all()
    devices = [d.id for d, _ in pairs]
    configs = {c.device_id:c for c in session.exec(select(DeviceConfiguration).where(DeviceConfiguration.device_id.in_(devices))).all()}
    inventory = {i.device_id:i for i in session.exec(select(DeviceInventory).where(DeviceInventory.device_id.in_(devices))).all()}
    ranked = select(DeviceEvent.id, sa.func.row_number().over(partition_by=DeviceEvent.binding_id,
        order_by=(DeviceEvent.received_at.desc(), DeviceEvent.id.desc())).label('rank')).where(
        DeviceEvent.binding_id.in_([b.id for _, b in pairs]), DeviceEvent.kind == 'telemetry').subquery()
    events = {e.binding_id:e for e in session.exec(select(DeviceEvent).join(ranked, ranked.c.id == DeviceEvent.id).where(ranked.c.rank == 1)).all()}
    return tanks, following, pairs, configs, inventory, events
