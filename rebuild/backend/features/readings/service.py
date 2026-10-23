"""Audited manual measurements and immutable, snapshot-consistent tank history."""
from datetime import timedelta, timezone

from sqlmodel import select

from backend.database.models import (DeviceEvent, ManualReading, ManualReadingRevision,
    ReadingHistoryState)
from backend.features.accounts.service import utc_now
from backend.features.registry.service import RegistryService
from backend.features.live.cursor import StreamCursor
from . import repository as queries
from .cursor import Cursor
from .errors import ReadingsError
from .schemas import MeasurementContent

CONTENT = ("measured_at", "temperature_c", "ph", "turbidity_ntu", "notes", "instrument")
METRICS = ("temperature_c", "ph", "turbidity_ntu")


class ReadingsService:
    def __init__(self, engine, token_key, clock=utc_now):
        self.engine, self.clock = engine, clock
        self.registry = RegistryService(engine, token_key, clock)
        self.cursor = Cursor(token_key)
        self.stream_cursor = StreamCursor(token_key)

    def tank(self, session, hatchery_id, tank_id, mutation=False):
        tank = self.registry.tank(session, hatchery_id, tank_id)
        if mutation and tank.archived_at is not None:
            raise ReadingsError(409, "tank_archived")
        return tank

    @staticmethod
    def reading(session, hatchery_id, tank_id, reading_id):
        row = session.get(ManualReading, reading_id)
        if row is None or (row.hatchery_id, row.tank_id) != (hatchery_id, tank_id):
            raise ReadingsError(404, "reading_unavailable")
        return row

    def content(self, body):
        content = MeasurementContent.model_validate({field: getattr(body, field) for field in CONTENT})
        if content.measured_at > self.clock() + timedelta(minutes=5):
            raise ReadingsError(422, "future_measurement")
        return content.model_dump()

    @staticmethod
    def manual_view(row, revision):
        return dict(origin="manual", id=row.id, hatchery_id=row.hatchery_id, tank_id=row.tank_id,
            received_at=row.received_at, created_by=row.created_by,
            revision_id=revision.id, version=revision.version, actor_id=revision.actor_id,
            changed_at=revision.changed_at, reason=revision.reason, voided=revision.voided,
            provenance="operator_reported_measurement",
            missing_metrics=[field for field in METRICS if getattr(revision, field) is None],
            **{field: getattr(revision, field) for field in CONTENT})

    @staticmethod
    def device_view(row):
        return dict(origin="device", id=row.id, hatchery_id=row.hatchery_id, tank_id=row.tank_id,
            device_id=row.payload["device_id"], binding_id=row.binding_id, measured_at=row.captured_at,
            received_at=row.received_at, telemetry=row.payload)

    def create(self, hatchery_id, tank_id, actor_id, body):
        with self.registry.operation(hatchery_id, actor_id, mutation=True) as session:
            self.tank(session, hatchery_id, tank_id, True)
            content = self.content(body)
            previous = queries.request_reading(session, hatchery_id, actor_id, body.request_id)
            if previous:
                initial = session.exec(select(ManualReadingRevision).where(
                    ManualReadingRevision.reading_id == previous.id, ManualReadingRevision.version == 1)).one()
                if previous.tank_id != tank_id or content != {field: getattr(initial, field) for field in CONTENT}:
                    raise ReadingsError(409, "request_id_conflict")
                return self.manual_view(previous, queries.current_revision(session, previous.id)), False
            row = ManualReading(hatchery_id=hatchery_id, tank_id=tank_id, created_by=actor_id,
                request_id=body.request_id, received_at=self.clock())
            session.add(row)
            session.flush()
            revision = ManualReadingRevision(reading_id=row.id, hatchery_id=hatchery_id, tank_id=tank_id,
                version=1, actor_id=actor_id, changed_at=self.clock(), **content)
            session.add(revision)
            session.flush()  # Journal and revision share this transaction through DB triggers.
            return self.manual_view(row, revision), True

    def change(self, hatchery_id, tank_id, actor_id, reading_id, body, action):
        with self.registry.operation(hatchery_id, actor_id, mutation=True) as session:
            self.tank(session, hatchery_id, tank_id, True)
            row = self.reading(session, hatchery_id, tank_id, reading_id)
            previous = queries.current_revision(session, row.id)
            if previous.version != body.expected_version:
                raise ReadingsError(409, "stale_version")
            if (action in ("correct", "void") and previous.voided) or (action == "restore" and not previous.voided):
                raise ReadingsError(409, "invalid_reading_state")
            content = self.content(body) if action == "correct" else {field: getattr(previous, field) for field in CONTENT}
            revision = ManualReadingRevision(reading_id=row.id, hatchery_id=hatchery_id, tank_id=tank_id,
                version=previous.version + 1, actor_id=actor_id, changed_at=self.clock(), reason=body.reason,
                voided=action == "void", **content)
            session.add(revision)
            session.flush()
            return self.manual_view(row, revision)

    def detail(self, hatchery_id, tank_id, actor_id, origin, reading_id):
        with self.registry.operation(hatchery_id, actor_id) as session:
            self.tank(session, hatchery_id, tank_id)
            if origin == "manual":
                row = self.reading(session, hatchery_id, tank_id, reading_id)
                return self.manual_view(row, queries.current_revision(session, row.id))
            row = session.get(DeviceEvent, reading_id)
            if row is None or row.kind != "telemetry" or (row.hatchery_id, row.tank_id) != (hatchery_id, tank_id):
                raise ReadingsError(404, "reading_unavailable")
            return self.device_view(row)

    def revisions(self, hatchery_id, tank_id, actor_id, reading_id, limit, before):
        with self.registry.operation(hatchery_id, actor_id) as session:
            self.tank(session, hatchery_id, tank_id)
            row = self.reading(session, hatchery_id, tank_id, reading_id)
            statement = select(ManualReadingRevision).where(ManualReadingRevision.reading_id == row.id)
            if before is not None:
                statement = statement.where(ManualReadingRevision.version < before)
            revisions = session.exec(statement.order_by(ManualReadingRevision.version.desc()).limit(limit + 1)).all()
            return dict(items=[self.manual_view(row, revision) for revision in revisions[:limit]],
                next_before_version=revisions[limit - 1].version if len(revisions) > limit else None)

    def history(self, hatchery_id, tank_id, actor_id, *, limit=50, cursor=None, time_basis="measured",
                origin="all", include_voided=False, since=None, until=None, _position=None):
        def normalize(value):
            if value is None:
                return None
            if value.tzinfo is None:
                raise ReadingsError(422, "invalid_time_range")
            return value.astimezone(timezone.utc)
        since, until = normalize(since), normalize(until)
        if since is not None and until is not None and since >= until:
            raise ReadingsError(422, "invalid_time_range")
        scope = dict(hatchery=str(hatchery_id), tank=str(tank_id), time_basis=time_basis, origin=origin,
            include_voided=include_voided, since=since.isoformat() if since else None,
            until=until.isoformat() if until else None)
        with self.registry.operation(hatchery_id, actor_id) as session:
            self.tank(session, hatchery_id, tank_id)
            state = session.get(ReadingHistoryState, hatchery_id)
            position = state.last_position if _position is None else min(_position, state.last_position)
            last = None
            if cursor is not None:
                position, last = self.cursor.open(cursor, scope)
                if position > state.last_position:
                    raise ReadingsError(422, "invalid_cursor")
            rows = queries.history(session, hatchery_id, tank_id, position, basis=time_basis, origin=origin,
                include_voided=include_voided, since=since, until=until, last=last, limit=limit)
            next_cursor = None
            if len(rows) > limit:
                final = rows[limit - 1]
                clock = final["measured_at" if time_basis == "measured" else "received_at"]
                next_cursor = self.cursor.seal(scope, position, [clock.isoformat(), final["origin"], str(final["id"])])
            rows = rows[:limit]
            device_ids = [row["ref"] for row in rows if row["origin"] == "device"]
            manual_ids = [row["ref"] for row in rows if row["origin"] == "manual"]
            devices = {row.id: row for row in session.exec(select(DeviceEvent).where(DeviceEvent.id.in_(device_ids))).all()}
            revisions = {row.id: row for row in session.exec(select(ManualReadingRevision).where(ManualReadingRevision.id.in_(manual_ids))).all()}
            headers = {row.id: row for row in session.exec(select(ManualReading).where(
                ManualReading.id.in_([revision.reading_id for revision in revisions.values()]))).all()}
            items = [self.device_view(devices[row["ref"]]) if row["origin"] == "device" else
                self.manual_view(headers[row["id"]], revisions[row["ref"]]) for row in rows]
            return dict(items=items, next_cursor=next_cursor, time_basis=time_basis, snapshot_position=position,
                stream_cursor=self.stream_cursor.seal(hatchery_id, tank_id, position),
                unknown_capture_times="excluded" if time_basis == "measured" else "included")
